"""One safe, lock-protected monitoring tick."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import fcntl
import logging
from pathlib import Path
from typing import Protocol, TextIO

from .email_parser import EmailParseError, parse_project_emails
from .imap_source import MailItem
from .models import DeliveryResult, ProjectEmail, Settings
from .proposal import ProposalError
from .relevance import is_relevant
from .store import mail_key, project_key
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


Parser = Callable[[bytes, int], tuple[ProjectEmail, ...]]
LockFileOpener = Callable[[Path], TextIO]
LockAcquirer = Callable[[], AbstractContextManager[bool]]


@dataclass(frozen=True)
class Dependencies:
    """Ports and stable inputs needed to run one monitor tick."""

    mail_source: MailSource
    store: Store
    proposal_client: ProposalGenerator
    notifier: Notifier
    settings: Settings
    profile: str
    parser: Parser = parse_project_emails
    lock_path: Path = LOCK_PATH
    lock_file_opener: LockFileOpener | None = None
    lock_acquirer: LockAcquirer | None = None


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
    advance_allowed = True
    for item in items:
        summary.inspected += 1
        terminal = _process_item(
            dependencies,
            summary,
            item,
            mail_key(item.message_id, item.uid),
            dry_run=dry_run,
            with_generation=with_generation,
        )

        if terminal and not dry_run and advance_allowed:
            dependencies.store.advance_cursor(item.uid)
        if not terminal:
            advance_allowed = False


def _process_item(
    dependencies: Dependencies,
    summary: RunSummary,
    item: MailItem,
    key: str,
    *,
    dry_run: bool,
    with_generation: bool,
) -> bool:
    try:
        projects = dependencies.parser(item.raw, item.uid)
    except EmailParseError as error:
        return _handle_parse_error(
            dependencies,
            summary,
            item,
            key,
            error.reason,
            dry_run=dry_run,
        )

    terminal = True
    for project in projects:
        key = project_key(project.project_url or "")
        if dependencies.store.is_recorded(key):
            summary.duplicates += 1
            continue
        if not is_relevant(project, dependencies.settings.filters.keywords):
            summary.ignored += 1
            if dry_run:
                LOGGER.info("dry-run: would ignore project UID %s", item.uid)
            else:
                dependencies.store.record(key, item.uid, "ignored")
            continue

        if not _handle_relevant_project(
            dependencies,
            summary,
            project,
            key,
            item.uid,
            dry_run=dry_run,
            with_generation=with_generation,
        ):
            terminal = False
    return terminal


def _handle_parse_error(
    dependencies: Dependencies,
    summary: RunSummary,
    item: MailItem,
    key: str,
    reason: str,
    *,
    dry_run: bool,
) -> bool:
    summary.parse_errors += 1
    if dry_run:
        LOGGER.info("dry-run: would alert and record parse error for UID %s", item.uid)
        return True
    try:
        dependencies.notifier.send_parse_error_alert(item.message_id, reason)
    except TelegramError:
        summary.delivery_failures += 1
        LOGGER.error("Telegram parse-error alert failed for UID %s", item.uid)
        return False
    dependencies.store.record(key, item.uid, "parse_error", reason)
    return True


def _handle_relevant_project(
    dependencies: Dependencies,
    summary: RunSummary,
    project: ProjectEmail,
    key: str,
    uid: int,
    *,
    dry_run: bool,
    with_generation: bool,
) -> bool:
    proposal, generation_error = _generate_or_none(
        dependencies,
        summary,
        project,
        enabled=not dry_run or with_generation,
    )
    if dry_run:
        LOGGER.info("dry-run: would notify and record project UID %s", uid)
        return True
    try:
        dependencies.notifier.send(project, proposal, generation_error)
    except TelegramError:
        summary.delivery_failures += 1
        LOGGER.error("Telegram project notification failed for UID %s", uid)
        return False
    dependencies.store.record(key, uid, "notified")
    summary.notified += 1
    return True


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


@contextmanager
def _acquire_lock(dependencies: Dependencies) -> Iterable[bool]:
    if dependencies.lock_acquirer is not None:
        with dependencies.lock_acquirer() as acquired:
            yield acquired
        return
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
