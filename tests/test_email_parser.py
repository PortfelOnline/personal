"""Tests for parsing official Kwork notification emails without web access."""

from __future__ import annotations

from pathlib import Path

import pytest

from kwork_monitor.email_parser import (
    EmailParseError,
    parse_project_email,
    parse_project_emails,
)


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
    with pytest.raises(EmailParseError, match="project URL") as error:
        parse_project_email(load_fixture("kwork_project_malformed.eml"), uid=43)

    assert error.value.message_id == "<project-101@example.kwork.ru>"
    assert error.value.reason == "missing Message-ID, subject, or project URL"


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


def test_parser_returns_each_project_from_an_html_digest() -> None:
    """A Kwork digest produces separate project records rather than just its first link."""
    raw = b"\n".join(
        (
            b"Message-ID: <digest-200@example.kwork.ru>",
            b"Subject: New Kwork projects",
            b"MIME-Version: 1.0",
            b"Content-Type: text/html; charset=utf-8",
            b"",
            b"<table>",
            b'<tr><td><a href="https://kwork.ru/projects/200">Telegram bot</a></td><td>Budget: 5 000 RUB</td></tr>',
            b'<tr><td><a href="https://kwork.ru/projects/201">Logo design</a></td><td>Budget: 3 000 RUB</td></tr>',
            b"</table>",
        )
    )

    projects = parse_project_emails(raw, uid=50)

    assert [(project.project_url, project.budget) for project in projects] == [
        ("https://kwork.ru/projects/200", "5 000 RUB"),
        ("https://kwork.ru/projects/201", "3 000 RUB"),
    ]
    assert projects[0].description is not None
    assert "Telegram bot" in projects[0].description
    assert "Logo design" not in projects[0].description
    assert projects[1].description is not None
    assert "Logo design" in projects[1].description
    assert "Telegram bot" not in projects[1].description


def test_parser_returns_each_project_from_kwork_new_offer_links() -> None:
    """Current Kwork digests use one unique ``/new_offer`` link per listed row."""
    raw = b"\n".join(
        (
            b"Message-ID: <digest-202@example.kwork.ru>",
            b"Subject: New Kwork projects",
            b"MIME-Version: 1.0",
            b"Content-Type: text/html; charset=utf-8",
            b"",
            b"<table>",
            b'<tr><td><a href="https://kwork.ru/new_offer?offer=202">Telegram bot</a></td><td>Budget: 5 000 RUB</td></tr>',
            b'<tr><td><a href="https://kwork.ru/new_offer?offer=203">Telegram integration</a></td><td>Budget: 7 000 RUB</td></tr>',
            b"</table>",
        )
    )

    projects = parse_project_emails(raw, uid=52)

    assert [project.project_url for project in projects] == [
        "https://kwork.ru/new_offer?offer=202",
        "https://kwork.ru/new_offer?offer=203",
    ]


def test_parser_keeps_plain_text_data_with_its_leading_new_offer_link() -> None:
    """A plain digest with links first must not attach one row to the next URL."""
    raw = b"\n".join(
        (
            b"Message-ID: <digest-204@example.kwork.ru>",
            b"Subject: New Kwork projects",
            b"Content-Type: text/plain; charset=utf-8",
            b"",
            b"https://kwork.ru/new_offer?offer=204",
            b"Telegram bot",
            b"Budget: 5 000 RUB",
            b"https://kwork.ru/new_offer?offer=205",
            b"Logo design",
            b"Budget: 3 000 RUB",
        )
    )

    projects = parse_project_emails(raw, uid=54)

    assert [(project.project_url, project.budget) for project in projects] == [
        ("https://kwork.ru/new_offer?offer=204", "5 000 RUB"),
        ("https://kwork.ru/new_offer?offer=205", "3 000 RUB"),
    ]
    assert projects[0].description is not None
    assert "Telegram bot" in projects[0].description
    assert "Logo design" not in projects[0].description
    assert projects[1].description is not None
    assert "Logo design" in projects[1].description
    assert "Telegram bot" not in projects[1].description


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


def test_parser_skips_a_malformed_url_before_a_valid_kwork_project_url() -> None:
    """An invalid URL candidate cannot abort parsing of a later valid project URL."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-105@example.kwork.ru>",
            b"Subject: Malformed URL first",
            b"Content-Type: text/plain; charset=utf-8",
            b"",
            b"https://[kwork.ru https://kwork.ru/projects/105",
        )
    )

    project = parse_project_email(raw, uid=47)

    assert project.project_url == "https://kwork.ru/projects/105"


def test_parser_decodes_an_unknown_part_charset_with_safe_fallback() -> None:
    """An unrecognized MIME charset cannot turn a valid notification into a crash."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-106@example.kwork.ru>",
            b"Subject: Unknown charset",
            b"MIME-Version: 1.0",
            b"Content-Type: text/plain; charset=x-unknown-charset",
            b"Content-Transfer-Encoding: base64",
            b"",
            b"aHR0cHM6Ly9rd29yay5ydS9wcm9qZWN0cy8xMDY=",
        )
    )

    project = parse_project_email(raw, uid=48)

    assert project.project_url == "https://kwork.ru/projects/106"


def test_parser_uses_html_fallback_when_base64_plain_part_is_empty() -> None:
    """An empty plain alternative cannot hide a valid HTML project notification."""
    raw = b"\n".join(
        (
            b"Message-ID: <project-107@example.kwork.ru>",
            b"Subject: Empty plain alternative",
            b"MIME-Version: 1.0",
            b'Content-Type: multipart/alternative; boundary="empty-plain"',
            b"",
            b"--empty-plain",
            b"Content-Type: text/plain; charset=utf-8",
            b"Content-Transfer-Encoding: base64",
            b"",
            b"Cg==",
            b"--empty-plain",
            b"Content-Type: text/html; charset=utf-8",
            b"",
            b'<a href="https://kwork.ru/projects/107">Open project</a>',
            b"--empty-plain--",
        )
    )

    project = parse_project_email(raw, uid=49)

    assert project.project_url == "https://kwork.ru/projects/107"
