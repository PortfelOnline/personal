#!/usr/bin/env python3
"""Claude Code → DeepSeek Anthropic API proxy.

Fixes:
1. Strips image blocks (DeepSeek has no vision)
2. Strips budget_tokens from thinking (DeepSeek ignores it but CC sends it)

Usage:
  python3 ds-proxy.py [--port 8099] [--api-key KEY]

Then set:
  export ANTHROPIC_BASE_URL=http://localhost:8099
  export ANTHROPIC_AUTH_TOKEN=<your-deepseek-key>
  # run Claude Code as usual
"""
import json, os, sys, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

DEEPSEEK_ANTHROPIC_URL = "https://api.deepseek.com/anthropic/v1/messages"
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8099
API_KEY = os.environ.get("DEEPSEEK_API_KEY") or next(
    (sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--api-key"), None
)

def fix_request(body: dict) -> dict:
    """Strip images and fix thinking blocks."""
    for msg in body.get("messages", []):
        c = msg.get("content")
        if isinstance(c, list):
            msg["content"] = [b for b in c if b.get("type") != "image"]
            # If after stripping images there's nothing, add a text placeholder
            if not msg["content"]:
                msg["content"] = [{"type": "text", "text": "[Image removed — DeepSeek does not support vision]"}]

    if "thinking" in body and isinstance(body["thinking"], dict):
        body["thinking"].pop("budget_tokens", None)

    return body

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")

    def do_PATCH(self):
        self._proxy("PATCH")

    def _proxy(self, method):
        target = DEEPSEEK_ANTHROPIC_URL + ("?" + self.path.split("?", 1)[1] if "?" in self.path else "")
        body_bytes = self.rfile.read(int(self.headers.get("Content-Length", 0))) if method in ("POST", "PATCH") else None

        if body_bytes:
            try:
                req = json.loads(body_bytes)
                body_bytes = json.dumps(fix_request(req)).encode()
            except json.JSONDecodeError:
                pass

        headers = {
            "x-api-key": API_KEY or self.headers.get("x-api-key", ""),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        if body_bytes and len(body_bytes) > 0:
            pass

        fwd = urllib.request.Request(target, data=body_bytes, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(fwd, timeout=300)
        except urllib.error.HTTPError as e:
            resp = e

        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() in ("transfer-encoding", "content-length", "connection"):
                continue
            self.send_header(k, v)
        self.end_headers()

        if resp.status >= 400:
            self.wfile.write(resp.read())
            return

        if body_bytes and json.loads(body_bytes).get("stream"):
            self._stream(resp)
        else:
            self.wfile.write(resp.read())

    def _stream(self, resp):
        """Forward SSE stream, unfiltered."""
        for chunk in iter(lambda: resp.read(4096), b""):
            self.wfile.write(chunk)
            self.wfile.flush()

if __name__ == "__main__":
    if not API_KEY:
        print("No API key. Set DEEPSEEK_API_KEY env var or pass --api-key")
        sys.exit(1)
    server = HTTPServer(("", PORT), ProxyHandler)
    print(f"DeepSeek proxy on http://localhost:{PORT} → {DEEPSEEK_ANTHROPIC_URL}")
    print(f"Set: export ANTHROPIC_BASE_URL=http://localhost:{PORT}")
    server.serve_forever()
