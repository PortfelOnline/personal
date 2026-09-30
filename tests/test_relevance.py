"""Tests for deterministic project keyword filtering."""

from __future__ import annotations

from kwork_monitor.models import ProjectEmail
from kwork_monitor.relevance import is_relevant


def _project(
    *,
    subject: str = "Нужен TELEGRAM-бот",
    description: str | None = "Создать AI-агент",
    budget: str | None = "10 000 ₽",
) -> ProjectEmail:
    return ProjectEmail(
        message_id="<project-1@example.kwork.ru>",
        uid=101,
        subject=subject,
        project_url="https://kwork.ru/projects/1",
        budget=budget,
        description=description,
    )


def test_relevance_matches_case_insensitively_in_subject_or_description() -> None:
    """A regression to case-sensitive matching would miss suitable projects."""
    project = _project()

    assert is_relevant(project, ("ai-агент", "telegram-бот"), 20_000) is False
    assert is_relevant(project, ("ai-агент", "telegram-бот"), 10_000) is True
    assert is_relevant(project, ("дизайн интерьера",), 10_000) is False


def test_relevance_collapses_whitespace_in_project_and_keyword() -> None:
    """A line break in an email must not prevent a configured phrase match."""
    project = _project(subject="Нужен Telegram\n    бот", description=None)

    assert is_relevant(project, ("telegram   бот",), 10_000) is True


def test_relevance_rejects_missing_or_unparseable_budget() -> None:
    """A project without a confirmed budget must not spend notification capacity."""
    assert is_relevant(_project(budget=None), ("telegram",), 20_000) is False
    assert is_relevant(_project(budget="договорная"), ("telegram",), 20_000) is False


def test_relevance_handles_missing_description_without_matching_empty_keyword() -> None:
    """An absent description must not turn an empty keyword into a match."""
    project = _project(subject="Только разработка", description=None)

    assert is_relevant(project, ("", "   "), 10_000) is False
