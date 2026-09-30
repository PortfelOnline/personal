"""Behavioral tests for one safe Kwork monitor tick."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kwork_monitor.imap_source import MailItem
from kwork_monitor.models import DeliveryResult, FilterSettings, ImapSettings, Settings
from kwork_monitor.proposal import ProposalError
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


def test_runner_notifies_each_relevant_project_in_a_single_digest(
    deps: Dependencies,
) -> None:
    """A digest must filter and deliver every row before its mail UID is completed."""
    digest = b"\n".join(
        (
            b"Message-ID: <digest-300@example.kwork.ru>",
            b"Subject: New Kwork projects",
            b"MIME-Version: 1.0",
            b"Content-Type: text/html; charset=utf-8",
            b"",
            b"<table>",
            b'<tr><td><a href="https://kwork.ru/projects/300">Telegram bot</a></td><td>Budget: 5 000 RUB</td></tr>',
            b'<tr><td><a href="https://kwork.ru/projects/301">Telegram integration</a></td><td>Budget: 7 000 RUB</td></tr>',
            b"</table>",
        )
    )
    deps = replace(
        deps,
        settings=replace(
            deps.settings,
            filters=replace(deps.settings.filters, minimum_budget_rub=1_000),
        ),
    )
    deps.mail_source.fetch_after.return_value = [replace(_item(101), raw=digest)]
    deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.notified == 2
    assert [
        call.args[0].project_url for call in deps.notifier.send_with_button.call_args_list
    ] == [
        "https://kwork.ru/projects/300",
        "https://kwork.ru/projects/301",
    ]
    assert [call.args[0] for call in deps.store.record.call_args_list] == [
        "project:https://kwork.ru/projects/300",
        "project:https://kwork.ru/projects/301",
    ]
    assert deps.store.advance_cursor.call_args.args[0] == 101


def test_runner_does_not_advance_cursor_when_telegram_fails(deps: Dependencies) -> None:
    """A failed delivery must be retried instead of being made durable."""
    deps.notifier.send.side_effect = TelegramError("offline")

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.delivery_failures == 1
    assert summary.exit_code == 1
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()


def test_runner_does_not_skip_failed_uid_when_a_later_notification_succeeds(
    deps: Dependencies,
) -> None:
    """Advancing through UID 102 after UID 101 fails would lose its retry."""
    deps.mail_source.fetch_after.return_value = [_item(101), _item(102)]
    deps.notifier.send.side_effect = [TelegramError("offline"), DeliveryResult(message_id=9)]

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.delivery_failures == 1
    assert summary.notified == 1
    assert [call.args[1] for call in deps.store.record.call_args_list] == [102]
    deps.store.advance_cursor.assert_not_called()


def test_dry_run_neither_writes_state_nor_sends_telegram(deps: Dependencies) -> None:
    """Preview mode must have no durable or notification side effects."""
    run_once(deps, dry_run=True, with_generation=False)

    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()
    deps.notifier.send.assert_not_called()
    deps.notifier.send_with_button.assert_not_called()
    deps.proposal_client.generate.assert_not_called()


def test_runner_processes_unsorted_mail_items_by_ascending_uid(deps: Dependencies) -> None:
    """A reordered source must not advance the cursor past an older message."""
    deps.mail_source.fetch_after.return_value = [_item(102), _item(101)]
    deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)

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


def test_runner_does_not_repeat_a_recorded_parse_error_while_cursor_is_held(
    deps: Dependencies,
) -> None:
    """A later recorded parse error must not alert again after an earlier UID fails."""
    deps.mail_source.fetch_after.return_value = [
        replace(_item(101), raw=b"Message-ID: <bad@example.test>\r\n\r\nno project")
    ]
    deps.store.is_recorded.return_value = True

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.duplicates == 1
    deps.notifier.send_parse_error_alert.assert_not_called()
    deps.store.record.assert_not_called()
    assert deps.store.advance_cursor.call_args.args[0] == 101


def test_dry_run_generation_requires_the_explicit_generation_flag(
    deps: Dependencies,
) -> None:
    """Preview generation is opt-in because it calls an external service."""
    run_once(deps, dry_run=True, with_generation=True)

    deps.proposal_client.generate.assert_called_once()
    deps.notifier.send.assert_not_called()
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()


def test_live_run_without_with_generation_sends_a_button_instead_of_a_draft(
    deps: Dependencies,
) -> None:
    """The default production tick must not call an external service per project."""
    deps.store.create_pending.return_value = 42
    deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)

    run_once(deps, dry_run=False, with_generation=False)

    deps.proposal_client.generate.assert_not_called()
    deps.store.create_pending.assert_called_once()
    deps.notifier.send_with_button.assert_called_once()
    assert deps.notifier.send_with_button.call_args.args[1] == 42


def test_runner_ignores_irrelevant_project_as_a_terminal_state(deps: Dependencies) -> None:
    """A non-matching project must be recorded before its cursor can move."""
    deps = replace(
        deps,
        settings=replace(
            deps.settings,
            filters=replace(deps.settings.filters, keywords=("design",)),
        ),
    )

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.ignored == 1
    assert deps.store.record.call_args.args[2] == "ignored"
    assert deps.store.advance_cursor.call_args.args[0] == 101
    deps.notifier.send.assert_not_called()


def test_manual_with_generation_delivers_fallback_when_proposal_generation_fails(
    deps: Dependencies,
) -> None:
    """--with-generation must still notify manually even if the bridge is down."""
    deps.proposal_client.generate.side_effect = ProposalError("offline")
    deps.notifier.send.return_value = DeliveryResult(message_id=9)

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.generation_failures == 1
    assert deps.notifier.send.call_args.args[1:] == (None, "proposal generation failed")
    assert deps.store.record.call_args.args[2] == "notified"


def test_button_notification_creates_pending_row_before_sending(deps: Dependencies) -> None:
    """The callback_data must reference a row that already exists when the click arrives."""
    deps.store.create_pending.return_value = 7
    deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)

    run_once(deps, dry_run=False, with_generation=False)

    created_project = deps.store.create_pending.call_args.args[0]
    assert created_project.project_url == "https://kwork.ru/projects/100"
    assert deps.notifier.send_with_button.call_args.args == (created_project, 7)


def test_button_notification_deletes_pending_row_when_delivery_fails(
    deps: Dependencies,
) -> None:
    """An undelivered button message must not leave an unreachable pending row behind."""
    deps.store.create_pending.return_value = 7
    deps.notifier.send_with_button.side_effect = TelegramError("offline")

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.delivery_failures == 1
    deps.store.delete_pending.assert_called_once_with(7)
    deps.store.record.assert_not_called()


def test_button_notification_is_fatal_when_pending_row_creation_fails(deps: Dependencies) -> None:
    """A local store failure creating the pending row is treated as fatal, like other store errors."""
    deps.store.create_pending.side_effect = RuntimeError("disk full")

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.fatal_failures == 1
    deps.notifier.send_with_button.assert_not_called()


def test_runner_ignores_project_below_minimum_budget(deps: Dependencies) -> None:
    """A matching skill alone must not alert on projects below the configured floor."""
    deps = replace(
        deps,
        settings=replace(
            deps.settings,
            filters=replace(deps.settings.filters, minimum_budget_rub=20_000),
        ),
    )

    summary = run_once(deps, dry_run=False, with_generation=True)

    assert summary.ignored == 1
    deps.proposal_client.generate.assert_not_called()
    deps.notifier.send.assert_not_called()


def test_runner_returns_success_without_processing_when_lock_is_contended(
    deps: Dependencies,
) -> None:
    """A cron overlap is normal and must not race state or delivery side effects."""
    deps = replace(deps, lock_acquirer=_contended_lock)

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.lock_unavailable is True
    assert summary.exit_code == 0
    deps.mail_source.fetch_after.assert_not_called()
    deps.store.record.assert_not_called()


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
            minimum_budget_rub=10_000,
        ),
    )


@contextmanager
def _contended_lock():
    yield False
