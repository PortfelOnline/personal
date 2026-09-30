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


def parse_project_emails(raw: bytes, uid: int) -> tuple[ProjectEmail, ...]:
    """Convert one notification or digest into bounded per-project values."""
    message = BytesParser(policy=policy.default).parsebytes(raw)
    message_id = _decode_header(message.get("Message-ID"))
    subject = _decode_header(message.get("Subject"))
    chunks = _project_chunks(message)

    if not message_id or not subject or not chunks:
        raise EmailParseError(
            message_id, "missing Message-ID, subject, or project URL"
        )

    return tuple(
        ProjectEmail(
            message_id=message_id,
            uid=uid,
            subject=subject,
            project_url=project_url,
            budget=extract_budget(chunk),
            description=truncate(chunk, 6_000),
        )
        for project_url, chunk in chunks
    )


def parse_project_email(raw: bytes, uid: int) -> ProjectEmail:
    """Return the first project for backwards-compatible single-mail consumers."""
    return parse_project_emails(raw, uid)[0]


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

    plain_text = "\n".join(plain_parts).strip()
    if plain_text:
        return plain_text
    return " ".join(html_parts).strip()


def extract_kwork_project_url(text: str) -> str | None:
    """Return the first HTTPS URL whose hostname is exactly kwork.ru."""
    return next(iter(_project_url_matches(text)), None)


def extract_budget(text: str) -> str | None:
    """Return the original budget text, preserving its displayed whitespace."""
    match = _BUDGET_PATTERN.search(text)
    return match.group("budget").strip() if match else None


def truncate(text: str, maximum_length: int) -> str:
    """Keep untrusted email text within the downstream prompt budget."""
    return text[:maximum_length]


def _project_chunks(message: EmailMessage) -> list[tuple[str, str]]:
    """Select the mail representation that contains the most project rows."""
    candidates: list[tuple[int, list[tuple[str, str]]]] = []
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        if part.get_content_type() == "text/plain":
            text = _part_text(part)
            candidates.append(
                (0, _chunks_from_text(text, links_first=_plain_links_first(text)))
            )
        elif part.get_content_type() == "text/html":
            candidates.append(
                (1, _chunks_from_text(_html_to_text(_part_text(part)), links_first=True))
            )

    if not candidates:
        return []
    _, chunks = max(candidates, key=lambda candidate: (len(candidate[1]), candidate[0]))
    return chunks


def _plain_links_first(text: str) -> bool:
    """Infer whether plain-text rows put their project link before their data."""
    matches = list(_project_url_matches(text, with_spans=True))
    if len(matches) < 2:
        return False

    before_budgets = 0
    after_budgets = 0
    previous_end = 0
    for index, (_, start, end) in enumerate(matches):
        next_start = matches[index + 1][1] if index + 1 < len(matches) else len(text)
        before_budgets += int(extract_budget(text[previous_end:start]) is not None)
        after_budgets += int(extract_budget(text[end:next_start]) is not None)
        previous_end = end
    return after_budgets > before_budgets


def _chunks_from_text(text: str, *, links_first: bool) -> list[tuple[str, str]]:
    """Split a rendered mail body into local text around each project link."""
    matches = list(_project_url_matches(text, with_spans=True))
    chunks: list[tuple[str, str]] = []
    previous_end = 0
    for index, (project_url, start, end) in enumerate(matches):
        next_start = matches[index + 1][1] if index + 1 < len(matches) else len(text)
        if len(matches) == 1:
            chunk = text
        elif links_first:
            chunk = text[0:next_start] if index == 0 else text[start:next_start]
        else:
            chunk = text[previous_end:end]
        chunks.append((project_url, chunk.strip()))
        previous_end = end
    return chunks


def _project_url_matches(
    text: str, *, with_spans: bool = False
) -> list[str] | list[tuple[str, int, int]]:
    """Find unique official Kwork project links, preserving their body positions."""
    results: list[str] | list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for candidate in _URL_PATTERN.finditer(text):
        url = candidate.group().rstrip(_TRAILING_URL_PUNCTUATION)
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname != "kwork.ru"
            or not _is_project_link_path(parsed.path)
            or url in seen
        ):
            continue
        seen.add(url)
        end = candidate.start() + len(url)
        if with_spans:
            results.append((url, candidate.start(), end))
        else:
            results.append(url)
    return results


def _is_project_link_path(path: str) -> bool:
    """Accept official direct project URLs and per-row digest offer URLs."""
    return path.startswith("/projects/") or path == "/new_offer"


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
    try:
        content = part.get_content()
    except (LookupError, UnicodeError):
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        return payload.decode("utf-8", errors="replace")
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
