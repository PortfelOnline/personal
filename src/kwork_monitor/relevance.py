"""Deterministic project relevance and budget filtering."""

from __future__ import annotations

import re

from .models import ProjectEmail


_DIGITS = re.compile(r"\d+")


def is_relevant(
    project: ProjectEmail, keywords: tuple[str, ...], minimum_budget_rub: int
) -> bool:
    """Return whether a project matches skills and a confirmed budget floor."""
    budget = budget_rub(project.budget)
    if budget is None or budget < minimum_budget_rub:
        return False
    project_text = _normalize(f"{project.subject} {project.description or ''}")
    return any(
        keyword and keyword in project_text
        for keyword in (_normalize(item) for item in keywords)
    )


def budget_rub(value: str | None) -> int | None:
    """Parse a displayed whole-ruble budget such as ``20 000 ₽`` safely."""
    if not isinstance(value, str):
        return None
    digits = "".join(_DIGITS.findall(value))
    return int(digits) if digits else None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
