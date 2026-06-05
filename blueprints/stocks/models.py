"""SQLite database access layer for Stocks module (no encryption)."""

import os
import sqlite3
from config import DATA_DIR

DB_NAME = 'stocks.db'


def get_db_path() -> str:
    return os.path.join(DATA_DIR, DB_NAME)


def init_stocks_db() -> None:
    """Initialize the SQLite database and create tables if they do not exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(get_db_path())
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS stock_trades (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name   TEXT NOT NULL,
            stock_code   TEXT NOT NULL,
            date         TEXT NOT NULL,
            type         TEXT NOT NULL, -- buy / sell / stock_dividend
            total_amount REAL NOT NULL,
            shares       INTEGER NOT NULL,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS funds (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            type1        TEXT NOT NULL, -- deposit / withdraw
            type2        TEXT NOT NULL, -- cash / dividend / sell_profit / settlement
            stock_name   TEXT NOT NULL DEFAULT '',
            total_amount REAL NOT NULL,
            created_at   TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()


def create_trade(stock_name: str, stock_code: str, date: str, trade_type: str,
                 total_amount: float, shares: int) -> int:
    """Insert a new stock trade record."""
    conn = sqlite3.connect(get_db_path())
    cur = conn.execute(
        '''INSERT INTO stock_trades (stock_name, stock_code, date, type, total_amount, shares)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (stock_name, stock_code, date, trade_type, total_amount, shares),
    )
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trade_id


def get_all_trades() -> list[dict]:
    """Retrieve all trade records sorted by date and id."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM stock_trades ORDER BY date ASC, id ASC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_trade(trade_id: int) -> None:
    """Delete a trade record by id."""
    conn = sqlite3.connect(get_db_path())
    conn.execute('DELETE FROM stock_trades WHERE id = ?', (trade_id,))
    conn.commit()
    conn.close()


def create_fund(date: str, type1: str, type2: str, stock_name: str,
                total_amount: float) -> int:
    """Insert a new fund record."""
    conn = sqlite3.connect(get_db_path())
    cur = conn.execute(
        '''INSERT INTO funds (date, type1, type2, stock_name, total_amount)
           VALUES (?, ?, ?, ?, ?)''',
        (date, type1, type2, stock_name, total_amount),
    )
    fund_id = cur.lastrowid
    conn.commit()
    conn.close()
    return fund_id


def get_all_funds() -> list[dict]:
    """Retrieve all fund records sorted by date and id (newest first)."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM funds ORDER BY date DESC, id DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_fund(fund_id: int) -> None:
    """Delete a fund record by id."""
    conn = sqlite3.connect(get_db_path())
    conn.execute('DELETE FROM funds WHERE id = ?', (fund_id,))
    conn.commit()
    conn.close()
