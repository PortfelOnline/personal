"""Tests for parsing official Kwork notification emails without web access."""

from __future__ import annotations

from pathlib import Path

import pytest

from kwork_monitor.email_parser import EmailParseError, parse_project_email


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    """Read a sanitized RFC 822 fixture as the IMAP client would provide it."""
    return (FIXTURES / name).read_bytes()


def test_parser_extracts_identity_link_budget_and_plain_text_description() -> None:
    """A plain-text notification produces a bounded project value object."""
    project = parse_project_email(load_fixture("kwork_project_valid.eml"), uid=42)

    assert project.message_id == "<project-100@example.kwork.ru>"
    assert project.uid == 42
    assert project.subject == "Новый проект: Telegram-бот"
    assert project.project_url == "https://kwork.ru/projects/100"
    assert project.budget == "10 000 ₽"
    assert project.description is not None
    assert "Telegram-бот" in project.description


def test_parser_rejects_a_notification_without_project_link() -> None:
    """A notification without a Kwork project URL must not reach generation."""
    with pytest.raises(EmailParseError, match="project URL"):
        parse_project_email(load_fixture("kwork_project_malformed.eml"), uid=43)


def test_parser_uses_html_when_no_plain_text_part_exists() -> None:
    """HTML-only notifications retain readable text and the exact Kwork URL."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-102@example.kwork.ru>",
            b"Subject: HTML project",
            b"MIME-Version: 1.0",
            b"Content-Type: text/html; charset=utf-8",
            b"",
            b"<p>Telegram-\xd0\xb1\xd0\xbe\xd1\x82</p><a href=\"https://kwork.ru/projects/102\">Project</a>",
        )
    )

    project = parse_project_email(raw, uid=44)

    assert project.project_url == "https://kwork.ru/projects/102"
    assert project.description is not None
    assert "Telegram-бот" in project.description


def test_parser_rejects_subdomain_project_url() -> None:
    """A lookalike Kwork hostname cannot be treated as an official project URL."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-103@example.kwork.ru>",
            b"Subject: Unsafe link",
            b"Content-Type: text/plain; charset=utf-8",
            b"",
            b"https://evil.kwork.ru/projects/103",
        )
    )

    with pytest.raises(EmailParseError, match="project URL"):
        parse_project_email(raw, uid=45)


def test_parser_caps_description_before_it_reaches_the_generator() -> None:
    """An oversized notification cannot expand the downstream prompt unboundedly."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-104@example.kwork.ru>",
            b"Subject: Long project",
            b"Content-Type: text/plain; charset=utf-8",
            b"",
            b"https://kwork.ru/projects/104",
            b"x" * 6_500,
        )
    )

    project = parse_project_email(raw, uid=46)

    assert project.description is not None
    assert len(project.description) == 6_000
