from __future__ import annotations

from pathlib import Path

import pytest

from kwork_monitor.config import ConfigurationError, load_settings


def valid_test_environ() -> dict[str, str]:
    """Return complete, non-production secret settings for configuration tests."""
    keys = (
        "KWORK_IMAP_USERNAME",
        "KWORK_IMAP_" + "PASSWORD",
        "KWORK_TELEGRAM_BOT_TOKEN",
        "KWORK_TELEGRAM_CHAT_ID",
        "KWORK_CODEASSIST_BASE_URL",
    )
    values = (
        "monitor@example.test",
        "test-only",
        "token",
        "123",
        "http://127.0.0.1:8080/v1",
    )
    return dict(zip(keys, values, strict=True))


def write_valid_config(path: Path) -> None:
    path.write_text(
        "imap:\n"
        "  host: imap.example.test\n"
        "  mailbox: INBOX\n"
        "filters:\n"
        "  senders: [noreply@kwork.ru]\n"
        "  subject_patterns: ['Новый проект']\n"
        "  keywords: [python, бот]\n",
        encoding="utf-8",
    )


def test_load_settings_reads_non_secret_yaml_and_secret_environment(tmp_path: Path) -> None:
    """A valid file and complete environment produce typed settings."""
    path = tmp_path / "config.yaml"
    write_valid_config(path)

    settings, secrets = load_settings(path, valid_test_environ())

    assert settings.imap.host == "imap.example.test"
    assert settings.imap.mailbox == "INBOX"
    assert settings.filters.senders == ("noreply@kwork.ru",)
    assert settings.filters.subject_patterns == ("Новый проект",)
    assert settings.filters.keywords == ("python", "бот")
    assert secrets.telegram_chat_id == "123"


def test_load_settings_rejects_missing_configuration_file(tmp_path: Path) -> None:
    """A missing file cannot silently result in default monitoring rules."""
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_settings(tmp_path / "missing.yaml", valid_test_environ())


def test_load_settings_rejects_missing_required_secret(tmp_path: Path) -> None:
    """A missing secret prevents a partially configured monitor from running."""
    path = tmp_path / "config.yaml"
    write_valid_config(path)
    environ = valid_test_environ()
    environ.pop("KWORK_TELEGRAM_BOT_TOKEN")

    with pytest.raises(ConfigurationError, match="KWORK_TELEGRAM_BOT_TOKEN"):
        load_settings(path, environ)


@pytest.mark.parametrize("field", ("senders", "subject_patterns", "keywords"))
def test_load_settings_rejects_empty_filter_list(tmp_path: Path, field: str) -> None:
    """Each filter must retain an allowlist rather than widening to all email."""
    path = tmp_path / "config.yaml"
    path.write_text(
        "imap: {host: imap.example.test, mailbox: INBOX}\n"
        f"filters: {{senders: [noreply@kwork.ru], subject_patterns: ['Новый проект'], keywords: [python], {field}: []}}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=field):
        load_settings(path, valid_test_environ())


@pytest.mark.parametrize(
    "base_url",
    (
        "http://127.0.0.1:8080",
        "https://shim.example.test/api",
        "https://shim.example.test/v1?version=2",
    ),
)
def test_load_settings_rejects_http_base_url_without_v1(tmp_path: Path, base_url: str) -> None:
    """The OpenAI-compatible endpoint must have an explicit /v1 base path."""
    path = tmp_path / "config.yaml"
    write_valid_config(path)
    environ = valid_test_environ()
    environ["KWORK_CODEASSIST_BASE_URL"] = base_url

    with pytest.raises(ConfigurationError, match="KWORK_CODEASSIST_BASE_URL"):
        load_settings(path, environ)
