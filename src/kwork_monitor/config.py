"""Safe loading and validation of non-secret and secret monitor settings."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .models import FilterSettings, ImapSettings, SecretSettings, Settings


class ConfigurationError(ValueError):
    """Raised when monitor configuration is missing or unsafe to use."""


_REQUIRED_ENVIRONMENT = {
    "KWORK_IMAP_USERNAME": "imap_username",
    "KWORK_IMAP_PASSWORD": "imap_password",
    "KWORK_TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "KWORK_TELEGRAM_CHAT_ID": "telegram_chat_id",
    "KWORK_CODEASSIST_BASE_URL": "codeassist_base_url",
}


def load_settings(
    config_path: Path, environ: Mapping[str, str]
) -> tuple[Settings, SecretSettings]:
    """Load non-secrets from YAML and mandatory secrets from ``environ``.

    This function deliberately does not log configuration data: environment
    values can contain credentials and tokens.
    """
    data = _load_yaml(config_path)
    settings = Settings(
        imap=ImapSettings(
            host=_required_text(_section(data, "imap"), "host", "imap"),
            mailbox=_required_text(_section(data, "imap"), "mailbox", "imap"),
        ),
        filters=FilterSettings(
            senders=_required_text_list(_section(data, "filters"), "senders"),
            subject_patterns=_required_text_list(
                _section(data, "filters"), "subject_patterns"
            ),
            keywords=_required_text_list(_section(data, "filters"), "keywords"),
        ),
    )
    secrets = _load_secrets(environ)
    return settings, secrets


def _load_yaml(config_path: Path) -> Mapping[str, object]:
    if not config_path.is_file():
        raise ConfigurationError(f"configuration file does not exist: {config_path}")

    try:
        with config_path.open(encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError("configuration YAML could not be read") from error

    if not isinstance(data, Mapping):
        raise ConfigurationError("configuration YAML must contain a mapping")
    return data


def _section(data: Mapping[str, object], name: str) -> Mapping[str, object]:
    value = data.get(name)
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"configuration section {name!r} must be a mapping")
    return value


def _required_text(section: Mapping[str, object], name: str, section_name: str) -> str:
    value = section.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{section_name}.{name} must be a non-empty string")
    return value.strip()


def _required_text_list(section: Mapping[str, object], name: str) -> tuple[str, ...]:
    value = section.get(name)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"filters.{name} must be a non-empty list")

    values = tuple(_list_item(item, name) for item in value)
    return values


def _list_item(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"filters.{name} must contain non-empty strings")
    return value.strip()


def _load_secrets(environ: Mapping[str, str]) -> SecretSettings:
    values: dict[str, str] = {}
    for environment_name, field_name in _REQUIRED_ENVIRONMENT.items():
        value = environ.get(environment_name)
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"missing required environment variable: {environment_name}")
        values[field_name] = value.strip()

    _validate_codeassist_base_url(values["codeassist_base_url"])
    return SecretSettings(**values)


def _validate_codeassist_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not base_url.endswith("/v1")
    ):
        raise ConfigurationError(
            "KWORK_CODEASSIST_BASE_URL must be an http(s) URL ending in /v1"
        )
