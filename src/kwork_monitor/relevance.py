"""Deterministic project relevance filtering."""

from __future__ import annotations

import re

from .models import ProjectEmail


def is_relevant(project: ProjectEmail, keywords: tuple[str, ...]) -> bool:
    """Return whether a normalized configured keyword appears in the project."""
    project_text = _normalize(f"{project.subject} {project.description or ''}")
    return any(
        keyword and keyword in project_text
        for keyword in (_normalize(item) for item in keywords)
    )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
