"""Tests for the callback-query handling loop of the interactive proposal daemon."""

from __future__ import annotations

from unittest.mock import MagicMock

from kwork_monitor.proposal import ProposalError
from kwork_monitor.store import PendingProposal


def _callback_update(
    update_id: int, data: str, *, chat_id: int = 123, message_id: int = 81
) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "data": data,
            "message": {"chat": {"id": chat_id}, "message_id": message_id},
        },
    }


def _pending() -> PendingProposal:
    return PendingProposal(
        id=42,
        project_url="https://kwork.ru/projects/9",
        subject="Нужен бот",
        budget="10 000 ₽",
        description="ТЗ.",
    )


def _deps() -> tuple[MagicMock, MagicMock, MagicMock]:
    updates_client = MagicMock()
    proposal_client = MagicMock()
    store = MagicMock()
    store.get_telegram_offset.return_value = 0
    return updates_client, proposal_client, store


def test_poll_once_generates_edits_and_deletes_pending_project() -> None:
    from kwork_monitor.bot_daemon import poll_once

    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = _pending()
    proposal_client.generate.return_value = "Готов помочь."

    handled = poll_once(updates_client, proposal_client, store, "Опыт: Python")

    assert handled == 1
    updates_client.answer_callback_query.assert_called_once_with("cb-5")
    proposal_client.generate.assert_called_once()
    project, profile = proposal_client.generate.call_args.args
    assert project.subject == "Нужен бот"
    assert profile == "Опыт: Python"
    updates_client.edit_with_draft.assert_called_once_with("123", 81, project, "Готов помочь.")
    store.delete_pending.assert_called_once_with(42)
    store.set_telegram_offset.assert_called_once_with(6)


def test_poll_once_restores_button_after_generation_error() -> None:
    from kwork_monitor.bot_daemon import poll_once

    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = _pending()
    proposal_client.generate.side_effect = ProposalError("offline")

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    project = updates_client.edit_with_retry.call_args.args[2]
    updates_client.edit_with_retry.assert_called_once_with(
        "123", 81, project, 42, "proposal generation failed"
    )
    store.delete_pending.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(6)


def test_poll_once_marks_click_on_missing_project_as_expired() -> None:
    from kwork_monitor.bot_daemon import poll_once

    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = None

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    updates_client.answer_callback_query.assert_called_once_with("cb-5")
    updates_client.edit_expired.assert_called_once_with("123", 81)
    proposal_client.generate.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(6)


def test_poll_once_skips_unrecognised_updates_and_advances_offset() -> None:
    from kwork_monitor.bot_daemon import poll_once

    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [
        {"update_id": 5, "message": {"text": "hello"}},
        _callback_update(6, "not-a-generate-callback"),
    ]

    handled = poll_once(updates_client, proposal_client, store, "Опыт: Python")

    assert handled == 2
    updates_client.answer_callback_query.assert_called_once_with("cb-6")
    proposal_client.generate.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(7)


def test_poll_once_skips_malformed_callback_but_advances_offset() -> None:
    from kwork_monitor.bot_daemon import poll_once

    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [
        {"update_id": 5, "callback_query": {"id": "cb-5", "data": "gen:42", "message": {}}}
    ]

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    updates_client.answer_callback_query.assert_called_once_with("cb-5")
    store.get_pending.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(6)
