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

# DeepSeek context: 128K total, small safety margin (tiktoken точный)
MAX_CONTEXT_TOKENS = 128_000
PROMPT_SAFETY_MARGIN = 1024
TOOL_RESULT_MAX_TOKENS = 2000


def _groq_describe(base64_data: str, media_type: str) -> str | None:
    """Describe image via Groq vision API."""
    if not GROQ_KEY:
        return None
    data = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe this image concisely in 1-2 sentences. "
             "Focus on visible text, UI elements, layout, and notable content. "
             "Ignore watermarks, logos, and UI chrome."},
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


def _count_tokens(text: str) -> int:
    """Token count via tiktoken cl100k_base (shared by Claude & DeepSeek BPE)."""
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    return len(_TOKENIZER.encode(text, disallowed_special=()))


def _truncate_messages(messages: list, max_tok: int) -> list:
    """Two-phase truncation: drop tool-only messages first, then oldest (safety)."""
    costs = [_msg_tokens(m) for m in messages]
    if sum(costs) <= max_tok:
        return messages
    sys_end = next((i for i, m in enumerate(messages) if m.get("role") != "system"), 0)
    kept = list(messages[:sys_end])
    kept_cost = sum(costs[:sys_end])
    # Phase 1: drop tool-only messages (preserve user text & assistant reasoning)
    for i, m in enumerate(messages[sys_end:], start=sys_end):
        c = costs[i]
        if _is_tool_only(m) and kept_cost + c > max_tok:
            continue  # skip this tool-only message
        kept.append(m)
        kept_cost += c
    # Phase 2: if still over budget, fall back to oldest-first (keep newest)
    if kept_cost > max_tok:
        kept = list(messages[:sys_end])
        kept_cost = sum(costs[:sys_end])
        for i in range(len(messages) - 1, sys_end - 1, -1):
            c = costs[i]
            if kept_cost + c <= max_tok or len(kept) == sys_end:
                kept.append(messages[i])
                kept_cost += c
    dropped = len(messages) - len(kept)
    if dropped:
        kept.insert(0, {"role": "system", "content": f"[{dropped} messages truncated to fit 128K context] — "})
    return kept


def _msg_tokens(m: dict) -> int:
    """Token count for a message including format overhead (~5 tok/msg)."""
    c = m.get("content", "")
    if isinstance(c, list):
        total = 0
        for b in c:
            total += _count_tokens(b.get("text", "") or b.get("name", "") or "")
            if b.get("type") == "tool_use":
                total += _count_tokens(json.dumps(b.get("input", {})))
            if b.get("type") == "tool_result":
                tc = b.get("content", "")
                if isinstance(tc, list):
                    for tb in tc:
                        total += _count_tokens(tb.get("text", "") or "")
                else:
                    total += _count_tokens(str(tc))
        return total + 5
    return _count_tokens(str(c)) + 5


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
    """Recursively replace image blocks with text descriptions (в т.ч. внутри tool_result)."""
    fixed = []
    for block in blocks:
        t = block.get("type")
        if t == "image":
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


def _normalize_text(text: str) -> str:
    """Compress 3+ newlines → 2, strip trailing spaces per line, strip edges."""
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(l.rstrip() for l in text.split('\n'))).strip()


def _is_tool_only(msg: dict) -> bool:
    """True if message is exclusively tool_result/tool_use blocks."""
    c = msg.get("content", "")
    return isinstance(c, list) and all(b.get("type") in ("tool_result", "tool_use") for b in c)


def _truncate_tool_results(messages: list) -> None:
    """Truncate tool_result content to TOOL_RESULT_MAX_TOKENS (mutates in-place)."""
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
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
                    encoded = _TOKENIZER.encode(tc, disallowed_special=())
                    block["content"] = (_TOKENIZER.decode(encoded[:TOOL_RESULT_MAX_TOKENS])
                                        + "\n[...truncated to 2000 tokens]")
            elif isinstance(tc, list):
                for tb in tc:
                    if tb.get("type") == "text":
                        text = tb.get("text", "")
                        tok = _count_tokens(text)
                        if tok > TOOL_RESULT_MAX_TOKENS:
                            encoded = _TOKENIZER.encode(text, disallowed_special=())
                            tb["text"] = (_TOKENIZER.decode(encoded[:TOOL_RESULT_MAX_TOKENS])
                                          + "\n[...truncated to 2000 tokens]")


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


def fix_request(body: dict) -> dict:
    """Normalize whitespace, fix images, strip thinking, smart-truncate context."""
    for msg in body.get("messages", []):
        c = msg.get("content")
        if isinstance(c, str):
            msg["content"] = _normalize_text(c)
            if not msg["content"]:
                msg["content"] = [{"type": "text", "text": "[Empty message]"}]
        elif isinstance(c, list):
            # Normalize text blocks first (reduces token count)
            for b in c:
                if b.get("type") == "text":
                    b["text"] = _normalize_text(b.get("text", ""))
            msg["content"] = _strip_image_blocks(c)
            if not msg["content"]:
                msg["content"] = [{"type": "text", "text": "[Empty message]"}]

    # DeepSeek doesn't support extended thinking — strip entirely
    # DeepSeek doesn't support extended thinking — strip entirely
    body.pop("thinking", None)

    # Strip cache_control blocks — DeepSeek has no prompt caching
    if "messages" in body:
        _strip_cache_control(body["messages"])
        _truncate_tool_results(body["messages"])
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


class ProxyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")

    def do_PATCH(self):
        self._proxy("PATCH")

    def _proxy(self, method):
        qs = ("?" + self.path.split("?", 1)[1]) if "?" in self.path else ""
        target = DEEPSEEK_ANTHROPIC_URL + qs
        clen = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(clen) if method in ("POST", "PATCH") and clen else None

        if body_bytes:
            try:
                req = json.loads(body_bytes)
                body_bytes = json.dumps(fix_request(req)).encode()
            except json.JSONDecodeError:
                pass

        hdrs = {
            "x-api-key": API_KEY or self.headers.get("x-api-key", ""),
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
                for chunk in iter(lambda: resp.read(4096), b""):
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
                    if "content" in js and isinstance(js["content"], list):
                        js["content"] = [b for b in js["content"] if b.get("type") != "thinking"]
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
    server = HTTPServer(("", PORT), ProxyHandler)
    print(f"DeepSeek proxy :{PORT} → {DEEPSEEK_ANTHROPIC_URL}")
    print(f"  Features: {', '.join(features)}")
    print(f"  Context: ~{(MAX_CONTEXT_TOKENS - PROMPT_SAFETY_MARGIN - 8192) // 1000}K prompt budget (128K total - {PROMPT_SAFETY_MARGIN}b safety)")
    print(f"  Set: ANTHROPIC_BASE_URL=http://localhost:{PORT}")
    server.serve_forever()
