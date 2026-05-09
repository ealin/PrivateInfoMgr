"""SQLite data access layer for Places module (no encryption)."""

import json
import os
import sqlite3

from config import DATA_DIR

_INDEX_PATH = os.path.join(DATA_DIR, 'places_index.json')


def load_places_index() -> list[dict]:
    if not os.path.exists(_INDEX_PATH):
        return []
    with open(_INDEX_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_places_index(index: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def db_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def init_places_db(filename: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path(filename))
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS places (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL DEFAULT '',
            address    TEXT    NOT NULL DEFAULT '',
            link1      TEXT    NOT NULL DEFAULT '',
            link2      TEXT    NOT NULL DEFAULT '',
            achieved   INTEGER NOT NULL DEFAULT 0,
            note       TEXT    NOT NULL DEFAULT '',
            created_at TEXT    DEFAULT (datetime('now')),
            updated_at TEXT    DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()


def get_all_places(filename: str) -> list[dict]:
    conn = sqlite3.connect(db_path(filename))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT * FROM places ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_place(filename: str, place_id: int) -> dict | None:
    conn = sqlite3.connect(db_path(filename))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        'SELECT * FROM places WHERE id = ?', (place_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_place(filename: str, name: str, address: str, link1: str,
                 link2: str, achieved: int, note: str) -> int:
    conn = sqlite3.connect(db_path(filename))
    cur = conn.execute(
        '''INSERT INTO places (name, address, link1, link2, achieved, note)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (name, address, link1, link2, achieved, note),
    )
    place_id = cur.lastrowid
    conn.commit()
    conn.close()
    return place_id


def save_place(filename: str, place_id: int, name: str, address: str,
               link1: str, link2: str, achieved: int, note: str) -> None:
    conn = sqlite3.connect(db_path(filename))
    conn.execute(
        '''UPDATE places
           SET name=?, address=?, link1=?, link2=?, achieved=?, note=?,
               updated_at=datetime('now')
           WHERE id=?''',
        (name, address, link1, link2, achieved, note, place_id),
    )
    conn.commit()
    conn.close()
