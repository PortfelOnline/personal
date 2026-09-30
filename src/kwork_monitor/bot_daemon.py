"""Long-polling daemon for Kwork proposal-generation button clicks."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any

from .config import ConfigurationError, load_settings, read_profile
from .models import ProjectEmail
from .proposal import ProposalClient, ProposalError
from .store import PendingProposal, StateStore
from .telegram_updates import TelegramUpdatesClient


LOGGER = logging.getLogger(__name__)
_RETRY_DELAY_SECONDS = 5
_GENERATION_FAILURE_REASON = "proposal generation failed"


def main(argv: list[str] | None = None) -> int:
    """Configure adapters and keep processing Telegram callback queries."""
    arguments = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )
    try:
        _, secrets = load_settings(arguments.config, os.environ)
        profile = read_profile(arguments.config.parent / "PROFILE.md")
    except ConfigurationError:
        LOGGER.error("bot daemon configuration failed")
        return 1

    run_forever(
        TelegramUpdatesClient(secrets.telegram_bot_token),
        ProposalClient(secrets.codeassist_base_url),
        StateStore(arguments.config.parent / "seen_orders.db"),
        profile,
    )
    return 0


def run_forever(
    updates_client: Any, proposal_client: Any, store: Any, profile: str
) -> None:
    """Poll indefinitely; temporary Telegram failures are retried in-process."""
    while True:
        try:
            poll_once(updates_client, proposal_client, store, profile)
        except Exception as error:
            LOGGER.error(
                "update polling failed (%s), retrying in %ss",
                type(error).__name__,
                _RETRY_DELAY_SECONDS,
            )
            time.sleep(_RETRY_DELAY_SECONDS)


def poll_once(
    updates_client: Any, proposal_client: Any, store: Any, profile: str
) -> int:
    """Handle one batch of Telegram updates from the durable stored offset."""
    updates = updates_client.get_updates(store.get_telegram_offset())
    highest_update_id: int | None = None
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int) and not isinstance(update_id, bool):
            highest_update_id = update_id if highest_update_id is None else max(highest_update_id, update_id)
        try:
            _handle_update(update, updates_client, proposal_client, store, profile)
        except Exception as error:
            LOGGER.error(
                "failed to handle update_id %s (%s)",
                update_id,
                type(error).__name__,
            )
    if highest_update_id is not None:
        store.set_telegram_offset(highest_update_id + 1)
    return len(updates)


def _handle_update(
    update: dict[str, object], updates_client: Any, proposal_client: Any, store: Any, profile: str
) -> None:
    callback = update.get("callback_query")
    if not isinstance(callback, dict):
        return

    callback_id = callback.get("id")
    if isinstance(callback_id, str) and callback_id:
        updates_client.answer_callback_query(callback_id)

    pending_id = _pending_id(callback.get("data"))
    chat_and_message = _chat_and_message_ids(callback.get("message"))
    if pending_id is None or chat_and_message is None:
        return
    chat_id, message_id = chat_and_message

    pending = store.get_pending(pending_id)
    if pending is None:
        updates_client.edit_expired(chat_id, message_id)
        return

    project = _project_from_pending(pending)
    try:
        draft = proposal_client.generate(project, profile)
    except ProposalError:
        LOGGER.error("proposal generation failed for pending id %s", pending_id)
        updates_client.edit_with_retry(
            chat_id,
            message_id,
            project,
            pending_id,
            _GENERATION_FAILURE_REASON,
        )
        return

    updates_client.edit_with_draft(chat_id, message_id, project, draft)
    store.delete_pending(pending_id)


def _pending_id(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("gen:"):
        return None
    try:
        pending_id = int(value.removeprefix("gen:"))
    except ValueError:
        return None
    return pending_id if pending_id > 0 else None


def _chat_and_message_ids(value: object) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    chat = value.get("chat")
    message_id = value.get("message_id")
    if not isinstance(chat, dict) or not isinstance(message_id, int) or isinstance(message_id, bool):
        return None
    chat_id = chat.get("id")
    if isinstance(chat_id, bool) or not isinstance(chat_id, (int, str)):
        return None
    return str(chat_id), message_id


def _project_from_pending(pending: PendingProposal) -> ProjectEmail:
    return ProjectEmail(
        message_id="",
        uid=0,
        subject=pending.subject,
        project_url=pending.project_url,
        budget=pending.budget,
        description=pending.description,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Handle Kwork monitor 'Сгенерировать отклик' button clicks"
    )
    parser.add_argument("--config", type=Path, required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
