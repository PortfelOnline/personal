"""Behavioral tests for one safe Kwork monitor tick."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kwork_monitor.imap_source import MailItem
from kwork_monitor.models import DeliveryResult, FilterSettings, ImapSettings, Settings
from kwork_monitor.runner import Dependencies, run_once
from kwork_monitor.telegram import TelegramError


FIXTURE = Path(__file__).parent / "fixtures" / "kwork_project_valid.eml"


@pytest.fixture
def deps(tmp_path: Path) -> Dependencies:
    """Use injected ports so the tick cannot contact mail or Telegram."""
    mail_source = MagicMock()
    mail_source.fetch_after.return_value = [_item(101)]
    store = MagicMock()
    store.get_cursor.return_value = 100
    store.is_recorded.return_value = False
    proposal_client = MagicMock()
    proposal_client.generate.return_value = "Подготовлю Telegram-бота."
    notifier = MagicMock()
    return Dependencies(
        mail_source=mail_source,
        store=store,
        proposal_client=proposal_client,
        notifier=notifier,
        settings=_settings(),
        profile="Опыт: Python",
        lock_path=tmp_path / "monitor.lock",
    )


def test_runner_records_and_advances_only_after_successful_telegram_delivery(
    deps: Dependencies,
) -> None:
    """Recording before confirmed delivery would permanently lose a project."""
    deps.notifier.send.return_value = DeliveryResult(message_id=9)

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.notified == 1
    assert deps.store.record.call_args.args[2] == "notified"
    assert deps.store.advance_cursor.call_args.args[0] == 101


def test_runner_does_not_advance_cursor_when_telegram_fails(deps: Dependencies) -> None:
    """A failed delivery must be retried instead of being made durable."""
    deps.notifier.send.side_effect = TelegramError("offline")

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.delivery_failures == 1
    assert summary.exit_code == 1
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()


def test_dry_run_neither_writes_state_nor_sends_telegram(deps: Dependencies) -> None:
    """Preview mode must have no durable or notification side effects."""
    run_once(deps, dry_run=True, with_generation=False)

    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()
    deps.notifier.send.assert_not_called()
    deps.proposal_client.generate.assert_not_called()


def test_runner_processes_unsorted_mail_items_by_ascending_uid(deps: Dependencies) -> None:
    """A reordered source must not advance the cursor past an older message."""
    deps.mail_source.fetch_after.return_value = [_item(102), _item(101)]
    deps.notifier.send.return_value = DeliveryResult(message_id=9)

    run_once(deps, dry_run=False, with_generation=False)

    assert [call.args[0] for call in deps.store.advance_cursor.call_args_list] == [101, 102]


def test_runner_records_parse_error_only_after_parse_alert_delivery(
    deps: Dependencies,
) -> None:
    """An undelivered parse alert must leave that malformed email retryable."""
    deps.mail_source.fetch_after.return_value = [
        replace(_item(101), raw=b"Message-ID: <bad@example.test>\r\n\r\nno project")
    ]
    deps.notifier.send_parse_error_alert.side_effect = TelegramError("offline")

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.delivery_failures == 1
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()


def test_dry_run_generation_requires_the_explicit_generation_flag(
    deps: Dependencies,
) -> None:
    """Preview generation is opt-in because it calls an external service."""
    run_once(deps, dry_run=True, with_generation=True)

    deps.proposal_client.generate.assert_called_once()
    deps.notifier.send.assert_not_called()
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()


def test_live_run_generates_a_draft_without_the_dry_run_opt_in_flag(
    deps: Dependencies,
) -> None:
    """The generation flag guards previews; live project alerts retain a draft."""
    deps.notifier.send.return_value = DeliveryResult(message_id=9)

    run_once(deps, dry_run=False, with_generation=False)

    deps.proposal_client.generate.assert_called_once()


def _item(uid: int) -> MailItem:
    return MailItem(
        uid=uid,
        message_id=f"<project-{uid}@example.test>",
        raw=FIXTURE.read_bytes(),
        from_address="noreply@kwork.ru",
        subject="Новый проект: Telegram-бот",
    )


def _settings() -> Settings:
    return Settings(
        imap=ImapSettings(host="imap.example.test", mailbox="INBOX"),
        filters=FilterSettings(
            senders=("noreply@kwork.ru",),
            subject_patterns=("Новый проект",),
            keywords=("telegram",),
        ),
    )
