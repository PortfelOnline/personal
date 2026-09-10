"""Typed value objects shared by monitor components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImapSettings:
    """Non-secret IMAP connection settings."""

    host: str
    mailbox: str


@dataclass(frozen=True)
class FilterSettings:
    """Allowlists used before an email body is processed."""

    senders: tuple[str, ...]
    subject_patterns: tuple[str, ...]
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Settings:
    """Non-secret configuration loaded from YAML."""

    imap: ImapSettings
    filters: FilterSettings


@dataclass(frozen=True)
class SecretSettings:
    """Credentials and endpoint configuration supplied by the environment."""

    imap_username: str
    imap_password: str
    telegram_bot_token: str
    telegram_chat_id: str
    codeassist_base_url: str


@dataclass(frozen=True)
class ProjectEmail:
    """The relevant details extracted from one official notification email."""

    message_id: str
    uid: int
    subject: str
    project_url: str | None
    budget: str | None
    description: str | None


@dataclass(frozen=True)
class DeliveryResult:
    """The Telegram message identity returned after successful delivery."""

    message_id: int
