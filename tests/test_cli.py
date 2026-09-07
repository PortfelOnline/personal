"""CLI safety tests that run without mail, Telegram, or SQLite side effects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from kwork_monitor import cli


FIXTURE = Path(__file__).parent / "fixtures" / "kwork_project_valid.eml"


def test_configured_dry_run_does_not_create_sqlite_files(
    tmp_path: Path, monkeypatch
) -> None:
    """Previewing configured mail must not initialize SQLite or its WAL files."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "imap: {host: imap.example.test, mailbox: INBOX}\n"
        "filters: {senders: [noreply@kwork.ru], subject_patterns: [Новый], keywords: [telegram]}\n",
        encoding="utf-8",
    )
    (tmp_path / "PROFILE.md").write_text("Test profile", encoding="utf-8")
    state_path = tmp_path / "seen_orders.db"
    state_path.write_bytes(b"must remain untouched")
    original_state = state_path.read_bytes()
    _set_secrets(monkeypatch)
    source = MagicMock()
    source.fetch_after.return_value = []
    monkeypatch.setattr(cli.ImapSource, "from_settings", lambda *_args, **_kwargs: source)
    monkeypatch.setattr("kwork_monitor.runner._open_lock_file", lambda _path: (tmp_path / "lock").open("a+"))

    assert cli.main(["--config", str(config), "--dry-run"]) == 0
    assert state_path.read_bytes() == original_state
    assert list(tmp_path.glob("seen_orders.db*")) == [state_path]


def test_fixture_dry_run_needs_no_writable_sibling_file(tmp_path: Path) -> None:
    """Fixture mode must work when its directory cannot host a lock file."""
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture = fixture_dir / "sample.eml"
    fixture.write_bytes(FIXTURE.read_bytes())
    fixture_dir.chmod(0o555)
    try:
        assert cli.main(["--dry-run", "--fixture", str(fixture)]) == 0
        assert list(fixture_dir.iterdir()) == [fixture]
    finally:
        fixture_dir.chmod(0o755)


def test_missing_fixture_returns_concise_error_without_traceback(
    tmp_path: Path, caplog
) -> None:
    """A typo in a local fixture path should be a normal CLI input error."""
    missing = tmp_path / "missing.eml"

    assert cli.main(["--dry-run", "--fixture", str(missing)]) == 2
    assert "fixture could not be read" in caplog.text
    assert "Traceback" not in caplog.text


def _set_secrets(monkeypatch) -> None:
    monkeypatch.setenv("KWORK_IMAP_USERNAME", "monitor@example.test")
    monkeypatch.setenv("KWORK_IMAP_PASSWORD", "test-only")
    monkeypatch.setenv("KWORK_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("KWORK_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("KWORK_CODEASSIST_BASE_URL", "http://127.0.0.1:8080/v1")
