from __future__ import annotations

from dataclasses import dataclass, field
import ssl

import pytest

from kwork_monitor.imap_source import ImapSource, ImapSourceError
from kwork_monitor.models import FilterSettings, ImapSettings, SecretSettings, Settings


RAW_A = "From: noreply@kwork.ru\r\nSubject: Новый проект: A\r\nMessage-ID: <a@test>\r\n\r\nA".encode()
RAW_B = "From: noreply@kwork.ru\r\nSubject: Новый проект: B\r\nMessage-ID: <b@test>\r\n\r\nB".encode()
RAW_OTHER = "From: other@example.test\r\nSubject: Новый проект: C\r\nMessage-ID: <c@test>\r\n\r\nC".encode()


@dataclass
class FakeImapClient:
    messages: dict[int, bytes]
    calls: list[tuple[str, str, str]] = field(default_factory=list)
    search_status: str = "OK"
    fetch_status: str = "OK"
    seen: bool = False
    login_calls: list[tuple[str, str]] = field(default_factory=list)
    select_calls: list[tuple[str, bool]] = field(default_factory=list)

    def login(self, username: str, password: str):
        self.login_calls.append((username, password))
        return "OK", [b"authenticated"]

    def select(self, mailbox: str, *, readonly: bool):
        self.select_calls.append((mailbox, readonly))
        return "OK", [b"3"]

    def uid(self, command: str, *arguments: str):
        self.calls.append((command, *(str(argument) for argument in arguments)))
        if command == "SEARCH":
            return self.search_status, [b"7 8 9"]
        if self.fetch_status != "OK":
            return self.fetch_status, [None]
        uid = int(arguments[0])
        item = self.messages[uid]
        if arguments[1] == "(RFC822.HEADER)":
            item = item.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"
        elif arguments[1] == "(RFC822)":
            self.seen = True
        return "OK", [(b"metadata", item), b")"]


def test_source_returns_only_uids_after_cursor_and_never_marks_seen() -> None:
    client = FakeImapClient(messages={7: RAW_A, 8: RAW_B, 9: RAW_OTHER})
    source = ImapSource(
        client,
        allowed_senders={"noreply@kwork.ru"},
        subject_patterns=("Новый проект",),
    )

    items = source.fetch_after(7)

    assert [item.uid for item in items] == [8]
    assert items[0].message_id == "<b@test>"
    assert items[0].raw == RAW_B
    assert client.seen is False
    assert all(call[0] not in {"STORE", "EXPUNGE", "DELETE"} for call in client.calls)


def test_source_checks_headers_before_fetching_any_matching_body() -> None:
    client = FakeImapClient(messages={7: RAW_A, 8: RAW_B, 9: RAW_OTHER})
    source = ImapSource(
        client,
        allowed_senders={"noreply@kwork.ru"},
        subject_patterns=("Новый проект",),
    )

    source.fetch_after(6)

    fetches = [call for call in client.calls if call[0] == "FETCH"]
    assert [call[2] for call in fetches] == [
        "(RFC822.HEADER)",
        "(BODY.PEEK[])",
        "(RFC822.HEADER)",
        "(BODY.PEEK[])",
        "(RFC822.HEADER)",
    ]
    assert [call[1] for call in fetches] == ["7", "7", "8", "8", "9"]
    assert client.seen is False


def test_source_decodes_subject_and_normalizes_from_address() -> None:
    raw = (
        b"From: Kwork <NOREPLY@KWORK.RU>\r\n"
        b"Subject: =?utf-8?b?0J3QvtCy0YvQuSDQv9GA0L7QtdC60YI=?=\r\n"
        b"Message-ID: <encoded@test>\r\n\r\nbody"
    )
    client = FakeImapClient(messages={4: raw})
    client.uid = _single_message_uid(client, raw)  # type: ignore[method-assign]
    source = ImapSource(
        client,
        allowed_senders={"noreply@kwork.ru"},
        subject_patterns=("Новый проект",),
    )

    items = source.fetch_after(3)

    assert [item.uid for item in items] == [4]
    assert items[0].from_address == "noreply@kwork.ru"
    assert items[0].subject == "Новый проект"


def test_from_settings_authenticates_with_safe_tls_and_readonly_mailbox() -> None:
    client = FakeImapClient(messages={})
    captured: dict[str, object] = {}

    def factory(host: str, *, ssl_context: ssl.SSLContext):
        captured["host"] = host
        captured["ssl_context"] = ssl_context
        return client

    settings = Settings(
        imap=ImapSettings(host="imap.example.test", mailbox="INBOX"),
        filters=FilterSettings(
            senders=("noreply@kwork.ru",),
            subject_patterns=("Новый проект",),
            keywords=("python",),
        ),
    )
    secrets = SecretSettings(
        imap_username="monitor@example.test",
        imap_password="test-only",
        telegram_bot_token="token",
        telegram_chat_id="123",
        codeassist_base_url="http://127.0.0.1:8080/v1",
    )

    source = ImapSource.from_settings(settings, secrets, client_factory=factory)

    assert source.client is client
    assert captured["host"] == "imap.example.test"
    context = captured["ssl_context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert client.login_calls == [("monitor@example.test", "test-only")]
    assert client.select_calls == [("INBOX", True)]


@pytest.mark.parametrize("status", ("NO", "BAD"))
def test_source_raises_controlled_error_for_non_ok_search(status: str) -> None:
    client = FakeImapClient(messages={}, search_status=status)
    source = ImapSource(
        client,
        allowed_senders={"noreply@kwork.ru"},
        subject_patterns=("Новый проект",),
    )

    with pytest.raises(ImapSourceError, match="UID SEARCH failed"):
        source.fetch_after(0)


@pytest.mark.parametrize("status", ("NO", "BAD"))
def test_source_raises_controlled_error_for_non_ok_fetch(status: str) -> None:
    client = FakeImapClient(messages={7: RAW_A}, fetch_status=status)
    source = ImapSource(
        client,
        allowed_senders={"noreply@kwork.ru"},
        subject_patterns=("Новый проект",),
    )

    with pytest.raises(ImapSourceError, match="UID FETCH headers failed"):
        source.fetch_after(6)


def _single_message_uid(client: FakeImapClient, raw: bytes):
    def uid(command: str, *arguments: str):
        client.calls.append((command, *(str(argument) for argument in arguments)))
        if command == "SEARCH":
            return "OK", [b"4"]
        item = raw if arguments[1] == "(BODY.PEEK[])" else raw.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"
        return "OK", [(b"metadata", item), b")"]

    return uid
