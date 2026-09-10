"""Tests for safe, bounded Telegram delivery."""

from __future__ import annotations

from dataclasses import replace
from html.parser import HTMLParser
import re
import traceback

import pytest

from kwork_monitor.models import ProjectEmail
from kwork_monitor.telegram import TelegramError, TelegramNotifier


def _project() -> ProjectEmail:
    return ProjectEmail(
        message_id="<project-3@example.kwork.ru>",
        uid=103,
        subject="Нужен <Telegram> бот & интеграция",
        project_url="https://kwork.ru/projects/3?x=1&y=2",
        budget="10 000 <рублей>",
        description="Описание не выводится в уведомлении.",
    )


def test_telegram_message_includes_link_and_fallback_when_generation_failed(requests_mock) -> None:
    """Generation failure still needs a manually actionable Telegram alert."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 77}},
    )

    result = TelegramNotifier("token", "123").send(_project(), None, "timeout <again>")

    assert result.message_id == 77
    payload = requests_mock.last_request.json()
    assert requests_mock.last_request.timeout == 15
    assert payload["chat_id"] == "123"
    assert payload["disable_web_page_preview"] is True
    assert payload["parse_mode"] == "HTML"
    assert "<b>Новый проект Kwork</b>" in payload["text"]
    assert "Нужен &lt;Telegram&gt; бот &amp; интеграция" in payload["text"]
    assert '<a href="https://kwork.ru/projects/3?x=1&amp;y=2">Открыть проект вручную</a>' in payload["text"]
    assert "⚠️ черновик не сгенерирован: timeout &lt;again&gt;" in payload["text"]


def test_telegram_caps_long_escaped_message_before_delivery(requests_mock) -> None:
    """An oversized generated draft must not exceed Telegram's configured limit."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 78}},
    )

    TelegramNotifier("token", "123").send(_project(), "<&" * 2_000)

    text = requests_mock.last_request.json()["text"]
    assert len(text) <= 3_800
    assert re.search(r"&(?:[a-zA-Z]{0,3})?$", text) is None


@pytest.mark.parametrize(
    ("proposal", "entity"),
    [("\"" * 2_000, "&quot;"), ("'" * 2_000, "&#x27;")],
    ids=("quot", "apostrophe"),
)
def test_telegram_truncates_unescaped_draft_before_html_entities(
    proposal: str, entity: str, requests_mock
) -> None:
    """A character-entity boundary must never leave malformed Telegram HTML."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 80}},
    )

    TelegramNotifier("token", "123").send(_project(), proposal)

    text = requests_mock.last_request.json()["text"]
    assert len(text) <= 3_800
    assert text.endswith(entity)
    _assert_well_formed_html(text)


def test_telegram_caps_long_url_before_building_complete_href(requests_mock) -> None:
    """An unusually long project URL must not cut the href or its closing tag."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 81}},
    )
    project = replace(_project(), project_url="https://kwork.ru/projects/3?" + "x" * 10_000)

    TelegramNotifier("token", "123").send(project, "Черновик")

    text = requests_mock.last_request.json()["text"]
    assert len(text) <= 3_800
    assert 'href="' in text
    assert '">Открыть проект вручную</a>' in text
    _assert_well_formed_html(text)


@pytest.mark.parametrize(
    "response",
    [
        {"ok": False, "description": "Bad Request"},
        {"ok": True, "result": {}},
        {"not_ok": True},
    ],
)
def test_telegram_rejects_unsuccessful_or_invalid_api_responses(response: dict[str, object], requests_mock) -> None:
    """A missing confirmed Telegram message ID must not count as delivery."""
    requests_mock.post("https://api.telegram.org/bottoken/sendMessage", json=response)

    with pytest.raises(TelegramError):
        TelegramNotifier("token", "123").send(_project(), "Черновик")


def test_telegram_http_error_traceback_does_not_expose_bot_token(requests_mock) -> None:
    """An HTTPError includes its request URL, so it must not remain chained."""
    token = "synthetic-bot-token-must-not-leak"
    requests_mock.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        status_code=401,
    )

    with pytest.raises(TelegramError) as error:
        TelegramNotifier(token, "123").send(_project(), "Черновик")

    formatted = "".join(traceback.format_exception(error.value))
    assert token not in str(error.value)
    assert token not in formatted


def test_parse_error_alert_escapes_untrusted_reason_and_message_id(requests_mock) -> None:
    """Parser errors originate in emails and must not inject Telegram HTML."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 79}},
    )

    result = TelegramNotifier("token", "123").send_parse_error_alert("<id>", "bad <markup>")

    assert result.message_id == 79
    text = requests_mock.last_request.json()["text"]
    assert "&lt;id&gt;" in text
    assert "bad &lt;markup&gt;" in text


class _TagTracker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        assert self.open_tags.pop() == tag


def _assert_well_formed_html(text: str) -> None:
    parser = _TagTracker()
    parser.feed(text)
    parser.close()
    assert parser.open_tags == []
