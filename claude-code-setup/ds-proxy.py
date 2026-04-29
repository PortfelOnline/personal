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
import json, os, sys, subprocess, tempfile, base64, urllib.request, urllib.error
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

# DeepSeek context: 128K total, reserve 8K for response, use 80% of prompt budget
MAX_CONTEXT_TOKENS = 128_000
RESPONSE_MARGIN = 8_192
MAX_PROMPT_TOKENS = int((MAX_CONTEXT_TOKENS - RESPONSE_MARGIN) * 0.8)  # ~96K


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
    """Drop oldest non-system messages to fit DeepSeek's 128K window."""
    msg_cost = _msg_tokens
    total = sum(msg_cost(m) for m in messages)
    if total <= max_tok:
        return messages
    # preserve leading system messages
    sys_end = next((i for i, m in enumerate(messages) if m.get("role") != "system"), 0)
    kept = list(messages[:sys_end])
    rest = messages[sys_end:]
    for m in reversed(rest):
        candidate = kept + [m]
        if sum(msg_cost(x) for x in candidate) <= max_tok:
            kept.append(m)
        elif len(kept) == sys_end:
            kept.append(m)  # always keep at least one user message
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
                total += _count_tokens(b.get("content", "") if isinstance(b.get("content"), str) else json.dumps(b.get("content", "")))
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


def fix_request(body: dict) -> dict:
    """Fix images (vision/OCR), strip thinking, truncate context for DeepSeek."""
    for msg in body.get("messages", []):
        c = msg.get("content")
        if not isinstance(c, list):
            continue
        fixed = []
        for block in c:
            if block.get("type") == "image":
                src = block.get("source", {})
                b64 = src.get("data", "")
                mime = src.get("media_type", "image/png")
                desc = _describe_image(b64, mime)
                fixed.append({"type": "text", "text": desc})
            else:
                fixed.append(block)
        msg["content"] = fixed
        if not msg["content"]:
            msg["content"] = [{"type": "text", "text": "[Empty message]"}]

    # DeepSeek doesn't support extended thinking — strip entirely
    body.pop("thinking", None)

    # Truncate oldest messages if context overflows DeepSeek's 128K limit
    if "messages" in body:
        max_tok = body.get("max_tokens", 8192)
        prompt_budget = min(MAX_PROMPT_TOKENS, MAX_CONTEXT_TOKENS - RESPONSE_MARGIN - max_tok)
        body["messages"] = _truncate_messages(body["messages"], prompt_budget)

    return body


class ProxyHandler(BaseHTTPRequestHandler):
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
    print(f"  Context: ~96K prompt budget (128K total - 8K response)")
    print(f"  Set: ANTHROPIC_BASE_URL=http://localhost:{PORT}")
    server.serve_forever()
