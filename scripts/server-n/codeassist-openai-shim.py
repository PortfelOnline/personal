#!/usr/bin/env python3
"""OpenAI-совместимый шим поверх Code Assist моста (ViralCraft /genai).

Vibe-Trading (как и любой langchain-клиент) умеет говорить только в
OpenAI-формате (/v1/chat/completions). Мост говорит в нативном формате Gemini
(/genai/v1beta/models/<model>:generateContent). Шим переводит один в другой.

Слушает 127.0.0.1:4405. Наружу не смотрит.

Ограничение моста: agGenerate() возвращает только текст, части functionCall
отбрасываются -> tool_calls обратно вернуть нечем. Запрошенные клиентом tools
транслируются в functionDeclarations и уходят наверх, но ответ всегда приходит
текстом. Каждый такой случай пишется в лог как TOOLS_DROPPED.
"""
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BRIDGE = os.environ.get("BRIDGE_BASE", "http://127.0.0.1:4400/genai/v1beta")
# Маршрут с полным ответом (включая functionCall). Появляется после патча моста; до него
# запросы с инструментами откатываются на BRIDGE и приходят текстом.
BRIDGE_TOOLS = os.environ.get("BRIDGE_TOOLS_BASE", BRIDGE.replace("/genai/", "/genai-tools/"))
LISTEN_HOST = os.environ.get("SHIM_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("SHIM_PORT", "4405"))
TIMEOUT = int(os.environ.get("SHIM_TIMEOUT", "300"))
MAX_BODY = 8 * 1024 * 1024

# Мост выбирает pro-модель, если в имени есть "pro" (server.ts:1244).
MODELS = ["gemini-3.1-pro", "gemini-flash"]

# tool_call_id → thoughtSignature. Gemini 3 требует вернуть подпись вместе с тем же вызовом,
# а в OpenAI-формате её негде провезти — держим соответствие у себя.
SIGNATURES: dict[str, str] = {}
MAX_SIGNATURES = 500

# 10.09.2026: конвейер статей kadastrmap и виджет 100zem.ru (gma-api, ходит к
# Google напрямую, в обход этого шима) делят один Google-квоту на модель —
# конвейер грел gemini-3.1-pro до RESOURCE_EXHAUSTED (429) часами подряд,
# и виджет получал ту же ошибку у живых клиентов ("поиск временно недоступен").
# Точного числа RPD/RPW не знаем, поэтому политика не по проценту от известного
# лимита, а по факту: первый RESOURCE_EXHAUSTED от Google — сигнал, что месячный/
# недельный потолок реально задет, дальше конвейеру ЖДАТЬ НЕДЕЛЬНОГО ОБНОВЛЕНИЯ
# (по умолчанию 7 дней от момента отказа), а не долбить квоту повторными попытками.
# Состояние в файле — переживает перезапуск шима; ручной сброс — стереть файл.
# Cooldown отдельно на каждую модель (gemini-3.1-pro и gemini-flash — разные квоты).
BREAKER_COOLDOWN_SECONDS = 7 * 24 * 3600  # 7 дней — "ждём недельного обновления"
BREAKER_STATE_PATH = "/root/.codeassist-breaker-state.json"


def _breaker_load() -> dict:
    try:
        with open(BREAKER_STATE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _breaker_save(state: dict):
    try:
        with open(BREAKER_STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError as exc:
        log.warning("не удалось сохранить состояние breaker: %s", exc)


def breaker_check(model: str):
    # Бросает RuntimeError('breaker_open:...'), если по этой модели автомат разомкнут.
    state = _breaker_load()
    open_until = state.get(model)
    if open_until and time.time() < open_until:
        remaining = open_until - time.time()
        raise RuntimeError(f"breaker_open:{model}:{remaining:.0f}")


def breaker_record_failure(model: str):
    state = _breaker_load()
    open_until = time.time() + BREAKER_COOLDOWN_SECONDS
    state[model] = open_until
    _breaker_save(state)
    log.warning(
        "breaker OPEN для %s до %s (RESOURCE_EXHAUSTED — ждём недельного обновления квоты; "
        "ручной сброс: rm %s)",
        model, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(open_until)), BREAKER_STATE_PATH,
    )


def breaker_record_success(model: str):
    state = _breaker_load()
    if model in state:
        log.info("breaker RESET для %s (успешный запрос)", model)
        del state[model]
        _breaker_save(state)


# 11.09.2026: reactive breaker (выше) срабатывает ПОСЛЕ первого 429 — этого
# просили дополнить проактивным потолком, чтобы конвейер статей/новостей САМ
# останавливался заранее, не дожидаясь исчерпания. Точного числа RPD от Google
# нет, поэтому бюджет — оценка по факту: 10.09.2026 квота у gemini-3.1-pro
# кончилась после ~552 запросов с этого моста за день (единственный calling-IP
# конвейера статей/новостей, соцсети через этот мост не ходят — проверено,
# в коде ViralCraft нет ссылок на :4400/:4405). 70% от этого — ~386, округлено
# до 380 с запасом. Актуализировать при появлении точного числа лимита.
DAILY_BUDGET_PER_MODEL = {
    "gemini-3.1-pro": 380,
}
DAILY_USAGE_PATH = "/root/.codeassist-daily-usage.json"


def _daily_load() -> dict:
    try:
        with open(DAILY_USAGE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _daily_save(data: dict):
    try:
        with open(DAILY_USAGE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError as exc:
        log.warning("не удалось сохранить дневной счётчик: %s", exc)


def _today_key() -> str:
    return time.strftime("%Y-%m-%d")  # локальная дата сервера (МСК) — сброс в полночь


def daily_check(model: str):
    """Бросает RuntimeError('daily_cap:...'), если модель уже выбрала свой дневной бюджет."""
    budget = DAILY_BUDGET_PER_MODEL.get(model)
    if budget is None:
        return
    today = _today_key()
    count = _daily_load().get(today, {}).get(model, 0)
    if count >= budget:
        raise RuntimeError(f"daily_cap:{model}:{budget}")


def daily_record(model: str):
    """Считаем КАЖДУЮ попытку до Google (включая те, что вернут 429) — они тоже жгут лимит."""
    if model not in DAILY_BUDGET_PER_MODEL:
        return
    today = _today_key()
    data = _daily_load()
    day_bucket = data.get(today, {})
    day_bucket[model] = day_bucket.get(model, 0) + 1
    # держим в файле только сегодняшний день — не растим бесконечно
    _daily_save({today: day_bucket})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("shim")


def _text_of(content) -> str:
    """Достать текст из content: строка или список частей OpenAI-формата."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                out.append(part["text"])
            elif isinstance(part, str):
                out.append(part)
        return "\n".join(out)
    return ""


# Ключи JSON Schema, которые понимает Gemini. Всё остальное (exclusiveMinimum,
# additionalProperties, $schema, $ref, allOf, oneOf, const, ...) вызывает 400 "Unknown name".
GEMINI_SCHEMA_KEYS = {
    "type", "format", "title", "description", "nullable", "enum",
    "items", "properties", "required", "anyOf", "default", "example",
    "minItems", "maxItems", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "minProperties", "maxProperties",
}


def gemini_schema(node):
    """Оставить только то подмножество JSON Schema, которое принимает Gemini."""
    if isinstance(node, list):
        return [gemini_schema(item) for item in node]
    if not isinstance(node, dict):
        return node

    out = {}
    for key, value in node.items():
        if key not in GEMINI_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            out[key] = {name: gemini_schema(sub) for name, sub in value.items()}
        elif key in ("items", "anyOf"):
            out[key] = gemini_schema(value)
        else:
            out[key] = value

    # const выражаем через enum — иначе ограничение просто потеряется.
    if "const" in node and "enum" not in out:
        out["enum"] = [node["const"]]
        out.setdefault("type", "string")
    # Схема без type Gemini не принимает; объект с properties по умолчанию object.
    if "type" not in out and "properties" in out:
        out["type"] = "object"
    return out


def to_gemini(payload: dict) -> tuple[dict, str, bool]:
    """OpenAI chat.completions -> тело generateContent для моста."""
    messages = payload.get("messages") or []
    contents, system_bits = [], []
    tool_names: dict[str, str] = {}  # tool_call_id → имя функции, для functionResponse

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        text = _text_of(msg.get("content"))

        if role == "system":
            if text:
                system_bits.append(text)
            continue
        if role == "tool":
            name = msg.get("name") or tool_names.get(msg.get("tool_call_id") or "") or "tool"
            try:
                response_payload = json.loads(text) if text else {}
            except Exception:
                response_payload = {"result": text}
            if not isinstance(response_payload, dict):
                response_payload = {"result": response_payload}
            part = {"functionResponse": {"name": name, "response": response_payload}}
            # Подряд идущие результаты — части ОДНОГО хода, а не отдельные ходы.
            if (
                contents
                and contents[-1]["role"] == "user"
                and all("functionResponse" in p for p in contents[-1]["parts"])
            ):
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})
            continue

        gem_role = "model" if role == "assistant" else "user"
        parts = []
        if text:
            parts.append({"text": text})
        for call in msg.get("tool_calls") or []:
            fn = call.get("function") if isinstance(call, dict) else None
            if not isinstance(fn, dict) or not fn.get("name"):
                continue
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            call_id = call.get("id") or ""
            tool_names[call_id] = fn["name"]
            part = {"functionCall": {"name": fn["name"], "args": args}}
            signature = SIGNATURES.get(call_id)
            if signature:
                part["thoughtSignature"] = signature
            parts.append(part)
        if parts:
            contents.append({"role": gem_role, "parts": parts})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": " "}]}]
    elif contents[-1]["role"] == "model":
        # Диалог оканчивается ходом модели: generateContent продолжать собственный ход не умеет
        # и возвращает пустой кандидат. Нужен завершающий ход user.
        contents.append({"role": "user", "parts": [{"text": "Continue."}]})

    body: dict = {"contents": contents}
    if system_bits:
        body["systemInstruction"] = {
            "role": "user",
            "parts": [{"text": "\n\n".join(system_bits)}],
        }

    gen_cfg = {}
    if isinstance(payload.get("temperature"), (int, float)):
        gen_cfg["temperature"] = payload["temperature"]
    if isinstance(payload.get("top_p"), (int, float)):
        gen_cfg["topP"] = payload["top_p"]
    if isinstance(payload.get("max_tokens"), int):
        gen_cfg["maxOutputTokens"] = payload["max_tokens"]
    if gen_cfg:
        body["generationConfig"] = gen_cfg

    tools_dropped = False
    decls = []
    for tool in payload.get("tools") or []:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(fn, dict) or not fn.get("name"):
            continue
        decl = {"name": fn["name"]}
        if fn.get("description"):
            decl["description"] = fn["description"]
        if isinstance(fn.get("parameters"), dict):
            decl["parameters"] = gemini_schema(fn["parameters"])
        decls.append(decl)
    if decls:
        body["tools"] = [{"functionDeclarations": decls}]
        tools_dropped = True

    model = payload.get("model") or "gemini-3.1-pro"
    return body, model, tools_dropped


def _post(base: str, model: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{base}/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def call_bridge(model: str, body: dict, want_tools: bool = False) -> tuple[str, list]:
    """Вернуть (текст, вызовы инструментов). Вызовы приходят только с маршрута /genai-tools."""
    breaker_check(model)
    daily_check(model)
    daily_record(model)

    data = None
    try:
        if want_tools:
            try:
                data = _post(BRIDGE_TOOLS, model, body)
            except urllib.error.HTTPError as exc:
                if exc.code not in (404, 405):
                    raise
                log.warning("маршрут %s недоступен (%s) — откат на текстовый /genai", BRIDGE_TOOLS, exc.code)
        if data is None:
            data = _post(BRIDGE, model, body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace") if hasattr(exc, "read") else ""
        if exc.code == 429 or "RESOURCE_EXHAUSTED" in detail:
            breaker_record_failure(model)
        raise

    breaker_record_success(model)

    chunks, calls = [], []
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])
            elif isinstance(part.get("functionCall"), dict):
                calls.append({
                    "call": part["functionCall"],
                    "signature": part.get("thoughtSignature"),
                })
    return "".join(chunks), calls


def openai_response(model: str, text: str, calls: list | None = None) -> dict:
    now = int(time.time())
    message = {"role": "assistant", "content": text or None}
    finish = "stop"
    if calls:
        tool_calls = []
        for i, entry in enumerate(calls):
            fn = entry.get("call") or {}
            call_id = f"call_{now}_{i}"
            if entry.get("signature"):
                if len(SIGNATURES) >= MAX_SIGNATURES:
                    SIGNATURES.pop(next(iter(SIGNATURES)))
                SIGNATURES[call_id] = entry["signature"]
            tool_calls.append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": fn.get("name") or "unknown",
                    "arguments": json.dumps(fn.get("args") or {}, ensure_ascii=False),
                },
            })
        message["tool_calls"] = tool_calls
        finish = "tool_calls"
    return {
        "id": f"chatcmpl-bridge-{now}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish,
        }],
        # Мост токены не отдаёт; грубая оценка, чтобы клиенты не падали на None.
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": max(1, len(text) // 4),
            "total_tokens": max(1, len(text) // 4),
        },
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        log.info("%s %s", self.address_string(), fmt % args)

    def _send(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code: int, message: str):
        self._send(code, {"error": {"message": message, "type": "bridge_error"}})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/health", "/v1/health"):
            self._send(200, {"ok": True, "bridge": BRIDGE})
            return
        if path.endswith("/models"):
            now = int(time.time())
            self._send(200, {
                "object": "list",
                "data": [
                    {"id": m, "object": "model", "created": now, "owned_by": "code-assist"}
                    for m in MODELS
                ],
            })
            return
        self._error(404, f"unknown path {path}")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if not re.search(r"/chat/completions$", path):
            self._error(404, f"unknown path {path}")
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._error(413, "request body too large")
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self._error(400, f"bad json: {exc}")
            return
        if not isinstance(payload, dict):
            self._error(400, "body must be a JSON object")
            return

        body, model, has_tools = to_gemini(payload)

        try:
            text, calls = call_bridge(model, body, want_tools=has_tools)
            if has_tools and not calls and not text:
                log.warning("модель ответила пустым при заявленных tools — вероятно, "
                            "functionCall потерян мостом (нужен маршрут /genai-tools)")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            log.error("bridge HTTP %s: %s", exc.code, detail)
            try:
                with open("/tmp/last_failed_gemini_request.json", "w", encoding="utf-8") as fh:
                    json.dump({"model": model, "body": body}, fh, ensure_ascii=False)
                log.info("тело запроса сохранено в /tmp/last_failed_gemini_request.json "
                         "(инструментов: %d)",
                         len((body.get("tools") or [{}])[0].get("functionDeclarations", [])))
            except Exception as dump_error:  # диагностика не должна ломать ответ
                log.warning("не удалось сохранить тело запроса: %s", dump_error)
            self._error(502, f"bridge {exc.code}: {detail}")
            return
        except RuntimeError as exc:
            if str(exc).startswith("breaker_open:"):
                _, brk_model, remaining = str(exc).split(":", 2)
                log.info("отклонён локально (breaker open): model=%s осталось=%sс", brk_model, remaining)
                self._error(429, f"quota exhausted for {brk_model}, waiting for weekly reset, retry in {remaining}s")
                return
            if str(exc).startswith("daily_cap:"):
                _, cap_model, budget = str(exc).split(":", 2)
                log.info("отклонён локально (дневной потолок %s/%s исчерпан): model=%s", budget, budget, cap_model)
                self._error(429, f"daily self-imposed cap reached for {cap_model} ({budget}/day), resets at midnight")
                return
            log.error("bridge failure: %s", exc)
            self._error(502, f"bridge unavailable: {exc}")
            return
        except Exception as exc:
            log.error("bridge failure: %s", exc)
            self._error(502, f"bridge unavailable: {exc}")
            return

        log.info("BRIDGE_RESULT tools=%s text_len=%d calls=%d", has_tools, len(text or ''), len(calls))
        result = openai_response(model, text, calls)

        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            now = int(time.time())
            delta = {"role": "assistant"}
            if text:
                delta["content"] = text
            message_tool_calls = result["choices"][0]["message"].get("tool_calls")
            if message_tool_calls:
                # В потоке у каждого вызова обязан быть index — без него клиент их не соберёт.
                delta["tool_calls"] = [
                    {**call, "index": i} for i, call in enumerate(message_tool_calls)
                ]
            first = {
                "id": result["id"], "object": "chat.completion.chunk",
                "created": now, "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
            }
            last = {
                "id": result["id"], "object": "chat.completion.chunk",
                "created": now, "model": model,
                "choices": [{"index": 0, "delta": {},
                             "finish_reason": "tool_calls" if message_tool_calls else "stop"}],
            }
            for chunk in (first, last):
                self.wfile.write(
                    b"data: " + json.dumps(chunk, ensure_ascii=False).encode("utf-8") + b"\n\n"
                )
            self.wfile.write(b"data: [DONE]\n\n")
            self.close_connection = True
            return

        self._send(200, result)


def main():
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    server.daemon_threads = True
    log.info("shim listening on %s:%s -> %s", LISTEN_HOST, LISTEN_PORT, BRIDGE)
    server.serve_forever()


if __name__ == "__main__":
    main()
