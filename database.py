import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "brain_dump.db"


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text  TEXT    NOT NULL,
                timestamp TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                processed INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS daily_summary (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT    NOT NULL UNIQUE,
                categories   TEXT    NOT NULL DEFAULT '{}',
                summary      TEXT    NOT NULL DEFAULT '',
                action_items TEXT    NOT NULL DEFAULT '[]',
                patterns     TEXT    NOT NULL DEFAULT '[]'
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
