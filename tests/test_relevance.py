"""Tests for deterministic project keyword filtering."""

from __future__ import annotations

from kwork_monitor.models import ProjectEmail
from kwork_monitor.relevance import is_relevant


def _project(*, subject: str = "Нужен TELEGRAM-бот", description: str | None = "Создать AI-агент") -> ProjectEmail:
    return ProjectEmail(
        message_id="<project-1@example.kwork.ru>",
        uid=101,
        subject=subject,
        project_url="https://kwork.ru/projects/1",
        budget="10 000 ₽",
        description=description,
    )


def test_relevance_matches_case_insensitively_in_subject_or_description() -> None:
    """A regression to case-sensitive matching would miss suitable projects."""
    project = _project()

    assert is_relevant(project, ("ai-агент", "telegram-бот")) is True
    assert is_relevant(project, ("дизайн интерьера",)) is False


def test_relevance_collapses_whitespace_in_project_and_keyword() -> None:
    """A line break in an email must not prevent a configured phrase match."""
    project = _project(subject="Нужен Telegram\n    бот", description=None)

    assert is_relevant(project, ("telegram   бот",)) is True


def test_relevance_handles_missing_description_without_matching_empty_keyword() -> None:
    """An absent description must not turn an empty keyword into a match."""
    project = _project(subject="Только разработка", description=None)

    assert is_relevant(project, ("", "   ")) is False
