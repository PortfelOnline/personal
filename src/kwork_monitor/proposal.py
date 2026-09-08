"""Bounded client for generating a Kwork response draft through Code Assist."""

from __future__ import annotations

from collections.abc import Mapping

import requests

from .models import ProjectEmail


class ProposalError(RuntimeError):
    """Raised when a proposal cannot be generated safely."""


_SYSTEM_PROMPT = (
    "Верни только короткий черновик отклика на русском; "
    "не утверждай факты, отсутствующие в проекте или профиле; "
    "если ТЗ неполное, задай один уточняющий вопрос"
)


class ProposalClient:
    """Call an OpenAI-compatible local Code Assist bridge."""

    def __init__(self, base_url: str) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"

    def generate(self, project: ProjectEmail, profile: str) -> str:
        """Generate a short draft from separately supplied profile and project data."""
        payload = {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Профиль:\n{profile}"},
                {"role": "user", "content": _project_message(project)},
            ]
        }
        try:
            response = requests.post(self._url, json=payload, timeout=30)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as error:
            raise ProposalError("proposal service unavailable") from error

        draft = _extract_draft(body)
        if draft is None:
            raise ProposalError("invalid response from proposal service")
        return draft


def _project_message(project: ProjectEmail) -> str:
    return (
        "Проект:\n"
        f"Тема: {project.subject}\n"
        f"Бюджет: {project.budget or 'не указан'}\n"
        f"Описание: {project.description or 'не указано'}"
    )


def _extract_draft(body: object) -> str | None:
    if not isinstance(body, Mapping):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        return None
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()
