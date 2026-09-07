"""Parse official Kwork project notifications from RFC 822 message bytes."""

from __future__ import annotations

import re
from email import policy
from email.header import decode_header
from email.message import EmailMessage
from email.parser import BytesParser
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .models import ProjectEmail


_URL_PATTERN = re.compile(r"https://[^\s<>\"']+", re.IGNORECASE)
_BUDGET_PATTERN = re.compile(
    r"(?:бюджет|budget)\s*[:\-]?\s*"
    r"(?P<budget>\d[\d \u00a0]*(?:\s*(?:₽|руб(?:\.|лей|ля)?|RUB))?)",
    re.IGNORECASE,
)
_TRAILING_URL_PUNCTUATION = ".,;:!?)]}"


class EmailParseError(ValueError):
    """Raised when a notification cannot be safely identified as a project."""

    def __init__(self, message_id: str | None, reason: str) -> None:
        self.message_id = message_id
        self.reason = reason
        super().__init__(reason)


def parse_project_email(raw: bytes, uid: int) -> ProjectEmail:
    """Convert raw IMAP message bytes into a bounded project notification."""
    message = BytesParser(policy=policy.default).parsebytes(raw)
    message_id = _decode_header(message.get("Message-ID"))
    subject = _decode_header(message.get("Subject"))
    text = extract_body_text(message)
    project_url = extract_kwork_project_url(text)

    if not message_id or not subject or not project_url:
        raise EmailParseError(
            message_id, "missing Message-ID, subject, or project URL"
        )

    return ProjectEmail(
        message_id=message_id,
        uid=uid,
        subject=subject,
        project_url=project_url,
        budget=extract_budget(text),
        description=truncate(text, 6_000),
    )


def extract_body_text(message: EmailMessage) -> str:
    """Prefer readable plain text and fall back to normalized HTML text."""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        if part.get_content_type() == "text/plain":
            plain_parts.append(_part_text(part))
        elif part.get_content_type() == "text/html":
            html_parts.append(_html_to_text(_part_text(part)))

    if plain_parts:
        return "\n".join(plain_parts).strip()
    return " ".join(html_parts).strip()


def extract_kwork_project_url(text: str) -> str | None:
    """Return the first HTTPS URL whose hostname is exactly kwork.ru."""
    for candidate in _URL_PATTERN.findall(text):
        url = candidate.rstrip(_TRAILING_URL_PUNCTUATION)
        parsed = urlsplit(url)
        if parsed.scheme.lower() == "https" and parsed.hostname == "kwork.ru":
            return url
    return None


def extract_budget(text: str) -> str | None:
    """Return the original budget text, preserving its displayed whitespace."""
    match = _BUDGET_PATTERN.search(text)
    return match.group("budget").strip() if match else None


def truncate(text: str, maximum_length: int) -> str:
    """Keep untrusted email text within the downstream prompt budget."""
    return text[:maximum_length]


def _decode_header(value: object | None) -> str:
    """Decode RFC 2047 header fragments without leaking replacement failures."""
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


def _part_text(part: EmailMessage) -> str:
    """Decode one textual MIME part using the email package's declared charset."""
    content = part.get_content()
    return content if isinstance(content, str) else str(content)


class _HTMLTextExtractor(HTMLParser):
    """Collect visible HTML text and hyperlink targets as whitespace-separated text."""

    _BLOCK_TAGS = frozenset({"br", "div", "li", "p", "tr"})
    _IGNORED_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        if tag in self._BLOCK_TAGS:
            self._chunks.append(" ")
        if not self._ignored_depth:
            for name, value in attrs:
                if name.casefold() == "href" and value:
                    self._chunks.extend((" ", value, " "))

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in self._BLOCK_TAGS:
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join("".join(self._chunks).split())


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()
