#!/usr/bin/env python3
"""Claude Code → DeepSeek Anthropic API proxy.

Fixes:
1. Image blocks → Groq vision (llama-4-scout) description, OCR fallback, or placeholder
2. Strips thinking block entirely (DeepSeek doesn't support extended thinking)
3. Truncates oldest messages to fit DeepSeek's 128K context window

Usage:
  python3 ds-proxy.py [--port 8099] [--api-key KEY]

Env:
  DEEPSEEK_API_KEY   — required, DeepSeek API key
  GROQ_API_KEY       — optional, enables vision (llama-4-scout)
  OCR               — set to "1" to enable tesseract fallback for images

Then:
  export ANTHROPIC_BASE_URL=http://localhost:8099
  # run Claude Code
"""
import json, os, sys, subprocess, tempfile, base64, re, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import tiktoken

DEEPSEEK_ANTHROPIC_URL = "https://api.deepseek.com/anthropic/v1/messages"
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8099
API_KEY = os.environ.get("DEEPSEEK_API_KEY") or next(
    (sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--api-key"), None
)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-4-scout-17b-16e-instruct"
USE_OCR = os.environ.get("OCR") == "1"
CLAUDE_KEY = os.environ.get("CLAUDE_API_KEY")
ANTHROPIC_DIRECT_URL = "https://api.anthropic.com/v1/messages"

# Max parallel tool_use blocks — DeepSeek часто выдаёт >10, API падает с 400
MAX_PARALLEL_TOOLS = 3

# DeepSeek context: 128K total, small safety margin (tiktoken точный)
MAX_CONTEXT_TOKENS = 128_000
PROMPT_SAFETY_MARGIN = 1024
TOOL_RESULT_MAX_TOKENS = 6000  # higher limit, truncation is adaptive (only when over budget)

# ── Auto model selection (flash vs pro) ──
_MODEL_SIMPLE = frozenset({
    "translate", "summarize", "format", "spell", "grammar",
    "convert", "short", "hello", "hi", "test", "echo", "ping",
    "capitalize", "lowercase", "uppercase", "trim", "strip",
    "plural", "singular", "synonym", "antonym",
})
_MODEL_COMPLEX = frozenset({
    "code", "implement", "debug", "refactor", "analyze", "architect",
    "design", "review", "optimize", "algorithm", "architecture",
    "complex", "async", "concurrency", "parallel", "distributed",
    "database", "query", "migration", "schema", "api", "endpoint",
    "authentication", "authorization", "encrypt", "decrypt",
    "performance", "benchmark", "profiling",
})


def _should_use_flash(body: dict) -> bool:
    """Определить: flash (дёшево) или pro (полно).

    Смотрит ТОЛЬКО сообщения user, не system (там tool descriptions,
    которые одинаковые всегда и не влияют на сложность запроса).

    1. Последнее user сообщение < 200 tok → flash
    2. Простые маркеры (translate, format, ping) → flash
    3. Сложные маркеры (code, debug, review) → pro
    4. Все сообщения > 3000 tok суммарно → pro (много контекста)
    """
    messages = body.get("messages", [])

    # Только user-сообщения для оценки длины
    user_texts = []
    for m in messages:
        if m.get("role") == "user":
            user_texts.append(_normalize_to_text(m.get("content", "")))
    user_text = " ".join(p for p in user_texts if p)
    user_tok = _count_tokens(user_text) if user_text else 0

    # Если вообще нет user сообщений — flash (здоровый default)
    if user_tok == 0:
        return True

    # Последнее user сообщение — самый точный индикатор сложности задачи
    last_user = _normalize_to_text(user_texts[-1]) if user_texts else ""
    last_tok = _count_tokens(last_user) if last_user else 0

    # Очень короткий запрос → flash
    if last_tok < 100:
        return True

    # Очень много контекста (все user сообщения) → pro
    if user_tok > 3000:
        return False

    # Keyword-анализ по последнему сообщению (там суть запроса)
    lower = last_user.lower()
    for m in _MODEL_COMPLEX:
        if re.search(rf"\b{re.escape(m)}\b", lower):
            return False
    for m in _MODEL_SIMPLE:
        if re.search(rf"\b{re.escape(m)}\b", lower):
            return True

    # Default: короткие (<200) → flash, иначе pro
    return last_tok < 200


# ── JSONL Usage Logger ──
_DEFAULT_LOG_PATH = os.path.expanduser("~/.local/var/deepseek-usage.jsonl")


def _log_jsonl(model: str, prompt_tokens: int, completion_tokens: int, system_len: int = 0):
    """Append one usage record to JSONL (единый с deepseek_api.py)."""
    import time as _time
    entry = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "system_prompt_len": system_len,
        "tags": ["proxy"],
    }
    try:
        parent = os.path.dirname(_DEFAULT_LOG_PATH)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(_DEFAULT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _groq_describe(base64_data: str, media_type: str) -> str | None:
    """Describe image via Groq vision API."""
    if not GROQ_KEY:
        return None
    data = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe concisely in 10-15 words"},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_data}"}},
        ]}],
        "max_tokens": 256,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
    )
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return resp["choices"][0]["message"]["content"]
    except Exception:
        return None


def _ocr_describe(base64_data: str) -> str | None:
    """OCR image via tesseract."""
    if not USE_OCR:
        return None
    try:
        raw = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(raw)
            tmp = f.name
        text = subprocess.run(
            ["tesseract", tmp, "stdout", "-l", "rus+eng"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        os.unlink(tmp)
        return f"[Screenshot text: {text[:500]}]" if text else None
    except Exception:
        return None


_TOKENIZER = None


def _normalize_to_text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        parts = []
        for item in x:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "content" in item:
                    parts.append(_normalize_to_text(item.get("content")))
        return "\n".join(p for p in parts if p)
    if isinstance(x, dict):
        if x.get("type") == "text":
            return x.get("text", "")
        return str(x)
    if x is None:
        return ""
    return str(x)


def _count_tokens(text) -> int:
    """Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE)."""
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    text = _normalize_to_text(text)
    if len(text) > 200_000:
        text = text[:100_000] + "\n...[truncated]...\n" + text[-50_000:]
    return len(_TOKENIZER.encode(text, disallowed_special=()))


def _truncate_messages(messages: list, max_tok: int) -> list:
    """Role-weighted truncation: compress content first, then drop tool-only, then newest-first."""
    costs = [_msg_tokens(m) for m in messages]
    if sum(costs) <= max_tok:
        return messages

    # Phase 0: compress tool_result content inline before dropping anything
    total = sum(costs)
    if total > max_tok * 1.1:
        for msg in messages:
            c = msg.get("content")
            if not isinstance(c, list):
                if isinstance(c, str) and msg.get("role") in ("user", "assistant"):
                    compressed = _compress_content(c)
                    if len(compressed) < len(c):
                        msg["content"] = compressed
                continue
            for block in c:
                if block.get("type") != "tool_result":
                    continue
                tc = block.get("content")
                if isinstance(tc, list):
                    for tb in tc:
                        if tb.get("type") == "text":
                            compressed = _compress_content(tb.get("text", ""))
                            tb["text"] = compressed
                elif isinstance(tc, str):
                    block["content"] = _compress_content(tc)
        costs = [_msg_tokens(m) for m in messages]
        if sum(costs) <= max_tok:
            return messages

    # Protect system prompts + first user message
    sys_end = next((i for i, m in enumerate(messages) if m.get("role") != "system"), 0)
    min_keep = max(sys_end, min(2, len(messages)))
    kept = list(messages[:min_keep])
    kept_cost = sum(costs[:min_keep])

    # Phase 1: keep messages by role priority (user > assistant > tool)
    remaining = list(enumerate(messages[min_keep:], start=min_keep))
    role_order = {"user": 0, "assistant": 1, "tool": 2}
    remaining.sort(key=lambda x: (role_order.get(x[1].get("role"), 3), x[0]))

    for i, m in remaining:
        c = costs[i]
        if kept_cost + c <= max_tok:
            kept.append(m)
            kept_cost += c
        elif m.get("role") == "user":
            # User messages get priority — drop tool-only first if we can
            tool_cut = [k for k in kept[min_keep:] if k.get("role") in ("tool",) or _is_tool_only(k)]
            for tc in tool_cut:
                idx = kept.index(tc)
                kept.pop(idx)
                kept_cost -= costs[messages.index(tc)]
                if kept_cost + c <= max_tok:
                    break
            if kept_cost + c <= max_tok:
                kept.append(m)
                kept_cost += c

    # Phase 2: if still over budget, keep newest with user+assistant pairs preferred
    if kept_cost > max_tok:
        kept = list(messages[:min_keep])
        kept_cost = sum(costs[:min_keep])
        for i in range(len(messages) - 1, min_keep - 1, -1):
            m = messages[i]
            c = costs[i]
            if kept_cost + c <= max_tok:
                kept.append(m)
                kept_cost += c
            elif m.get("role") == "user":
                # Try harder to fit user messages — bump oldest tool-only
                tool_idx = next((j for j in range(min_keep, len(kept))
                                if kept[j].get("role") in ("tool",) or _is_tool_only(kept[j])), None)
                if tool_idx is not None:
                    tool_cost = costs[messages.index(kept[tool_idx])]
                    kept.pop(tool_idx)
                    kept_cost -= tool_cost
                    if kept_cost + c <= max_tok:
                        kept.append(m)
                        kept_cost += c

    dropped = len(messages) - len(kept)
    if dropped:
        kept.insert(0, {"role": "system", "content": f"[{dropped} truncated] — "})
    return kept


def _msg_tokens(msg: dict) -> int:
    content = msg.get("content", "")
    content = _normalize_to_text(content)
    return _count_tokens(content)


def _describe_image(base64_data: str, media_type: str) -> str:
    """Try Groq vision → OCR → fallback placeholder."""
    desc = _groq_describe(base64_data, media_type)
    if desc:
        return f"[Screenshot: {desc}]"
    text = _ocr_describe(base64_data)
    if text:
        return text
    return "[Image]"


def _strip_image_blocks(blocks: list) -> list:
    """Recursively replace image/document blocks with text (в т.ч. внутри tool_result)."""
    fixed = []
    for block in blocks:
        t = block.get("type")
        if t in ("image", "document"):
            src = block.get("source", {})
            desc = _describe_image(src.get("data", ""), src.get("media_type", "image/png"))
            fixed.append({"type": "text", "text": desc})
        elif t == "tool_result":
            tc = block.get("content")
            if isinstance(tc, list):
                block = dict(block)
                block["content"] = _strip_image_blocks(tc)
            fixed.append(block)
        else:
            fixed.append(block)
    return fixed


def _normalize_text(text) -> str:
    """Strip trailing spaces per line + edges. Zero-risk — no content modification beyond whitespace."""
    text = _normalize_to_text(text)
    return '\n'.join(l.rstrip() for l in text.split('\n')).strip()


_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

# Patterns for content-type compression
_STACK_TRACE_RE = re.compile(r'^\s*(?:File\s+".*?"|Traceback|  File |  .*Error|at\s+|Caused by|→\s*)')
_LONG_LINE_THRESHOLD = 500  # chars — likely pretty-printed data


def _compress_content(text) -> str:
    """Content-type aware compression. Handles: file listings, stack traces, long JSON, repetitive logs."""
    text = _normalize_to_text(text)
    text = _ANSI_RE.sub('', text).strip()
    if not text:
        return text

    lines = text.split('\n')
    n = len(lines)

    # File listing or log with many repetitive lines → keep head+tail
    if n > 40:
        stack_lines = sum(1 for l in lines if _STACK_TRACE_RE.match(l))
        json_lines = sum(1 for l in lines[:5] if l.strip().startswith(('{', '[')))
        long_lines = sum(1 for l in lines if len(l) > _LONG_LINE_THRESHOLD / 2)

        # Stack trace → keep first 8 + last 4
        if stack_lines > 5:
            keep = lines[:8] + ['[...stack trace compressed...]'] + lines[-4:]
            return '\n'.join(keep)

        # Long JSON pretty-print → try compact
        if json_lines > 3 or long_lines > 10:
            joined = '\n'.join(lines)
            compacted = _compact_json_text(joined)
            if compacted != joined:
                return compacted

        # Generic many-line output → keep first 20 + last 10
        keep = lines[:20] + [f'\n[...{n - 30} lines compressed...]\n'] + lines[-10:]
        return '\n'.join(keep)

    # Short enough — just strip ANSI + normalize
    return text


# Backward compat alias
_compress_progress = _compress_content


def _is_tool_only(msg: dict) -> bool:
    """True if message is exclusively tool_result/tool_use blocks."""
    c = msg.get("content", "")
    return isinstance(c, list) and all(b.get("type") in ("tool_result", "tool_use") for b in c)


def _truncate_tool_results(messages: list, total_budget: int) -> None:
    """Adaptive truncation: only when total budget exceeded, never below TOOL_RESULT_MAX_TOKENS."""
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    actual = sum(_msg_tokens(m) for m in messages)
    if actual <= total_budget:
        return  # no truncation needed — zero risk
    for msg in messages:
        c = msg.get("content")
        if not isinstance(c, list):
            continue
        for block in c:
            if block.get("type") != "tool_result":
                continue
            tc = block.get("content", "")
            if isinstance(tc, str):
                tok = _count_tokens(tc)
                if tok > TOOL_RESULT_MAX_TOKENS:
                    encoded = _TOKENIZER.encode(_normalize_to_text(tc), disallowed_special=())
                    block["content"] = (_TOKENIZER.decode(encoded[:TOOL_RESULT_MAX_TOKENS])
                                        + f"\n[...truncated to {TOOL_RESULT_MAX_TOKENS} tokens]")
            elif isinstance(tc, list):
                for tb in tc:
                    if tb.get("type") == "text":
                        text = tb.get("text", "")
                        tok = _count_tokens(text)
                        if tok > TOOL_RESULT_MAX_TOKENS:
                            encoded = _TOKENIZER.encode(text, disallowed_special=())
                            tb["text"] = (_TOKENIZER.decode(encoded[:TOOL_RESULT_MAX_TOKENS])
                                          + f"\n[...truncated to {TOOL_RESULT_MAX_TOKENS} tokens]")


def _strip_empty_blocks(blocks: list) -> list:
    """Remove empty tool_result and text blocks. Zero risk — empty blocks carry no information."""
    cleaned = []
    for block in blocks:
        t = block.get("type")
        if t == "tool_result":
            tc = block.get("content", "")
            # Empty string or empty array → skip
            if isinstance(tc, str) and not tc.strip():
                continue
            if isinstance(tc, list):
                # Filter empty sub-blocks
                filled = [b for b in tc if b.get("type") == "text" and b.get("text", "").strip()]
                if not filled:
                    continue  # tool_result with no useful content
                block = dict(block)
                block["content"] = filled
            cleaned.append(block)
        elif t == "text":
            text = block.get("text", "")
            if text.strip():
                cleaned.append(block)
            # else drop empty text block
        else:
            cleaned.append(block)
    return cleaned


def _merge_text_blocks(blocks: list) -> list:
    """Merge adjacent text blocks into one. Zero risk — preserves all content."""
    merged = []
    buf = []
    for block in blocks:
        if block.get("type") == "text":
            buf.append(block.get("text", ""))
        else:
            if buf:
                merged.append({"type": "text", "text": "".join(buf)})
                buf = []
            merged.append(block)
    if buf:
        merged.append({"type": "text", "text": "".join(buf)})
    return merged


def _tool_result_text(block: dict) -> str:
    """Extract text from a tool_result block for comparison."""
    tc = block.get("content", "")
    return _normalize_to_text(tc)


DEDUP_MIN_LEN = 100  # only dedup if text is long enough — avoids coincedental short matches


def _dedup_consecutive_results(blocks: list) -> list:
    """Drop consecutive tool_result blocks with identical text. Zero-risk: identical copies carry no new info."""
    deduped = []
    prev_text = None
    for block in blocks:
        if block.get("type") == "tool_result":
            text = _tool_result_text(block)
            if text and len(text) > DEDUP_MIN_LEN and text == prev_text:
                continue  # skip identical consecutive result
            prev_text = text
        else:
            prev_text = None
        deduped.append(block)
    return deduped


def _limit_tool_use_blocks(blocks: list) -> list:
    """Limit parallel tool_use blocks to MAX_PARALLEL_TOOLS.
    DeepSeek часто выдаёт 10+ tool_use за раз → API Error 400.
    Zero-risk: избыточные tool_use блоки не будут выполнены корректно в любом случае.
    """
    tool_count = 0
    limited = []
    for block in blocks:
        if block.get("type") == "tool_use":
            tool_count += 1
            if tool_count > MAX_PARALLEL_TOOLS:
                continue  # drop excessive tool_use blocks
        limited.append(block)
    return limited


_DESC_BOILERPLATE_RE = re.compile(
    r'(?i)\b(?:please\s+|note\s+that\s+|'
    r'this\s+(?:tool|function)\s+(?:is\s+)?(?:used\s+)?(?:for|to|can\s+be\s+used\s+to)\s+|'
    r'use\s+this\s+(?:tool|function)\s+(?:in\s+order\s+)?to\s+|'
    r'this\s+(?:is\s+)?a\s+(?:tool|function)\s+(?:that\s+)?|'
    r'call\s+(?:this\s+)?(?:tool|function)\s+(?:in\s+order\s+)?to\s+|'
    r'you\s+(?:can|may|should|will\s+need\s+to)\s+|'
    r'(?:generally|typically|usually|basically|essentially)\s+|'
    r'in\s+order\s+to\s+|'
    r'(?:if\s+)?(?:needed|necessary|required|applicable)(?:,\s+)?|'
    r'as\s+needed|'
    r'for\s+example,?|'
    r'in\s+other\s+words,?|'
    r'i\.?\s*e\.?\s*|'
    r'e\.?\s*g\.?\s*)',
)

_DESC_PUNCT_RE = re.compile(r'\s{2,}')


_MINIFY_MIN_LEN = 40  # skip short descriptions — boilerplate regex would be meaningless on them


def _minify_description(desc: str) -> str:
    """Strip boilerplate/hedging from tool descriptions. Zero-risk: preserves all semantic content."""
    if not desc or len(desc) < _MINIFY_MIN_LEN:
        return desc
    desc = _DESC_BOILERPLATE_RE.sub('', desc)
    desc = _DESC_PUNCT_RE.sub(' ', desc)
    desc = desc.strip().strip('.,;: ')
    return desc


_FENCE_RE = re.compile(r'^```\w*$')  # ``` or ```json, ```python, etc.


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from tool results. Zero-risk: only strips standard fenced code blocks."""
    lines = text.split('\n')
    if lines and _FENCE_RE.match(lines[0].strip()):
        # Has opening fence — check for closing fence
        if lines[-1].strip() == '```':
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return '\n'.join(lines)
    return text


def _compact_json_text(text: str) -> str:
    """Compact pretty-printed JSON. Zero risk — identical data, fewer tokens."""
    stripped = text.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return text
    try:
        obj = json.loads(stripped)
        compact = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        return compact
    except (json.JSONDecodeError, TypeError, ValueError):
        return text


def _strip_cache_control(messages: list) -> None:
    """Remove cache_control from all blocks (DeepSeek doesn't support Anthropic caching)."""
    for msg in messages:
        c = msg.get("content")
        if isinstance(c, list):
            for b in c:
                b.pop("cache_control", None)
                if b.get("type") == "tool_result":
                    tc = b.get("content")
                    if isinstance(tc, list):
                        for tb in tc:
                            tb.pop("cache_control", None)


def _strip_metadata(messages: list) -> None:
    """Remove id/type from messages — DeepSeek ignores them (zero-risk)."""
    for msg in messages:
        msg.pop("id", None)
        msg.pop("type", None)


# ── Request processing cache (system prompt + tools don't change between calls) ──
import hashlib as _hashlib  # noqa: E402
_SYS_CACHE = {}   # hash → compressed_system_text
_TOOL_CACHE = {}  # hash → list of compressed tools


def _fix_request_cached(body: dict) -> dict:
    """Cache-aware wrapper: skip recomputation when system/tools unchanged."""
    # Cache system prompt normalization
    sys_prompt = body.get("system")
    if isinstance(sys_prompt, str):
        sys_hash = _hashlib.sha256(sys_prompt.encode()).hexdigest()[:16]
        if sys_hash in _SYS_CACHE:
            body["system"] = _SYS_CACHE[sys_hash]
        else:
            body["system"] = _compress_progress(_normalize_text(sys_prompt))
            if body["system"]:
                _SYS_CACHE[sys_hash] = body["system"]
    elif sys_prompt is not None:
        body["system"] = _compress_progress(_normalize_text(sys_prompt))

    # Cache tool description normalization
    tools = body.get("tools", [])
    if isinstance(tools, list) and tools:
        # Fast hash: just concatenate names+descs
        tool_key = _hashlib.sha256(
            ";".join(t.get("name","") + "|" + (t.get("description") or "") for t in tools).encode()
        ).hexdigest()[:16]
        if tool_key in _TOOL_CACHE:
            body["tools"] = _TOOL_CACHE[tool_key]
        else:
            for tool in tools:
                tool.pop("display_name", None)
                desc = tool.get("description")
                if isinstance(desc, str):
                    tool["description"] = _minify_description(_compress_progress(_normalize_text(desc)))
            _TOOL_CACHE[tool_key] = body["tools"]
    elif isinstance(tools, list):
        for tool in tools:
            tool.pop("display_name", None)

    # Keep cache bounded (max 64 entries each)
    while len(_SYS_CACHE) > 64:
        del _SYS_CACHE[next(iter(_SYS_CACHE))]
    while len(_TOOL_CACHE) > 64:
        del _TOOL_CACHE[next(iter(_TOOL_CACHE))]

    return body


def fix_request(body: dict) -> dict:
    """Normalize whitespace, fix images, strip thinking, smart-truncate context."""
    # System + tools normalization via cache
    body = _fix_request_cached(body)

    if "messages" in body:
        _strip_metadata(body["messages"])
    for msg in body.get("messages", []):
        c = msg.get("content")
        if isinstance(c, str):
            msg["content"] = _compress_progress(_normalize_text(c))
            if not msg["content"]:
                msg["content"] = [{"type": "text", "text": "[Empty message]"}]
        elif isinstance(c, dict):
            msg["content"] = [{"type": "text", "text": _compress_progress(_normalize_text(c)) or "[Empty message]"}]
        elif isinstance(c, list):
            # Normalize text blocks first (reduces token count)
            for b in c:
                if b.get("type") == "text":
                    b["text"] = _compress_progress(_normalize_text(b.get("text", "")))
                elif b.get("type") == "tool_result":
                    tc = b.get("content")
                    if isinstance(tc, list):
                        for tb in tc:
                            if tb.get("type") == "text":
                                tb["text"] = _compact_json_text(_strip_code_fences(_compress_progress(_normalize_text(tb.get("text", "")))))
            msg["content"] = _strip_image_blocks(c)
            msg["content"] = _strip_empty_blocks(msg["content"])
            msg["content"] = _merge_text_blocks(msg["content"])
            msg["content"] = _dedup_consecutive_results(msg["content"])
            if not msg["content"]:
                msg["content"] = [{"type": "text", "text": "[Empty message]"}]

    # Don't strip thinking — pass through to DeepSeek (ignored if unsupported)
    # DeepSeek ignores metadata field (user_id etc.) — zero-risk
    body.pop("metadata", None)
    # system prompt + tools already normalized by _fix_request_cached above
    # Strip cache_control blocks — DeepSeek has no prompt caching
    if "messages" in body:
        _strip_cache_control(body["messages"])
        prompt_budget_tmp = MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - body.get("max_tokens", 8192)
        _truncate_tool_results(body["messages"], prompt_budget_tmp)
        max_tok = body.get("max_tokens", 8192)
        prompt_budget = MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - max_tok
        body["messages"] = _truncate_messages(body["messages"], prompt_budget)
        # Conditional max_tokens cap — only when still over budget, never < 4096
        actual = sum(_msg_tokens(m) for m in body["messages"])
        if actual > prompt_budget and max_tok > 4096:
            max_tok = max(max_tok - 2048, 4096)
            body["max_tokens"] = max_tok
            body["messages"] = _truncate_messages(body["messages"],
                                                  MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - max_tok)

    return body


def _log_token_usage(body: dict, max_tok: int):
    """Log token consumption to stderr (observability, not optimisation)."""
    prompt_tok = sum(_msg_tokens(m) for m in body.get("messages", []))
    sys_tok = _count_tokens(_normalize_to_text(body.get("system", "")))
    total = prompt_tok + sys_tok
    budget = MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - max_tok
    pct = round(total / budget * 100, 1) if budget else 0
    print(f"  [tok] prompt={total} budget={budget} max_tok={max_tok} "
          f"usage={pct}% (sys={sys_tok} msgs={prompt_tok})", file=sys.stderr)


class ProxyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        if self.path.rstrip("/") == "/reload":
            self._do_reload()
            return
        self._proxy("POST")

    def _do_reload(self):
        """Graceful in-place restart: exec self with same args. No sessions dropped."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"reloading","pid":' + str(os.getpid()).encode() + b'}\n')
        self.wfile.flush()
        # Small delay to let response flush → then exec
        import threading, time
        def _restart():
            time.sleep(0.2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        threading.Thread(target=_restart, daemon=True).start()

    def do_PATCH(self):
        self._proxy("PATCH")

    def _proxy(self, method):
        qs = ("?" + self.path.split("?", 1)[1]) if "?" in self.path else ""
        clen = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(clen) if method in ("POST", "PATCH") and clen else None
        req_obj = json.loads(body_bytes) if body_bytes else {}

        # Route to native Claude if model name contains "claude" and API key is set
        use_native = bool(CLAUDE_KEY and "claude" in (req_obj.get("model", "") or "").lower())

        # Auto model selection (only for DeepSeek, not native Claude)
        selected_model = None
        if not use_native and body_bytes:
            selected_model = "deepseek-v4-flash" if _should_use_flash(req_obj) else "deepseek-v4-pro"
            req_obj["model"] = selected_model

        if use_native:
            target = ANTHROPIC_DIRECT_URL + qs
        else:
            target = DEEPSEEK_ANTHROPIC_URL + qs

        if body_bytes:
            try:
                if use_native:
                    body_bytes = json.dumps(req_obj, separators=(',', ':')).encode()
                else:
                    body_bytes = json.dumps(fix_request(req_obj), separators=(',', ':')).encode()
                    _log_token_usage(req_obj, req_obj.get("max_tokens", 8192))
            except json.JSONDecodeError:
                pass

        hdrs = {
            "x-api-key": CLAUDE_KEY if use_native else (API_KEY or self.headers.get("x-api-key", "")),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        fwd = urllib.request.Request(target, data=body_bytes, headers=hdrs, method=method)
        try:
            resp = urllib.request.urlopen(fwd, timeout=300)
        except urllib.error.HTTPError as e:
            resp = e

        status = resp.status if resp.status is not None else 502
        is_stream = body_bytes and json.loads(body_bytes).get("stream") if body_bytes else False

        if is_stream:
            self.send_response(status)
            for k, v in resp.headers.items():
                if k.lower() in ("transfer-encoding", "content-length", "connection"):
                    continue
                self.send_header(k, v)
            self.end_headers()
            if status < 400:
                # Track tool_use block indices to limit parallel tools in streaming SSE
                tool_use_indices = set()
                skip_indices = set()
                for chunk in iter(lambda: resp.read(4096), b""):
                    if b"data: " in chunk:
                        decoded = chunk.decode("utf-8", errors="replace")
                        lines = decoded.split("\n")
                        filtered = []
                        for line in lines:
                            if line.startswith("data: "):
                                payload = line[6:]
                                try:
                                    ev = json.loads(payload)
                                    ev_type = ev.get("type")
                                    ev_idx = ev.get("index")
                                    if ev_type == "content_block_start":
                                        cb = ev.get("content_block", {})
                                        if cb.get("type") == "tool_use":
                                            tool_use_indices.add(ev_idx)
                                            if len(tool_use_indices) > MAX_PARALLEL_TOOLS:
                                                skip_indices.add(ev_idx)
                                                continue
                                        # text blocks are always kept
                                    elif ev_type in ("content_block_delta", "content_block_stop"):
                                        if ev_idx in skip_indices:
                                            continue
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            filtered.append(line)
                        if filtered:
                            self.wfile.write("\n".join(filtered).encode("utf-8"))
                    else:
                        self.wfile.write(chunk)
                    self.wfile.flush()
            else:
                self.wfile.write(resp.read())
        else:
            # Non-streaming: read + filter body first → correct Content-Length
            body = resp.read()
            if status < 400:
                try:
                    js = json.loads(body)
                    # Limit parallel tool_use blocks — DeepSeek часто выдаёт > MAX_PARALLEL_TOOLS
                    content = js.get("content")
                    if isinstance(content, list):
                        js["content"] = _limit_tool_use_blocks(content)
                    usage = js.get("usage", {})
                    if usage:
                        inp = usage.get('input_tokens', 0)
                        out = usage.get('output_tokens', 0)
                        print(f"  [resp] input_tokens={inp} output_tokens={out}", file=sys.stderr)
                        if selected_model:
                            sys_len = _count_tokens(_normalize_to_text(req_obj.get("system", "")))
                            _log_jsonl(selected_model, inp, out, sys_len)
                    body = json.dumps(js).encode()
                except (json.JSONDecodeError, TypeError):
                    pass
            self.send_response(status)
            for k, v in resp.headers.items():
                if k.lower() in ("transfer-encoding", "content-length", "connection"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    if not API_KEY:
        print("No API key. Set DEEPSEEK_API_KEY env var or pass --api-key")
        sys.exit(1)
    features = []
    if GROQ_KEY:
        features.append(f"vision (Groq {GROQ_MODEL})")
    if USE_OCR:
        features.append("OCR fallback")
    if not features:
        features.append("image placeholder")
    native = "native Claude" if CLAUDE_KEY else "native Claude (set CLAUDE_API_KEY to enable)"
    server = HTTPServer(("", PORT), ProxyHandler)
    print(f"DeepSeek proxy :{PORT} → {DEEPSEEK_ANTHROPIC_URL}")
    print(f"  Features: {', '.join(features)}")
    print(f"  Fallback: {native} (model name containing 'claude')")
    print(f"  Context: ~{(MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - 8192) // 1000}K prompt budget (128K total - {PROMPT_SAFETY_MARGIN}b safety)")
    print(f"  Set: ANTHROPIC_BASE_URL=http://localhost:{PORT}")
    server.serve_forever()
