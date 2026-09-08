"""Tests for the daemon's long-polling and message-editing Telegram client."""

from __future__ import annotations

import pytest

from kwork_monitor.models import ProjectEmail
from kwork_monitor.telegram_updates import TelegramUpdatesClient, TelegramUpdatesError


def _project() -> ProjectEmail:
    return ProjectEmail(
        message_id="",
        uid=0,
        subject="Нужен бот",
        project_url="https://kwork.ru/projects/9",
        budget="10 000 ₽",
        description="ТЗ.",
    )


def test_get_updates_returns_result_list_and_sends_offset(requests_mock) -> None:
    requests_mock.get(
        "https://api.telegram.org/bottoken/getUpdates",
        json={"ok": True, "result": [{"update_id": 5}]},
    )

    updates = TelegramUpdatesClient("token").get_updates(5)

    assert updates == [{"update_id": 5}]
    assert requests_mock.last_request.qs["offset"] == ["5"]


def test_get_updates_raises_when_telegram_does_not_confirm(requests_mock) -> None:
    requests_mock.get(
        "https://api.telegram.org/bottoken/getUpdates",
        json={"ok": False},
    )

    with pytest.raises(TelegramUpdatesError, match="getUpdates"):
        TelegramUpdatesClient("token").get_updates(0)


def test_answer_callback_query_posts_the_callback_id(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/answerCallbackQuery",
        json={"ok": True},
    )

    TelegramUpdatesClient("token").answer_callback_query("cb-1")

    assert requests_mock.last_request.json() == {"callback_query_id": "cb-1"}


def test_edit_with_draft_clears_the_keyboard(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_with_draft("123", 81, _project(), "Готов помочь.")

    payload = requests_mock.last_request.json()
    assert payload["chat_id"] == "123"
    assert payload["message_id"] == 81
    assert "Готов помочь." in payload["text"]
    assert payload["reply_markup"] == {"inline_keyboard": []}


def test_edit_with_retry_restores_the_generate_button(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_with_retry("123", 81, _project(), 42, "proposal generation failed")

    payload = requests_mock.last_request.json()
    assert "proposal generation failed" in payload["text"]
    assert payload["reply_markup"] == {
        "inline_keyboard": [[{"text": "Сгенерировать отклик", "callback_data": "gen:42"}]]
    }


def test_edit_expired_clears_the_keyboard_with_a_generic_message(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_expired("123", 81)

    payload = requests_mock.last_request.json()
    assert "устарел" in payload["text"]
    assert payload["reply_markup"] == {"inline_keyboard": []}
