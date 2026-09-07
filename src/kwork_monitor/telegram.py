"""Safe, bounded Telegram Bot API notifications."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
import re

import requests

from .models import DeliveryResult, ProjectEmail


class TelegramError(RuntimeError):
    """Raised when Telegram does not confirm delivery."""


_MESSAGE_LIMIT = 3_800


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
        text = "\n".join(
            (
                "<b>Новый проект Kwork</b>",
                f"<b>Тема:</b> {escape(project.subject)}",
                f"<b>Бюджет:</b> {escape(project.budget or 'не указан')}",
                f'<a href="{escape(project.project_url or "", quote=True)}">Открыть проект вручную</a>',
                "",
                "<b>Черновик отклика</b>",
                escape(draft),
            )
        )
        return self._send_text(text)

    def send_parse_error_alert(
        self, message_id: str | None, reason: str
    ) -> DeliveryResult:
        """Deliver a bounded alert for one email that could not be parsed."""
        text = "\n".join(
            (
                "<b>Не удалось разобрать уведомление Kwork</b>",
                f"<b>Message-ID:</b> {escape(message_id or 'не указан')}",
                f"<b>Причина:</b> {escape(reason)}",
            )
        )
        return self._send_text(text)

    def _send_text(self, text: str) -> DeliveryResult:
        payload = {
            "chat_id": self._chat_id,
            "text": _truncate_html(text),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(self._url, json=payload, timeout=15)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as error:
            raise TelegramError("Telegram delivery failed") from error

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


def _truncate_html(text: str) -> str:
    """Keep the Telegram limit without cutting an escaped character entity."""
    truncated = text[:_MESSAGE_LIMIT]
    while re.search(r"&(?:[a-zA-Z]{0,3})?$", truncated):
        truncated = truncated[:-1]
    return truncated
