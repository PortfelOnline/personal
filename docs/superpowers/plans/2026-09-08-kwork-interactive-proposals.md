# Kwork Interactive Proposal Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current "every live tick auto-generates a draft" behavior with a Telegram inline button ("Сгенерировать отклик") that the user clicks per-project; a new long-polling daemon then generates the draft on demand and edits the notification message in place.

**Architecture:** The hourly cron tick (`kwork_monitor.cli`) stops calling the proposal generator by default — it stores a `pending_proposals` row in the existing SQLite state file and sends the notification with an inline keyboard button carrying that row's id as `callback_data`. A new always-running process (`kwork_monitor.bot_daemon`, systemd-managed) long-polls Telegram's `getUpdates`, and on a matching button click looks up the pending row, calls the existing `ProposalClient` (same Code Assist bridge, unchanged), and edits the original message with the draft (or a retryable error). `--with-generation` keeps its current meaning as a manual override that still generates eagerly (used for previews/backfill) — see spec's "Решённые вопросы" for why this stays.

**Tech Stack:** Python 3.10, `requests`, `sqlite3` (stdlib), `pytest` + `requests_mock`, systemd.

Spec: [2026-09-08-kwork-interactive-proposals-design.md](../specs/2026-09-08-kwork-interactive-proposals-design.md)

**Implementation-detail correction vs. the spec:** the spec's `pending_proposals` schema includes `chat_id`/`message_id` columns filled in "after successful delivery" — but the button's `callback_data` must be known *before* the message is sent, and Telegram's `callback_query.message` already carries the chat id and message id back to us when the button is clicked. So this plan drops those two columns entirely — one write (`create_pending`) before sending, nothing to reconcile after. No user-visible behavior changes.

---

### Task 1: `pending_proposals` table and Telegram offset in `store.py`

**Files:**
- Modify: `src/kwork_monitor/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_store.py`:

```python
from kwork_monitor.models import ProjectEmail
from kwork_monitor.store import PendingProposal


def _project(url: str = "https://kwork.ru/projects/9") -> ProjectEmail:
    return ProjectEmail(
        message_id="<p@test>",
        uid=1,
        subject="Нужен бот",
        project_url=url,
        budget="10 000 ₽",
        description="ТЗ.",
    )


def test_pending_proposal_round_trips_project_fields(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")

    pending_id = store.create_pending(_project())
    pending = store.get_pending(pending_id)

    assert pending == PendingProposal(
        id=pending_id,
        project_url="https://kwork.ru/projects/9",
        subject="Нужен бот",
        budget="10 000 ₽",
        description="ТЗ.",
    )


def test_get_pending_returns_none_for_missing_or_deleted_row(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    pending_id = store.create_pending(_project())

    assert store.get_pending(pending_id + 1) is None

    store.delete_pending(pending_id)

    assert store.get_pending(pending_id) is None


def test_telegram_offset_defaults_to_zero_and_persists(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")

    assert store.get_telegram_offset() == 0

    store.set_telegram_offset(42)

    assert store.get_telegram_offset() == 42
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: FAIL with `ImportError: cannot import name 'PendingProposal'` (or `AttributeError: 'StateStore' object has no attribute 'create_pending'`)

- [ ] **Step 3: Implement the schema and methods**

In `src/kwork_monitor/store.py`, add the import and dataclass near the top (after the existing imports, before `_STATUSES`):

```python
from dataclasses import dataclass

from .models import ProjectEmail


@dataclass(frozen=True)
class PendingProposal:
    """A project awaiting an on-demand generated proposal draft."""

    id: int
    project_url: str
    subject: str
    budget: str | None
    description: str | None
```

Extend `_initialize`'s script (add a fourth statement to the same `executescript` call, right after `processed_messages`):

```python
                CREATE TABLE IF NOT EXISTS pending_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_url TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    budget TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL
                );
```

Add methods to `StateStore` (after `record`, before the end of the class):

```python
    def create_pending(self, project: ProjectEmail) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO pending_proposals
                    (project_url, subject, budget, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project.project_url or "",
                    project.subject,
                    project.budget,
                    project.description,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return int(cursor.lastrowid)

    def get_pending(self, pending_id: int) -> PendingProposal | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, project_url, subject, budget, description
                FROM pending_proposals WHERE id = ?
                """,
                (pending_id,),
            ).fetchone()
        if row is None:
            return None
        return PendingProposal(
            id=row[0], project_url=row[1], subject=row[2], budget=row[3], description=row[4]
        )

    def delete_pending(self, pending_id: int) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM pending_proposals WHERE id = ?", (pending_id,))

    def get_telegram_offset(self) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM monitor_state WHERE key = ?", ("telegram_offset",)
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def set_telegram_offset(self, offset: int) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("telegram_offset", str(offset)),
            )
```

Note: `sqlite3.Connection` used as a context manager commits on successful exit but does **not** close the connection — this file already relies on that pattern elsewhere (see `record`), so `cursor.lastrowid` above is read while `connection` is still open, before the `with` block exits. Keep it inside the `with` body as written.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: PASS (all tests, including the 4 pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/kwork_monitor/store.py tests/test_store.py
git commit -m "feat: add pending_proposals table and Telegram offset to StateStore"
```

---

### Task 2: Shared `read_profile` helper (DRY between `cli.py` and the new daemon)

**Files:**
- Modify: `src/kwork_monitor/config.py`
- Modify: `src/kwork_monitor/cli.py:106-110` (remove local `_read_profile`, use the shared one)
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_config.py`:

```python
from kwork_monitor.config import ConfigurationError, read_profile


def test_read_profile_returns_file_contents(tmp_path: Path) -> None:
    profile_path = tmp_path / "PROFILE.md"
    profile_path.write_text("Опыт: Python", encoding="utf-8")

    assert read_profile(profile_path) == "Опыт: Python"


def test_read_profile_wraps_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="PROFILE.md could not be read"):
        read_profile(tmp_path / "missing.md")
```

(Check the top of `tests/test_config.py` already imports `Path` and `pytest`; if not, add `from pathlib import Path` and `import pytest`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_config.py -v -k read_profile`
Expected: FAIL with `ImportError: cannot import name 'read_profile'`

- [ ] **Step 3: Implement `read_profile` in `config.py`, then reuse it from `cli.py`**

Add to `src/kwork_monitor/config.py` (after `load_settings`, before `_load_yaml`):

```python
def read_profile(path: Path) -> str:
    """Return the freelancer brief used to constrain proposal generation."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError("PROFILE.md could not be read") from error
```

In `src/kwork_monitor/cli.py`, remove the local `_read_profile` function (lines 106-110) and its call site `profile = _read_profile(arguments.config.parent / "PROFILE.md")` becomes `profile = read_profile(arguments.config.parent / "PROFILE.md")`. Update the import line at the top of `cli.py`:

```python
from .config import ConfigurationError, load_settings, read_profile
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kwork_monitor/config.py src/kwork_monitor/cli.py tests/test_config.py
git commit -m "refactor: share read_profile between cli and the bot daemon"
```

---

### Task 3: `send_with_button` in `telegram.py`

**Files:**
- Modify: `src/kwork_monitor/telegram.py`
- Test: `tests/test_telegram.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_telegram.py`:

```python
def test_send_with_button_omits_draft_and_attaches_generate_callback(requests_mock) -> None:
    """The button variant must not contain a draft section and must carry the pending id."""
    requests_mock.post(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"ok": True, "result": {"message_id": 81}},
    )

    result = TelegramNotifier("token", "123").send_with_button(_project(), 42)

    assert result.message_id == 81
    payload = requests_mock.last_request.json()
    assert "Черновик отклика" not in payload["text"]
    assert payload["reply_markup"] == {
        "inline_keyboard": [[{"text": "Сгенерировать отклик", "callback_data": "gen:42"}]]
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_telegram.py -v -k send_with_button`
Expected: FAIL with `AttributeError: 'TelegramNotifier' object has no attribute 'send_with_button'`

- [ ] **Step 3: Extract the shared header and add `send_with_button`**

In `src/kwork_monitor/telegram.py`, replace the `send` method's header-building lines and the low-level POST logic. Full new file body for the changed region (everything from `class TelegramNotifier` down to just before `def _delivery_message_id`):

```python
class TelegramNotifier:
    """Deliver HTML-escaped monitor notifications to one Telegram chat."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._url = f"https://api.telegram.org/bot{bot_token}"
        self._chat_id = chat_id

    def send(
        self,
        project: ProjectEmail,
        proposal: str | None,
        generation_error: str | None = None,
    ) -> DeliveryResult:
        """Deliver a project link and generated draft or generation fallback."""
        draft = proposal or f"⚠️ черновик не сгенерирован: {generation_error or 'неизвестная ошибка'}"
        header = _project_header(project)
        separator = "\n\n<b>Черновик отклика</b>\n"
        budget = _MESSAGE_LIMIT - len(header) - len(separator)
        text = f"{header}{separator}{_escape_limited(draft, budget, quote=True)}"
        return self._deliver({"chat_id": self._chat_id, "text": text})

    def send_with_button(self, project: ProjectEmail, pending_id: int) -> DeliveryResult:
        """Deliver a project link with a button to request a drafted response."""
        return self._deliver(
            {
                "chat_id": self._chat_id,
                "text": _project_header(project),
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "Сгенерировать отклик", "callback_data": f"gen:{pending_id}"}]
                    ]
                },
            }
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
        return self._deliver(
            {
                "chat_id": self._chat_id,
                "text": f"{header}\n{_escape_limited(reason, _MESSAGE_LIMIT - len(header) - 1, quote=True)}",
            }
        )

    def _deliver(self, payload: dict[str, object]) -> DeliveryResult:
        payload.setdefault("parse_mode", "HTML")
        payload.setdefault("disable_web_page_preview", True)
        try:
            response = requests.post(f"{self._url}/sendMessage", json=payload, timeout=15)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            raise TelegramError("Telegram delivery failed") from None

        message_id = _delivery_message_id(body)
        if message_id is None:
            raise TelegramError("Telegram delivery was not confirmed")
        return DeliveryResult(message_id=message_id)


def _project_header(project: ProjectEmail) -> str:
    """Return the shared subject/budget/link block used by every notification variant."""
    return "\n".join(
        (
            "<b>Новый проект Kwork</b>",
            f"<b>Тема:</b> {_escape_limited(project.subject, _FIELD_LIMIT, quote=True)}",
            f"<b>Бюджет:</b> {_escape_limited(project.budget or 'не указан', _FIELD_LIMIT, quote=True)}",
            f'<a href="{_project_url(project.project_url)}">Открыть проект вручную</a>',
        )
    )
```

This changes `self._url` from a full `sendMessage` URL to the bot's base URL (`_deliver` appends `/sendMessage`) — check nothing else in the file reads `self._url` directly; it doesn't.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_telegram.py -v`
Expected: PASS (all tests, including the 3 pre-existing ones — they post to the same `.../sendMessage` URL as before)

- [ ] **Step 5: Commit**

```bash
git add src/kwork_monitor/telegram.py tests/test_telegram.py
git commit -m "feat: add send_with_button and extract shared project header"
```

---

### Task 4: `telegram_updates.py` — long-polling client used only by the daemon

**Files:**
- Create: `src/kwork_monitor/telegram_updates.py`
- Test: `tests/test_telegram_updates.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_telegram_updates.py`:

```python
"""Tests for the daemon's long-polling and message-editing Telegram client."""

from __future__ import annotations

import pytest

from kwork_monitor.models import ProjectEmail
from kwork_monitor.telegram_updates import TelegramUpdatesClient, TelegramUpdatesError


def _project() -> ProjectEmail:
    return ProjectEmail(
        message_id="",
        uid=0,
        subject="Нужен бот",
        project_url="https://kwork.ru/projects/9",
        budget="10 000 ₽",
        description="ТЗ.",
    )


def test_get_updates_returns_result_list_and_sends_offset(requests_mock) -> None:
    requests_mock.get(
        "https://api.telegram.org/bottoken/getUpdates",
        json={"ok": True, "result": [{"update_id": 5}]},
    )

    updates = TelegramUpdatesClient("token").get_updates(5)

    assert updates == [{"update_id": 5}]
    assert requests_mock.last_request.qs["offset"] == ["5"]


def test_get_updates_raises_when_telegram_does_not_confirm(requests_mock) -> None:
    requests_mock.get(
        "https://api.telegram.org/bottoken/getUpdates",
        json={"ok": False},
    )

    with pytest.raises(TelegramUpdatesError, match="getUpdates"):
        TelegramUpdatesClient("token").get_updates(0)


def test_answer_callback_query_posts_the_callback_id(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/answerCallbackQuery",
        json={"ok": True},
    )

    TelegramUpdatesClient("token").answer_callback_query("cb-1")

    assert requests_mock.last_request.json() == {"callback_query_id": "cb-1"}


def test_edit_with_draft_clears_the_keyboard(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_with_draft("123", 81, _project(), "Готов помочь.")

    payload = requests_mock.last_request.json()
    assert payload["chat_id"] == "123"
    assert payload["message_id"] == 81
    assert "Готов помочь." in payload["text"]
    assert payload["reply_markup"] == {"inline_keyboard": []}


def test_edit_with_retry_restores_the_generate_button(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_with_retry("123", 81, _project(), 42, "proposal generation failed")

    payload = requests_mock.last_request.json()
    assert "proposal generation failed" in payload["text"]
    assert payload["reply_markup"] == {
        "inline_keyboard": [[{"text": "Сгенерировать отклик", "callback_data": "gen:42"}]]
    }


def test_edit_expired_clears_the_keyboard_with_a_generic_message(requests_mock) -> None:
    requests_mock.post(
        "https://api.telegram.org/bottoken/editMessageText",
        json={"ok": True, "result": {}},
    )

    TelegramUpdatesClient("token").edit_expired("123", 81)

    payload = requests_mock.last_request.json()
    assert "устарел" in payload["text"]
    assert payload["reply_markup"] == {"inline_keyboard": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_telegram_updates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kwork_monitor.telegram_updates'`

- [ ] **Step 3: Implement `telegram_updates.py`**

Create `src/kwork_monitor/telegram_updates.py`:

```python
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
```

This imports `_project_header` and `_escape_limited` from `telegram.py` — both are module-level functions there after Task 3 (neither is a class attribute), so a same-package import is fine; there is no public/private enforcement in Python and this keeps the HTML-escaping and header format in exactly one place.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_telegram_updates.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kwork_monitor/telegram_updates.py tests/test_telegram_updates.py
git commit -m "feat: add long-polling Telegram client for button-driven generation"
```

---

### Task 5: Route the default (no `--with-generation`) live tick through the button

**Files:**
- Modify: `src/kwork_monitor/runner.py:32-63` (Protocols), `:232-276` (`_handle_relevant_project`/`_generate_or_none`)
- Modify: `tests/test_runner.py`

- [ ] **Step 1: Update the Protocols**

In `src/kwork_monitor/runner.py`, replace the `Store` and `Notifier` Protocol definitions:

```python
class Store(Protocol):
    """Durable cursor and processed-message store."""

    def get_cursor(self) -> int: ...

    def is_recorded(self, key: str) -> bool: ...

    def record(self, key: str, uid: int, status: str, error: str | None = None) -> None: ...

    def advance_cursor(self, uid: int) -> None: ...

    def create_pending(self, project: ProjectEmail) -> int: ...

    def delete_pending(self, pending_id: int) -> None: ...


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

    def send_with_button(self, project: ProjectEmail, pending_id: int) -> DeliveryResult: ...

    def send_parse_error_alert(
        self, message_id: str | None, reason: str
    ) -> DeliveryResult: ...
```

(Only the new `create_pending`/`delete_pending`/`send_with_button` lines are additions; everything else in these three classes is unchanged.)

- [ ] **Step 2: Replace `_handle_relevant_project` with the branching version**

Replace the existing `_handle_relevant_project` function body in `src/kwork_monitor/runner.py`:

```python
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
    if dry_run:
        _generate_or_none(dependencies, summary, project, enabled=with_generation)
        LOGGER.info("dry-run: would notify and record project UID %s", uid)
        return True
    if with_generation:
        return _notify_with_draft(dependencies, summary, project, key, uid)
    return _notify_with_button(dependencies, summary, project, key, uid)


def _notify_with_draft(
    dependencies: Dependencies,
    summary: RunSummary,
    project: ProjectEmail,
    key: str,
    uid: int,
) -> bool:
    proposal, generation_error = _generate_or_none(dependencies, summary, project, enabled=True)
    try:
        dependencies.notifier.send(project, proposal, generation_error)
    except TelegramError:
        summary.delivery_failures += 1
        LOGGER.error("Telegram project notification failed for UID %s", uid)
        return False
    dependencies.store.record(key, uid, "notified")
    summary.notified += 1
    return True


def _notify_with_button(
    dependencies: Dependencies,
    summary: RunSummary,
    project: ProjectEmail,
    key: str,
    uid: int,
) -> bool:
    pending_id = dependencies.store.create_pending(project)
    try:
        dependencies.notifier.send_with_button(project, pending_id)
    except TelegramError:
        summary.delivery_failures += 1
        dependencies.store.delete_pending(pending_id)
        LOGGER.error("Telegram project notification failed for UID %s", uid)
        return False
    dependencies.store.record(key, uid, "notified")
    summary.notified += 1
    return True
```

`_generate_or_none` itself is unchanged.

- [ ] **Step 3: Update `tests/test_runner.py` — replace the now-stale test and its neighbors**

Replace `test_live_run_generates_a_draft_without_the_dry_run_opt_in_flag` (the whole function) with:

```python
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
```

Replace `test_runner_delivers_fallback_when_proposal_generation_fails` (the whole function) with:

```python
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
```

Add two new tests after it:

```python
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
```

Now fix the two tests that build a button-path message but still assert against `deps.notifier.send` (they must assert against `send_with_button` instead, since `with_generation=False` now takes the button path):

In `test_runner_notifies_each_relevant_project_in_a_single_digest`, replace:

```python
    deps.notifier.send.return_value = DeliveryResult(message_id=9)

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.notified == 2
    assert [call.args[0].project_url for call in deps.notifier.send.call_args_list] == [
        "https://kwork.ru/projects/300",
        "https://kwork.ru/projects/301",
    ]
```

with:

```python
    deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)

    summary = run_once(deps, dry_run=False, with_generation=False)

    assert summary.notified == 2
    assert [call.args[0].project_url for call in deps.notifier.send_with_button.call_args_list] == [
        "https://kwork.ru/projects/300",
        "https://kwork.ru/projects/301",
    ]
```

In `test_runner_processes_unsorted_mail_items_by_ascending_uid`, replace `deps.notifier.send.return_value = DeliveryResult(message_id=9)` with `deps.notifier.send_with_button.return_value = DeliveryResult(message_id=9)`.

In `test_dry_run_neither_writes_state_nor_sends_telegram`, add one more assertion line after the existing ones:

```python
    deps.notifier.send_with_button.assert_not_called()
```

- [ ] **Step 4: Run the full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: PASS, all tests (the `deps` fixture's `notifier = MagicMock()` auto-creates `send_with_button`/`create_pending`/`delete_pending` as mock attributes, so no fixture changes are needed)

- [ ] **Step 5: Commit**

```bash
git add src/kwork_monitor/runner.py tests/test_runner.py
git commit -m "feat: send a generate-on-demand button instead of an eager draft by default"
```

---

### Task 6: `bot_daemon.py` — the long-polling process

**Files:**
- Create: `src/kwork_monitor/bot_daemon.py`
- Test: `tests/test_bot_daemon.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bot_daemon.py`:

```python
"""Tests for the callback-query handling loop of the interactive proposal daemon."""

from __future__ import annotations

from unittest.mock import MagicMock

from kwork_monitor.bot_daemon import poll_once
from kwork_monitor.proposal import ProposalError
from kwork_monitor.store import PendingProposal


def _callback_update(update_id: int, data: str, *, chat_id: int = 123, message_id: int = 81) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "data": data,
            "message": {"chat": {"id": chat_id}, "message_id": message_id},
        },
    }


def _pending() -> PendingProposal:
    return PendingProposal(
        id=42, project_url="https://kwork.ru/projects/9", subject="Нужен бот",
        budget="10 000 ₽", description="ТЗ.",
    )


def _deps():
    updates_client = MagicMock()
    proposal_client = MagicMock()
    store = MagicMock()
    store.get_telegram_offset.return_value = 0
    return updates_client, proposal_client, store


def test_poll_once_generates_and_edits_draft_then_deletes_pending_row() -> None:
    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = _pending()
    proposal_client.generate.return_value = "Готов помочь."

    handled = poll_once(updates_client, proposal_client, store, "Опыт: Python")

    assert handled == 1
    updates_client.answer_callback_query.assert_called_once_with("cb-5")
    proposal_client.generate.assert_called_once()
    assert proposal_client.generate.call_args.args[1] == "Опыт: Python"
    updates_client.edit_with_draft.assert_called_once()
    assert updates_client.edit_with_draft.call_args.args[:2] == ("123", 81)
    store.delete_pending.assert_called_once_with(42)
    store.set_telegram_offset.assert_called_once_with(6)


def test_poll_once_restores_button_when_generation_fails() -> None:
    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = _pending()
    proposal_client.generate.side_effect = ProposalError("offline")

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    updates_client.edit_with_retry.assert_called_once_with(
        "123", 81, updates_client.edit_with_retry.call_args.args[2], 42, "proposal generation failed"
    )
    store.delete_pending.assert_not_called()


def test_poll_once_reports_an_expired_request_for_a_missing_pending_row() -> None:
    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [_callback_update(5, "gen:42")]
    store.get_pending.return_value = None

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    updates_client.edit_expired.assert_called_once_with("123", 81)
    proposal_client.generate.assert_not_called()


def test_poll_once_ignores_updates_without_a_recognized_callback() -> None:
    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [
        {"update_id": 5, "message": {"text": "hello"}},
        _callback_update(6, "not-a-generate-callback"),
    ]

    handled = poll_once(updates_client, proposal_client, store, "Опыт: Python")

    assert handled == 2
    proposal_client.generate.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(7)


def test_poll_once_advances_offset_past_a_message_without_the_expected_shape() -> None:
    updates_client, proposal_client, store = _deps()
    updates_client.get_updates.return_value = [
        {
            "update_id": 5,
            "callback_query": {"id": "cb-5", "data": "gen:42", "message": {}},
        }
    ]

    poll_once(updates_client, proposal_client, store, "Опыт: Python")

    updates_client.answer_callback_query.assert_called_once_with("cb-5")
    store.get_pending.assert_not_called()
    store.set_telegram_offset.assert_called_once_with(6)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_bot_daemon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kwork_monitor.bot_daemon'`

- [ ] **Step 3: Implement `bot_daemon.py`**

Create `src/kwork_monitor/bot_daemon.py`:

```python
"""Long-polling daemon: generates a Kwork proposal draft when its button is clicked."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time

from .config import load_settings, read_profile
from .models import ProjectEmail
from .proposal import ProposalClient, ProposalError
from .store import StateStore
from .telegram_updates import TelegramUpdatesClient


LOGGER = logging.getLogger(__name__)
_RETRY_DELAY_SECONDS = 5
_GENERATION_FAILURE_REASON = "proposal generation failed"


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
    _, secrets = load_settings(arguments.config, os.environ)
    profile = read_profile(arguments.config.parent / "PROFILE.md")
    store = StateStore(arguments.config.parent / "seen_orders.db")
    updates_client = TelegramUpdatesClient(secrets.telegram_bot_token)
    proposal_client = ProposalClient(secrets.codeassist_base_url)
    run_forever(updates_client, proposal_client, store, profile)
    return 0


def run_forever(updates_client, proposal_client, store, profile: str) -> None:
    """Poll indefinitely; a failed poll waits and retries rather than crashing."""
    while True:
        try:
            poll_once(updates_client, proposal_client, store, profile)
        except Exception:
            LOGGER.error("update polling failed, retrying in %ss", _RETRY_DELAY_SECONDS)
            time.sleep(_RETRY_DELAY_SECONDS)


def poll_once(updates_client, proposal_client, store, profile: str) -> int:
    """Fetch and handle one batch of updates starting at the stored offset.

    Returns the number of updates received (handled or skipped), for tests.
    """
    offset = store.get_telegram_offset()
    updates = updates_client.get_updates(offset)
    for update in updates:
        try:
            _handle_update(update, updates_client, proposal_client, store, profile)
        except Exception:
            LOGGER.error("failed to handle update_id %s", update.get("update_id"))
    if updates:
        store.set_telegram_offset(updates[-1]["update_id"] + 1)
    return len(updates)


def _handle_update(update: dict, updates_client, proposal_client, store, profile: str) -> None:
    callback = update.get("callback_query")
    if callback is None:
        return
    updates_client.answer_callback_query(callback["id"])

    data = callback.get("data", "")
    if not isinstance(data, str) or not data.startswith("gen:"):
        return
    try:
        pending_id = int(data[len("gen:") :])
    except ValueError:
        return

    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    if chat_id is None or message_id is None:
        return
    chat_id = str(chat_id)

    pending = store.get_pending(pending_id)
    if pending is None:
        updates_client.edit_expired(chat_id, message_id)
        return

    project = ProjectEmail(
        message_id="",
        uid=0,
        subject=pending.subject,
        project_url=pending.project_url,
        budget=pending.budget,
        description=pending.description,
    )
    try:
        draft = proposal_client.generate(project, profile)
    except ProposalError:
        LOGGER.error("proposal generation failed for pending id %s", pending_id)
        updates_client.edit_with_retry(chat_id, message_id, project, pending_id, _GENERATION_FAILURE_REASON)
        return

    updates_client.edit_with_draft(chat_id, message_id, project, draft)
    store.delete_pending(pending_id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Handle Kwork monitor 'Сгенерировать отклик' button clicks"
    )
    parser.add_argument("--config", type=Path, required=True)
    return parser


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_bot_daemon.py -v`
Expected: PASS

- [ ] **Step 5: Run the entire suite once more**

Run: `.venv/bin/python -m pytest -v`
Expected: PASS, all tests across every file

- [ ] **Step 6: Commit**

```bash
git add src/kwork_monitor/bot_daemon.py tests/test_bot_daemon.py
git commit -m "feat: add the interactive proposal-generation long-polling daemon"
```

---

### Task 7: systemd unit and README

**Files:**
- Create: `ops/kwork-monitor-bot.service`
- Modify: `README.md`

- [ ] **Step 1: Create the systemd unit**

Create `ops/kwork-monitor-bot.service`:

```ini
[Unit]
Description=Kwork monitor - interactive proposal button daemon
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/kwork-monitor
EnvironmentFile=/root/kwork-monitor/.env
ExecStart=/root/kwork-monitor/.venv/bin/python -m kwork_monitor.bot_daemon --config /root/kwork-monitor/config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Document manual install and the two-process model in README**

In `README.md`, replace the single cron-line block near the end of "Manual server installation" (the block starting `Only after that succeeds...`) with:

```markdown
Only after that succeeds and the notification content is correct, add this cron
line manually:

```cron
17 * * * * cd /root/kwork-monitor && set -a && . ./.env && set +a && ./.venv/bin/python -m kwork_monitor.cli --config ./config.yaml >> ./kwork-monitor.log 2>&1
```

This cron tick sends a project notification with a **"Сгенерировать отклик"**
button instead of an eager draft. A second, always-running process handles
button clicks and must be installed separately:

```bash
install -m 644 ops/kwork-monitor-bot.service /etc/systemd/system/kwork-monitor-bot.service
systemctl daemon-reload
systemctl enable --now kwork-monitor-bot
journalctl -u kwork-monitor-bot -f
```

`--with-generation` still exists as a manual override (`--config ./config.yaml
--with-generation`) that generates a draft immediately for every relevant
project in that one tick, without touching the button/daemon path — useful for
a backfill or for testing generation quality against the current `PROFILE.md`.
```

- [ ] **Step 3: Commit**

```bash
git add ops/kwork-monitor-bot.service README.md
git commit -m "docs: document the button daemon's systemd unit and install steps"
```

---

### Task 8: Deploy to `n` and re-enable cron

**Files:** none (server-side operations only, no repo changes)

This task has no automated tests — it is a deployment checklist, run manually after Task 7 is merged.

- [ ] **Step 1: Pull the branch on `n`**

```bash
ssh n 'cd /root/kwork-monitor && git fetch origin && git checkout feat/kwork-email-monitor && git pull'
```

- [ ] **Step 2: Reinstall the package (picks up no new dependencies, but re-syncs `src/`)**

```bash
ssh n 'cd /root/kwork-monitor && .venv/bin/pip install -e ".[test]" && .venv/bin/python -m pytest -q'
```
Expected: all tests pass on the server's Python 3.10 the same as locally.

- [ ] **Step 3: Install and start the systemd unit**

```bash
ssh n 'install -m 644 /root/kwork-monitor/ops/kwork-monitor-bot.service /etc/systemd/system/kwork-monitor-bot.service && systemctl daemon-reload && systemctl enable --now kwork-monitor-bot && systemctl status kwork-monitor-bot --no-pager'
```
Expected: `active (running)`.

- [ ] **Step 4: Replace the real `PROFILE.md` on the server with the stack brief from the spec**

Write the "PROFILE.md — реальный стек" section of
`docs/superpowers/specs/2026-09-08-kwork-interactive-proposals-design.md` to
`/root/kwork-monitor/PROFILE.md` on `n` (per this project's global rule: a
local Python script + `scp`, not a heredoc over SSH — see `~/CLAUDE.md`).
Confirm the prices/deadlines line stays as `[пользователь впишет сам]` or is
filled in by the user, never invented.

- [ ] **Step 5: Re-enable the paused cron line**

```bash
ssh n "crontab -l | sed 's#^# PAUSED until interactive-button feature ships: 17 \* \* \* \* cd /root/kwork-monitor.*$##' | grep -v '^$' > /tmp/cron_new.txt"
ssh n 'echo "17 * * * * cd /root/kwork-monitor && set -a && . ./.env && set +a && ./.venv/bin/python -m kwork_monitor.cli --config ./config.yaml >> ./kwork-monitor.log 2>&1" >> /tmp/cron_new.txt'
ssh n 'crontab /tmp/cron_new.txt && crontab -l | grep kwork'
```
Expected: exactly one active (uncommented) `kwork-monitor` cron line, all other unrelated cron entries on `n` untouched.

- [ ] **Step 6: End-to-end check**

Wait for the next `:17` tick (or trigger one manually per README's dry-run
instructions against a real or fixture message), confirm the Telegram message
arrives with the button and no draft, click it, confirm the message is edited
in place with a generated draft referencing only facts from the new
`PROFILE.md`, and that the button disappears.
