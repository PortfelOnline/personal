"""Tests for the bounded Code Assist proposal client."""

from __future__ import annotations

import pytest
import requests

from kwork_monitor.models import ProjectEmail
from kwork_monitor.proposal import ProposalClient, ProposalError


def _project() -> ProjectEmail:
    return ProjectEmail(
        message_id="<project-2@example.kwork.ru>",
        uid=102,
        subject="Нужен Telegram-бот",
        project_url="https://kwork.ru/projects/2",
        budget="10 000 ₽",
        description="Нужен бот с AI-агентом.",
    )


def test_generator_sends_profile_and_project_as_separate_messages(requests_mock) -> None:
    """Combining profile with the project risks losing their distinct context."""
    requests_mock.post(
        "http://shim.test/v1/chat/completions",
        json={"choices": [{"message": {"content": "Готов подготовить бота."}}]},
    )

    proposal = ProposalClient("http://shim.test/v1").generate(_project(), "Опыт: Python")

    assert proposal == "Готов подготовить бота."
    request_json = requests_mock.last_request.json()
    assert requests_mock.last_request.timeout == 30
    assert request_json["messages"][0]["role"] == "system"
    assert "Верни только короткий черновик отклика на русском" in request_json["messages"][0]["content"]
    assert request_json["messages"][1] == {"role": "user", "content": "Профиль:\nОпыт: Python"}
    assert request_json["messages"][2] == {
        "role": "user",
        "content": "Проект:\nТема: Нужен Telegram-бот\nБюджет: 10 000 ₽\nОписание: Нужен бот с AI-агентом.",
    }


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": "  "}}]},
    ],
)
def test_generator_rejects_missing_or_empty_draft(response: dict[str, object], requests_mock) -> None:
    """Malformed bridge output must not be presented as a generated proposal."""
    requests_mock.post("http://shim.test/v1/chat/completions", json=response)

    with pytest.raises(ProposalError, match="invalid response"):
        ProposalClient("http://shim.test/v1").generate(_project(), "Опыт: Python")


def test_generator_wraps_http_unavailability_without_response_details(monkeypatch) -> None:
    """A transport error must become a controlled error without leaking details."""
    def unavailable(*args: object, **kwargs: object) -> None:
        raise requests.Timeout("network-specific detail")

    monkeypatch.setattr("kwork_monitor.proposal.requests.post", unavailable)

    with pytest.raises(ProposalError, match="unavailable") as error:
        ProposalClient("http://shim.test/v1").generate(_project(), "Опыт: Python")

    assert "network-specific detail" not in str(error.value)
