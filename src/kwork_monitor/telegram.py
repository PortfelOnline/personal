"""Safe, bounded Telegram Bot API notifications."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from urllib.parse import urlparse

import requests

from .models import DeliveryResult, ProjectEmail


class TelegramError(RuntimeError):
    """Raised when Telegram does not confirm delivery."""


_MESSAGE_LIMIT = 3_800
_FIELD_LIMIT = 512
_URL_LIMIT = 1_024


class TelegramNotifier:
    """Deliver HTML-escaped monitor notifications to one Telegram chat."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id

    def send(
        self,
        project: ProjectEmail,
        proposal: str | None,
        generation_error: str | None = None,
    ) -> DeliveryResult:
        """Deliver a project link and generated draft or generation fallback."""
        draft = proposal or f"⚠️ черновик не сгенерирован: {generation_error or 'неизвестная ошибка'}"
        header = "\n".join(
            (
                "<b>Новый проект Kwork</b>",
                f"<b>Тема:</b> {_escape_limited(project.subject, _FIELD_LIMIT, quote=True)}",
                f"<b>Бюджет:</b> {_escape_limited(project.budget or 'не указан', _FIELD_LIMIT, quote=True)}",
                f'<a href="{_project_url(project.project_url)}">Открыть проект вручную</a>',
                "",
                "<b>Черновик отклика</b>",
            )
        )
        return self._send_text(
            f"{header}\n{_escape_limited(draft, _MESSAGE_LIMIT - len(header) - 1, quote=True)}"
        )

    def send_parse_error_alert(
        self, message_id: str | None, reason: str
    ) -> DeliveryResult:
        """Deliver a bounded alert for one email that could not be parsed."""
        header = "\n".join(
            (
                "<b>Не удалось разобрать уведомление Kwork</b>",
                f"<b>Message-ID:</b> {_escape_limited(message_id or 'не указан', _FIELD_LIMIT, quote=True)}",
                "<b>Причина:</b>",
            )
        )
        return self._send_text(
            f"{header}\n{_escape_limited(reason, _MESSAGE_LIMIT - len(header) - 1, quote=True)}"
        )

    def _send_text(self, text: str) -> DeliveryResult:
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(self._url, json=payload, timeout=15)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            raise TelegramError("Telegram delivery failed") from None

        message_id = _delivery_message_id(body)
        if message_id is None:
            raise TelegramError("Telegram delivery was not confirmed")
        return DeliveryResult(message_id=message_id)


def _delivery_message_id(body: object) -> int | None:
    if not isinstance(body, Mapping) or body.get("ok") is not True:
        return None
    result = body.get("result")
    if not isinstance(result, Mapping):
        return None
    message_id = result.get("message_id")
    if not isinstance(message_id, int) or isinstance(message_id, bool):
        return None
    return message_id


def _project_url(value: str | None) -> str:
    """Return a bounded escaped http(s) URL suitable for an HTML attribute."""
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return _escape_limited(value[:_URL_LIMIT], _URL_LIMIT, quote=True)


def _escape_limited(value: str, limit: int, *, quote: bool = False) -> str:
    """Escape one input field without splitting an HTML entity at ``limit``."""
    escaped: list[str] = []
    size = 0
    for character in value:
        entity = escape(character, quote=quote)
        if size + len(entity) > limit:
            break
        escaped.append(entity)
        size += len(entity)
    return "".join(escaped)
