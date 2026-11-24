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
        if version not in (0, 1, 2):
            raise RuntimeError(
                f"Unsupported database schema {version}; use a compatible MYCMD version"
            )
        if version == 0:
            sql = (Path(__file__).parent / "migrations" / "001_initial.sql").read_text()
            for statement in sql.split(";"):
                if statement.strip():
                    db.execute(statement)
            db.execute("PRAGMA user_version = 1")
        if version in (0, 1):
            db.execute(
                "CREATE TABLE IF NOT EXISTS local_conflicts ("
                "id TEXT PRIMARY KEY,"
                "owner_id TEXT NOT NULL,"
                "entity_type TEXT NOT NULL,"
                "entity_id TEXT NOT NULL,"
                "local_json TEXT NOT NULL CHECK(json_valid(local_json)),"
                "server_json TEXT CHECK(json_valid(server_json)),"
                "local_version INTEGER NOT NULL,"
                "server_version INTEGER,"
                "conflict_type TEXT NOT NULL,"
                "state TEXT NOT NULL DEFAULT 'pending',"
                "created_at TEXT NOT NULL,"
                "resolved_at TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS sync_status ("
                "owner_id TEXT PRIMARY KEY,"
                "last_cursor INTEGER NOT NULL DEFAULT 0,"
                "last_success_at TEXT,"
                "status TEXT NOT NULL DEFAULT 'idle',"
                "last_error TEXT)"
            )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS local_conflicts_owner_entity "
                "ON local_conflicts(owner_id, entity_type, entity_id)"
            )
            db.execute("PRAGMA user_version = 2")
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    return db
