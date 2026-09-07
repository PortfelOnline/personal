"""Read-only IMAP source that filters headers before downloading message bodies."""

from __future__ import annotations

import imaplib
import ssl
from dataclasses import dataclass
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import parseaddr
import re
from typing import Any, Callable

from .models import SecretSettings, Settings


@dataclass(frozen=True)
class MailItem:
    """A message selected by the configured sender and subject allowlists."""

    uid: int
    message_id: str | None
    raw: bytes
    from_address: str
    subject: str


class ImapSourceError(RuntimeError):
    """Raised when an IMAP command cannot safely provide source data."""


class ImapSource:
    """Fetch matching messages without changing mailbox flags or messages."""

    def __init__(
        self,
        client: Any,
        allowed_senders: set[str] | frozenset[str] | tuple[str, ...],
        subject_patterns: tuple[str, ...],
        *,
        mailbox: str | None = None,
    ) -> None:
        self.client = client
        self.allowed_senders = frozenset(
            _normalize_text(sender) for sender in allowed_senders
        )
        self.subject_patterns = tuple(
            _normalize_text(pattern) for pattern in subject_patterns
        )
        self.mailbox = mailbox

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        secrets: SecretSettings,
        *,
        client_factory: Callable[..., Any] | None = None,
    ) -> "ImapSource":
        """Authenticate and select the configured mailbox in read-only mode."""
        factory = client_factory or imaplib.IMAP4_SSL
        client = factory(
            settings.imap.host,
            ssl_context=ssl.create_default_context(),
        )
        _imap_ok(client.login(secrets.imap_username, secrets.imap_password), "login")
        _imap_ok(
            client.select(settings.imap.mailbox, readonly=True),
            "select mailbox",
        )
        return cls(
            client,
            settings.filters.senders,
            settings.filters.subject_patterns,
            mailbox=settings.imap.mailbox,
        )

    connect = from_settings

    def fetch_after(self, uid: int) -> list[MailItem]:
        """Search by UID, inspect headers, then download only allow-listed bodies."""
        if uid < 0:
            raise ValueError("UID must be non-negative")
        status, data = self.client.uid("SEARCH", None, "UID", f"{uid + 1}:*")
        _imap_ok((status, data), "UID SEARCH")
        candidates = [candidate for candidate in _search_uids(data) if candidate > uid]
        items: list[MailItem] = []
        for candidate_uid in candidates:
            status, data = self.client.uid(
                "FETCH", str(candidate_uid), "(RFC822.HEADER)"
            )
            _imap_ok((status, data), "UID FETCH headers")
            header_bytes = _response_bytes(data)
            message = BytesParser(policy=policy.default).parsebytes(header_bytes)
            from_address = _normalized_from(message.get("From"))
            subject = _decode_header(message.get("Subject"))
            normalized_subject = _normalize_text(subject)
            if from_address not in self.allowed_senders or not any(
                pattern in normalized_subject for pattern in self.subject_patterns
            ):
                continue

            status, data = self.client.uid(
                "FETCH", str(candidate_uid), "(BODY.PEEK[])")
            _imap_ok((status, data), "UID FETCH message")
            items.append(
                MailItem(
                    uid=candidate_uid,
                    message_id=_optional_header(message.get("Message-ID")),
                    raw=_response_bytes(data),
                    from_address=from_address,
                    subject=subject,
                )
            )
        return items


def _imap_ok(response: tuple[Any, Any], operation: str) -> None:
    status = response[0]
    if isinstance(status, bytes):
        status = status.decode("ascii", errors="replace")
    if str(status).upper() != "OK":
        raise ImapSourceError(f"IMAP {operation} failed")


def _search_uids(data: Any) -> list[int]:
    if not data:
        return []
    values: list[int] = []
    chunks = data if isinstance(data, (list, tuple)) else [data]
    for chunk in chunks:
        if isinstance(chunk, bytes):
            text = chunk.decode("ascii", errors="ignore")
        else:
            text = str(chunk)
        for value in text.split():
            if value.isdigit():
                values.append(int(value))
    return sorted(set(values))


def _response_bytes(data: Any) -> bytes:
    """Extract RFC822 bytes from common imaplib and deterministic fake responses."""
    if isinstance(data, bytes):
        return data
    if isinstance(data, (list, tuple)):
        for entry in data:
            if isinstance(entry, tuple):
                for candidate in entry[1:]:
                    if isinstance(candidate, bytes):
                        return candidate
            elif isinstance(entry, bytes) and b"(" not in entry:
                return entry
    raise ImapSourceError("IMAP FETCH returned no message bytes")


def _decode_header(value: object | None) -> str:
    if value is None:
        return ""
    fragments: list[str] = []
    for fragment, charset in decode_header(str(value)):
        if isinstance(fragment, bytes):
            try:
                fragments.append(fragment.decode(charset or "utf-8", errors="replace"))
            except LookupError:
                fragments.append(fragment.decode("utf-8", errors="replace"))
        else:
            fragments.append(fragment)
    return "".join(fragments).strip()


def _normalized_from(value: object | None) -> str:
    _, address = parseaddr(_decode_header(value))
    return _normalize_text(address)


def _optional_header(value: object | None) -> str | None:
    decoded = _decode_header(value)
    return decoded or None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
