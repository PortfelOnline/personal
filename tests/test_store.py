from __future__ import annotations

import sqlite3
from pathlib import Path

from kwork_monitor.store import StateStore, mail_key, project_key


def test_store_keeps_cursor_and_deduplicates_message_id(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "seen_orders.db")

    assert store.get_cursor() == 0
    store.record("<a@test>", 7, "notified")
    store.advance_cursor(7)

    assert store.is_recorded("<a@test>") is True
    assert store.get_cursor() == 7


def test_store_cursor_never_moves_back_and_schema_uses_wal(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    store = StateStore(path)

    store.advance_cursor(12)
    store.advance_cursor(4)

    assert store.get_cursor() == 12
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"monitor_state", "processed_messages"} <= tables


def test_mail_key_uses_uid_only_without_message_id() -> None:
    assert mail_key(None, 9) == "uid:9"
    assert mail_key("", 9) == "uid:9"
    assert mail_key("<a@test>", 9) == "<a@test>"


def test_project_key_is_stable_across_digest_emails() -> None:
    assert project_key("https://kwork.ru/projects/9") == "project:https://kwork.ru/projects/9"
