"""One safe, lock-protected monitoring tick."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import logging
from pathlib import Path
from typing import Protocol, TextIO

from .email_parser import EmailParseError, parse_project_email
from .imap_source import MailItem
from .models import DeliveryResult, ProjectEmail, Settings
from .proposal import ProposalError
from .relevance import is_relevant
from .store import mail_key
from .telegram import TelegramError


LOGGER = logging.getLogger(__name__)
LOCK_PATH = Path("/root/kwork-monitor/kwork-monitor.lock")


class MailSource(Protocol):
    """Read-only source of candidate mail messages."""

    def fetch_after(self, uid: int) -> Iterable[MailItem]: ...


class Store(Protocol):
    """Durable cursor and processed-message store."""

    def get_cursor(self) -> int: ...

    def is_recorded(self, key: str) -> bool: ...

    def record(self, key: str, uid: int, status: str, error: str | None = None) -> None: ...

    def advance_cursor(self, uid: int) -> None: ...


class ProposalGenerator(Protocol):
    """Generate an optional proposal draft."""

    def generate(self, project: ProjectEmail, profile: str) -> str: ...


class Notifier(Protocol):
    """Deliver confirmed project and parser-error notifications."""

    def send(
        self,
        project: ProjectEmail,
        proposal: str | None,
        generation_error: str | None = None,
    ) -> DeliveryResult: ...

    def send_parse_error_alert(
        self, message_id: str | None, reason: str
    ) -> DeliveryResult: ...


Parser = Callable[[bytes, int], ProjectEmail]
LockFileOpener = Callable[[Path], TextIO]


@dataclass(frozen=True)
class Dependencies:
    """Ports and stable inputs needed to run one monitor tick."""

    mail_source: MailSource
    store: Store
    proposal_client: ProposalGenerator
    notifier: Notifier
    settings: Settings
    profile: str
    parser: Parser = parse_project_email
    lock_path: Path = LOCK_PATH
    lock_file_opener: LockFileOpener | None = None


@dataclass
class RunSummary:
    """Observable outcome of one tick, suitable for the CLI exit status."""

    inspected: int = 0
    notified: int = 0
    ignored: int = 0
    parse_errors: int = 0
    duplicates: int = 0
    generation_failures: int = 0
    delivery_failures: int = 0
    fatal_failures: int = 0
    lock_unavailable: bool = False

    @property
    def exit_code(self) -> int:
        """Return non-zero for a retry-worthy delivery or fatal failure."""
        return int(bool(self.delivery_failures or self.fatal_failures))


def run_once(
    dependencies: Dependencies, *, dry_run: bool, with_generation: bool
) -> RunSummary:
    """Process each unseen mail item without ever contacting Kwork itself."""
    summary = RunSummary()
    try:
        with _acquire_lock(dependencies) as acquired:
            if not acquired:
                summary.lock_unavailable = True
                LOGGER.info("monitor tick skipped: another run owns the lock")
                return summary
            _run_tick(
                dependencies,
                summary,
                dry_run=dry_run,
                with_generation=with_generation,
            )
    except Exception as error:
        summary.fatal_failures += 1
        LOGGER.error("monitor tick failed: %s", type(error).__name__)
    return summary


def _run_tick(
    dependencies: Dependencies,
    summary: RunSummary,
    *,
    dry_run: bool,
    with_generation: bool,
) -> None:
    cursor = dependencies.store.get_cursor()
    items = sorted(dependencies.mail_source.fetch_after(cursor), key=lambda item: item.uid)
    for item in items:
        summary.inspected += 1
        key = mail_key(item.message_id, item.uid)
        if dependencies.store.is_recorded(key):
            summary.duplicates += 1
            _finish_terminal_item(
                dependencies, item.uid, dry_run=dry_run, status="already recorded"
            )
            continue

        try:
            project = dependencies.parser(item.raw, item.uid)
        except EmailParseError as error:
            _handle_parse_error(
                dependencies,
                summary,
                item,
                key,
                error.reason,
                dry_run=dry_run,
            )
            continue

        project_key = mail_key(project.message_id, item.uid)
        if not is_relevant(project, dependencies.settings.filters.keywords):
            summary.ignored += 1
            if dry_run:
                LOGGER.info("dry-run: would ignore UID %s", item.uid)
            else:
                dependencies.store.record(project_key, item.uid, "ignored")
                dependencies.store.advance_cursor(item.uid)
            continue

        _handle_relevant_project(
            dependencies,
            summary,
            project,
            project_key,
            item.uid,
            dry_run=dry_run,
            with_generation=with_generation,
        )


def _handle_parse_error(
    dependencies: Dependencies,
    summary: RunSummary,
    item: MailItem,
    key: str,
    reason: str,
    *,
    dry_run: bool,
) -> None:
    summary.parse_errors += 1
    if dry_run:
        LOGGER.info("dry-run: would alert and record parse error for UID %s", item.uid)
        return
    try:
        dependencies.notifier.send_parse_error_alert(item.message_id, reason)
    except TelegramError:
        summary.delivery_failures += 1
        LOGGER.error("Telegram parse-error alert failed for UID %s", item.uid)
        return
    dependencies.store.record(key, item.uid, "parse_error", reason)
    dependencies.store.advance_cursor(item.uid)


def _handle_relevant_project(
    dependencies: Dependencies,
    summary: RunSummary,
    project: ProjectEmail,
    key: str,
    uid: int,
    *,
    dry_run: bool,
    with_generation: bool,
) -> None:
    proposal, generation_error = _generate_or_none(
        dependencies,
        summary,
        project,
        enabled=not dry_run or with_generation,
    )
    if dry_run:
        LOGGER.info("dry-run: would notify and record project UID %s", uid)
        return
    try:
        dependencies.notifier.send(project, proposal, generation_error)
    except TelegramError:
        summary.delivery_failures += 1
        LOGGER.error("Telegram project notification failed for UID %s", uid)
        return
    dependencies.store.record(key, uid, "notified")
    dependencies.store.advance_cursor(uid)
    summary.notified += 1


def _generate_or_none(
    dependencies: Dependencies,
    summary: RunSummary,
    project: ProjectEmail,
    *,
    enabled: bool,
) -> tuple[str | None, str | None]:
    if not enabled:
        return None, "generation disabled"
    try:
        return dependencies.proposal_client.generate(project, dependencies.profile), None
    except ProposalError:
        summary.generation_failures += 1
        LOGGER.error("proposal generation failed for UID %s", project.uid)
        return None, "proposal generation failed"


def _finish_terminal_item(
    dependencies: Dependencies, uid: int, *, dry_run: bool, status: str
) -> None:
    if dry_run:
        LOGGER.info("dry-run: would advance UID %s (%s)", uid, status)
        return
    dependencies.store.advance_cursor(uid)


@contextmanager
def _acquire_lock(dependencies: Dependencies) -> Iterable[bool]:
    opener = dependencies.lock_file_opener or _open_lock_file
    lock_file = opener(dependencies.lock_path)
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


def _open_lock_file(path: Path) -> TextIO:
    return path.open("a+", encoding="utf-8")
