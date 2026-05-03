"""SQLite database access layer."""

import json
import os
import sqlite3

from config import DATA_DIR

_INDEX_PATH = os.path.join(DATA_DIR, 'index.json')


# ── Database index (index.json) ──────────────────────────────────────────────

def load_db_index() -> list[dict]:
    if not os.path.exists(_INDEX_PATH):
        return []
    with open(_INDEX_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_db_index(index: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def db_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


# ── Schema ───────────────────────────────────────────────────────────────────

def init_db(filename: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path(filename))
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY,
            username            TEXT    NOT NULL UNIQUE,
            password1_hash      TEXT    NOT NULL,
            password2_hash      TEXT    NOT NULL,
            encrypted_master_key BLOB   NOT NULL,
            master_key_salt     BLOB    NOT NULL,
            created_at          TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS records (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            enc_name     TEXT    NOT NULL DEFAULT '',
            enc_url      TEXT    NOT NULL DEFAULT '',
            enc_account  TEXT    NOT NULL DEFAULT '',
            enc_password TEXT    NOT NULL DEFAULT '',
            enc_note1    TEXT    NOT NULL DEFAULT '',
            enc_note2    TEXT    NOT NULL DEFAULT '',
            created_at   TEXT    DEFAULT (datetime('now')),
            updated_at   TEXT    DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()


# ── Users ────────────────────────────────────────────────────────────────────

def create_user(filename: str, username: str, password1_hash: str,
                password2_hash: str, encrypted_master_key: bytes,
                master_key_salt: bytes) -> None:
    conn = sqlite3.connect(db_path(filename))
    conn.execute(
        '''INSERT INTO users
           (username, password1_hash, password2_hash, encrypted_master_key, master_key_salt)
           VALUES (?, ?, ?, ?, ?)''',
        (username, password1_hash, password2_hash, encrypted_master_key, master_key_salt),
    )
    conn.commit()
    conn.close()


def get_user(filename: str, username: str) -> dict | None:
    conn = sqlite3.connect(db_path(filename))
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Records ──────────────────────────────────────────────────────────────────

def get_all_records(filename: str) -> list[dict]:
    conn = sqlite3.connect(db_path(filename))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT * FROM records ORDER BY updated_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_record(filename: str, record_id: int) -> dict | None:
    conn = sqlite3.connect(db_path(filename))
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_record(filename: str, enc_name: str, enc_url: str, enc_account: str,
                  enc_password: str, enc_note1: str, enc_note2: str) -> int:
    conn = sqlite3.connect(db_path(filename))
    cur = conn.execute(
        '''INSERT INTO records (enc_name, enc_url, enc_account, enc_password, enc_note1, enc_note2)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (enc_name, enc_url, enc_account, enc_password, enc_note1, enc_note2),
    )
    record_id = cur.lastrowid
    conn.commit()
    conn.close()
    return record_id


def update_record(filename: str, record_id: int, enc_name: str, enc_url: str,
                  enc_account: str, enc_password: str,
                  enc_note1: str, enc_note2: str) -> None:
    conn = sqlite3.connect(db_path(filename))
    conn.execute(
        '''UPDATE records
           SET enc_name=?, enc_url=?, enc_account=?, enc_password=?,
               enc_note1=?, enc_note2=?, updated_at=datetime('now')
           WHERE id=?''',
        (enc_name, enc_url, enc_account, enc_password, enc_note1, enc_note2, record_id),
    )
    conn.commit()
    conn.close()


def delete_record(filename: str, record_id: int) -> None:
    conn = sqlite3.connect(db_path(filename))
    conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
