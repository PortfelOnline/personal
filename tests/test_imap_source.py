from __future__ import annotations

from dataclasses import dataclass, field

from kwork_monitor.imap_source import ImapSource


RAW_A = "From: noreply@kwork.ru\r\nSubject: Новый проект: A\r\nMessage-ID: <a@test>\r\n\r\nA".encode()
RAW_B = "From: noreply@kwork.ru\r\nSubject: Новый проект: B\r\nMessage-ID: <b@test>\r\n\r\nB".encode()
RAW_OTHER = "From: other@example.test\r\nSubject: Новый проект: C\r\nMessage-ID: <c@test>\r\n\r\nC".encode()


@dataclass
class FakeImapClient:
    messages: dict[int, bytes]
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def uid(self, command: str, *arguments: str):
        self.calls.append((command, *(str(argument) for argument in arguments)))
        if command == "SEARCH":
            return "OK", [b"7 8 9"]
        uid = int(arguments[0])
        item = self.messages[uid]
        if arguments[1] == "(RFC822.HEADER)":
            item = item.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"
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
        "(RFC822)",
        "(RFC822.HEADER)",
        "(RFC822)",
        "(RFC822.HEADER)",
    ]
    assert [call[1] for call in fetches] == ["7", "7", "8", "8", "9"]


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


def _single_message_uid(client: FakeImapClient, raw: bytes):
    def uid(command: str, *arguments: str):
        client.calls.append((command, *(str(argument) for argument in arguments)))
        if command == "SEARCH":
            return "OK", [b"4"]
        item = raw if arguments[1] == "(RFC822)" else raw.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"
        return "OK", [(b"metadata", item), b")"]

    return uid
