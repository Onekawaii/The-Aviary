from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = f"{self.version}\n{self.name}\n" + "\n-- statement --\n".join(self.statements)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        1,
        "foundation",
        (
            "CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY,text TEXT NOT NULL,context_json TEXT NOT NULL,created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL REFERENCES topics(id),status TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,elapsed_ms REAL,final_json TEXT)",
            "CREATE TABLE IF NOT EXISTS birds(bird_id TEXT PRIMARY KEY,name TEXT NOT NULL,version TEXT NOT NULL,role TEXT NOT NULL,metadata_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS opinions(id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES sessions(id),bird_id TEXT NOT NULL,opinion_json TEXT NOT NULL,created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,session_id INTEGER REFERENCES sessions(id),kind TEXT NOT NULL,content_json TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY,session_id INTEGER REFERENCES sessions(id),bird_id TEXT,artifact_type TEXT NOT NULL,content_json TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,event_type TEXT NOT NULL,entity_id TEXT,payload_json TEXT NOT NULL,created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS plugins(id INTEGER PRIMARY KEY,plugin_id TEXT NOT NULL UNIQUE,module TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,metadata_json TEXT NOT NULL,discovered_at TEXT NOT NULL)",
        ),
    ),
    Migration(
        2,
        "ledger_indexes",
        (
            "CREATE INDEX IF NOT EXISTS idx_sessions_topic_id ON sessions(topic_id)",
            "CREATE INDEX IF NOT EXISTS idx_opinions_session_id ON opinions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_receipts_session_kind ON receipts(session_id,kind)",
            "CREATE INDEX IF NOT EXISTS idx_artifacts_session_type ON artifacts(session_id,artifact_type)",
            "CREATE INDEX IF NOT EXISTS idx_history_entity ON history(entity_id,event_type)",
        ),
    ),
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_sequence(migrations: Iterable[Migration]) -> tuple[Migration, ...]:
    ordered = tuple(migrations)
    versions = tuple(migration.version for migration in ordered)
    if versions != tuple(range(1, len(ordered) + 1)):
        raise ValueError(f"migration versions must be contiguous from 1; received {versions}")
    return ordered


def apply_migrations(
    connection: sqlite3.Connection,
    migrations: Iterable[Migration] = MIGRATIONS,
) -> int:
    """Apply pending migrations atomically and reject migration drift.

    Each migration runs inside a SQLite savepoint. Savepoints are used instead
    of relying on sqlite3's version-dependent implicit transaction behaviour,
    so schema DDL and its migration receipt roll back together on Python 3.10+
    and on Termux.
    """
    ordered = _validate_sequence(migrations)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations("
        "version INTEGER PRIMARY KEY,"
        "name TEXT NOT NULL,"
        "checksum TEXT NOT NULL,"
        "applied_at TEXT NOT NULL)"
    )
    connection.commit()

    for migration in ordered:
        row = connection.execute(
            "SELECT name,checksum FROM schema_migrations WHERE version=?",
            (migration.version,),
        ).fetchone()
        if row is not None:
            if row[0] != migration.name or row[1] != migration.checksum:
                raise RuntimeError(
                    f"migration drift detected at version {migration.version}: "
                    f"stored={row[0]}:{row[1]} current={migration.name}:{migration.checksum}"
                )
            continue

        savepoint = f"aviary_migration_{migration.version}"
        try:
            connection.execute(f"SAVEPOINT {savepoint}")
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version,name,checksum,applied_at) VALUES(?,?,?,?)",
                (migration.version, migration.name, migration.checksum, _utcnow()),
            )
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        except sqlite3.Error as exc:
            try:
                connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            except sqlite3.Error:
                connection.rollback()
            raise RuntimeError(
                f"migration {migration.version} ({migration.name}) failed and was rolled back"
            ) from exc

    return current_schema_version(connection)


def current_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()
    return int(row[0])
