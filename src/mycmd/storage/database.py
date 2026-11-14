"""SQLite connection and transactional, versioned schema initialization."""

import sqlite3
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("PRAGMA synchronous = FULL")
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError(
                f"Unsupported database schema {version}; use a compatible MYCMD version"
            )
        if version == 0:
            sql = (Path(__file__).parent / "migrations" / "001_initial.sql").read_text()
            for statement in sql.split(";"):
                if statement.strip():
                    db.execute(statement)
            db.execute("PRAGMA user_version = 1")
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    return db
