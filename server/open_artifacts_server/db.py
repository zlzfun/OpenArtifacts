import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path: str) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              kind TEXT NOT NULL,
              owner TEXT NOT NULL,
              organization TEXT NOT NULL,
              workspace TEXT NOT NULL,
              visibility TEXT NOT NULL,
              status TEXT NOT NULL,
              current_version INTEGER NOT NULL,
              archived_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifact_versions (
              id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
              version_number INTEGER NOT NULL,
              payload TEXT NOT NULL,
              summary TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(artifact_id, version_number)
            );

            CREATE TABLE IF NOT EXISTS publish_events (
              id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
              version_number INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              idempotency_key TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(idempotency_key)
            );
            """
        )


@contextmanager
def transaction(database_path: str) -> Iterator[sqlite3.Connection]:
    with connect(database_path) as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
