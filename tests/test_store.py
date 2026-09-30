from __future__ import annotations

import sqlite3
from pathlib import Path

from kwork_monitor.models import ProjectEmail
from kwork_monitor.store import PendingProposal, StateStore, mail_key, project_key


def _project(url: str = "https://kwork.ru/projects/9") -> ProjectEmail:
    return ProjectEmail(
        message_id="<p@test>",
        uid=1,
        subject="Нужен бот",
        project_url=url,
        budget="10 000 ₽",
        description="ТЗ.",
    )


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


def test_pending_proposal_round_trips_project_fields(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")

    pending_id = store.create_pending(_project())
    pending = store.get_pending(pending_id)

    assert pending == PendingProposal(
        id=pending_id,
        project_url="https://kwork.ru/projects/9",
        subject="Нужен бот",
        budget="10 000 ₽",
        description="ТЗ.",
    )


def test_get_pending_returns_none_for_missing_or_deleted_row(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    pending_id = store.create_pending(_project())

    assert store.get_pending(pending_id + 1) is None

    store.delete_pending(pending_id)

    assert store.get_pending(pending_id) is None


def test_telegram_offset_defaults_to_zero_and_persists(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")

    assert store.get_telegram_offset() == 0

    store.set_telegram_offset(42)

    assert store.get_telegram_offset() == 42
