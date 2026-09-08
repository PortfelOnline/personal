"""Long-polling Telegram client for the interactive proposal-generation daemon."""

from __future__ import annotations

from collections.abc import Mapping
import json

import requests

from .models import ProjectEmail
from .telegram import _escape_limited, _project_header


class TelegramUpdatesError(RuntimeError):
    """Raised when Telegram does not confirm an updates-related call."""


_EDIT_MESSAGE_LIMIT = 3_800
_GENERATE_BUTTON = "Сгенерировать отклик"


class TelegramUpdatesClient:
    """Poll Telegram for button clicks and edit the message they were attached to."""

    def __init__(self, bot_token: str) -> None:
        self._url = f"https://api.telegram.org/bot{bot_token}"

    def get_updates(self, offset: int) -> list[dict]:
        """Long-poll for new updates at or after ``offset``, callback queries only."""
        response = requests.get(
            f"{self._url}/getUpdates",
            params={
                "offset": offset,
                "timeout": 25,
                "allowed_updates": json.dumps(["callback_query"]),
            },
            timeout=30,
        )
        try:
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            raise TelegramUpdatesError("getUpdates request failed") from None
        if not isinstance(body, Mapping) or body.get("ok") is not True:
            raise TelegramUpdatesError("getUpdates was not confirmed")
        result = body.get("result")
        return result if isinstance(result, list) else []

    def answer_callback_query(self, callback_query_id: str) -> None:
        """Stop the button's loading spinner; Telegram requires a prompt reply."""
        requests.post(
            f"{self._url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id},
            timeout=15,
        )

    def edit_with_draft(
        self, chat_id: str, message_id: int, project: ProjectEmail, draft: str
    ) -> None:
        """Replace the button with the generated draft, appended to the header."""
        header = _project_header(project)
        separator = "\n\n<b>Черновик отклика</b>\n"
        budget = _EDIT_MESSAGE_LIMIT - len(header) - len(separator)
        text = f"{header}{separator}{_escape_limited(draft, budget, quote=True)}"
        self._edit(chat_id, message_id, text, keyboard=None)

    def edit_with_retry(
        self,
        chat_id: str,
        message_id: int,
        project: ProjectEmail,
        pending_id: int,
        reason: str,
    ) -> None:
        """Report a generation failure and restore the button so the user can retry."""
        header = _project_header(project)
        separator = "\n\n⚠️ черновик не сгенерирован: "
        budget = _EDIT_MESSAGE_LIMIT - len(header) - len(separator)
        text = f"{header}{separator}{_escape_limited(reason, budget, quote=True)}"
        self._edit(chat_id, message_id, text, keyboard=_generate_button(pending_id))

    def edit_expired(self, chat_id: str, message_id: int) -> None:
        """Tell the user a click landed on a project that is no longer pending."""
        self._edit(chat_id, message_id, "Запрос устарел или уже обработан.", keyboard=None)

    def _edit(
        self, chat_id: str, message_id: int, text: str, *, keyboard: dict | None
    ) -> None:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            # Telegram keeps the previous keyboard unless an explicit (possibly
            # empty) reply_markup is sent with the edit.
            "reply_markup": keyboard if keyboard is not None else {"inline_keyboard": []},
        }
        try:
            response = requests.post(f"{self._url}/editMessageText", json=payload, timeout=15)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            raise TelegramUpdatesError("editMessageText request failed") from None
        if not isinstance(body, Mapping) or body.get("ok") is not True:
            raise TelegramUpdatesError("editMessageText was not confirmed")


def _generate_button(pending_id: int) -> dict:
    return {"inline_keyboard": [[{"text": _GENERATE_BUTTON, "callback_data": f"gen:{pending_id}"}]]}
