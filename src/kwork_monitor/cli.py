"""Command-line entry point for one Kwork monitor tick."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
import logging
import os
from pathlib import Path

from .config import ConfigurationError, load_settings
from .imap_source import ImapSource, ImapSourceError, MailItem
from .models import FilterSettings, ImapSettings, ProjectEmail, Settings
from .proposal import ProposalClient
from .runner import Dependencies, run_once
from .store import StateStore
from .telegram import TelegramNotifier


LOGGER = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Build adapters for a single monitored tick and return its exit status."""
    arguments = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if arguments.fixture is not None:
        if not arguments.dry_run:
            LOGGER.error("--fixture is only allowed with --dry-run")
            return 2
        return _run_fixture(arguments)
    if arguments.config is None:
        LOGGER.error("--config is required unless --fixture is used")
        return 2
    try:
        settings, secrets = load_settings(arguments.config, os.environ)
        profile = _read_profile(arguments.config.parent / "PROFILE.md")
        dependencies = Dependencies(
            mail_source=ImapSource.from_settings(settings, secrets),
            store=StateStore(arguments.config.parent / "seen_orders.db"),
            proposal_client=ProposalClient(secrets.codeassist_base_url),
            notifier=TelegramNotifier(
                secrets.telegram_bot_token, secrets.telegram_chat_id
            ),
            settings=settings,
            profile=profile,
        )
    except (ConfigurationError, ImapSourceError, OSError):
        LOGGER.error("monitor configuration or IMAP setup failed")
        return 1
    return run_once(
        dependencies,
        dry_run=arguments.dry_run,
        with_generation=arguments.with_generation,
    ).exit_code


def _run_fixture(arguments: argparse.Namespace) -> int:
    """Run a fixture read-only without loading credentials or creating state."""
    if arguments.with_generation:
        LOGGER.error("--with-generation with a fixture requires configured services")
        return 2
    fixture_item = MailItem(
        uid=1,
        message_id=None,
        raw=arguments.fixture.read_bytes(),
        from_address="",
        subject="",
    )
    dependencies = Dependencies(
        mail_source=_FixtureSource(fixture_item),
        store=_DryRunStore(),
        proposal_client=_NoExternalServices(),
        notifier=_NoExternalServices(),
        settings=_fixture_settings(),
        profile="",
        lock_path=arguments.fixture.parent / "kwork-monitor.fixture.lock",
    )
    return run_once(dependencies, dry_run=True, with_generation=False).exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process one Kwork email monitor tick")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--with-generation", action="store_true")
    return parser


def _read_profile(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError("PROFILE.md could not be read") from error


def _fixture_settings() -> Settings:
    return Settings(
        imap=ImapSettings(host="fixture", mailbox="fixture"),
        filters=FilterSettings(
            senders=(), subject_patterns=(), keywords=("telegram",)
        ),
    )


class _FixtureSource:
    def __init__(self, item: MailItem) -> None:
        self._item = item

    def fetch_after(self, uid: int) -> Iterable[MailItem]:
        return (self._item,) if self._item.uid > uid else ()


class _DryRunStore:
    def get_cursor(self) -> int:
        return 0

    def is_recorded(self, key: str) -> bool:
        return False

    def record(self, key: str, uid: int, status: str, error: str | None = None) -> None:
        raise AssertionError("dry-run must not write state")

    def advance_cursor(self, uid: int) -> None:
        raise AssertionError("dry-run must not advance the cursor")


class _NoExternalServices:
    def generate(self, project: ProjectEmail, profile: str) -> str:
        raise AssertionError("fixture dry-run must not generate a proposal")

    def send(
        self,
        project: ProjectEmail,
        proposal: str | None,
        generation_error: str | None = None,
    ) -> object:
        raise AssertionError("fixture dry-run must not send Telegram")

    def send_parse_error_alert(self, message_id: str | None, reason: str) -> object:
        raise AssertionError("fixture dry-run must not send Telegram")


if __name__ == "__main__":
    raise SystemExit(main())
