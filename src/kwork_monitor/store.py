"""Durable cursor and idempotency state for one monitor mailbox."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


_STATUSES = frozenset({"notified", "ignored", "parse_error"})


def mail_key(message_id: str | None, uid: int) -> str:
    """Return the stable identity used for durable message deduplication."""
    normalized = message_id.strip() if isinstance(message_id, str) else ""
    return normalized or f"uid:{uid}"


class StateStore:
    """Persist the IMAP cursor and processing result in a local SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def get_cursor(self) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM monitor_state WHERE key = ?", ("cursor",)
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def advance_cursor(self, uid: int) -> None:
        if uid < 0:
            raise ValueError("UID must be non-negative")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                WHERE CAST(monitor_state.value AS INTEGER) < CAST(excluded.value AS INTEGER)
                """,
                ("cursor", str(uid)),
            )

    def is_recorded(self, key: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?", (key,)
            ).fetchone()
        return row is not None

    def record(
        self, key: str, uid: int, status: str, error: str | None = None
    ) -> None:
        if status not in _STATUSES:
            raise ValueError(f"unsupported processing status: {status!r}")
        if uid < 0:
            raise ValueError("UID must be non-negative")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO processed_messages
                    (message_id, uid, status, error, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    key,
                    uid,
                    status,
                    error,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS monitor_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    uid INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('notified', 'ignored', 'parse_error')),
                    error TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
