"""
DeepSeek API — прямой доступ к DeepSeek V4 без Claude Code.

С оптимизацией токенов:
- Pre-call оценка через tiktoken (cl100k_base)
- Post-call usage из API ответа
- Dynamic max_tokens под контекст 64K
- Расчёт стоимости + JSONL-лог расхода
- Предупреждения при длинных промптах

Импорт:
  from deepseek_api import chat, stream_chat, count_tokens
"""

import os
import json
import time
import sys
import re
import urllib.request
import urllib.error

# ── Конфигурация ──────────────────────────────────────────────

BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-pro"
FAST_MODEL = "deepseek-v4-flash"
AUTO_MODEL = "auto"  # автоматический выбор flash/pro

CONTEXT_WINDOW = 64_000          # 64K токенов DeepSeek V4
MAX_TOKENS_DEFAULT = 8192
MAX_TOKENS_MIN = 256
TOKEN_HEADROOM = 1024            # резерв на системные промпты API

# Цены DeepSeek (USD за 1M токенов) — актуальны на 2026-04
PRICING = {
    "deepseek-v4-pro":   {"input": 2.00, "output": 8.00},
    "deepseek-v4-flash": {"input": 0.30, "output": 1.20},
}

DEFAULT_LOG_PATH = os.path.expanduser("~/.local/var/deepseek-usage.jsonl")

# ── TokenCounter (tiktoken) ───────────────────────────────────

_ENCODING = None  # lazy init


def _get_encoding():
    """Lazy-загрузка tiktoken encoding.
    Падает молча если tiktoken не установлен — fallback на char-based оценку."""
    global _ENCODING
    if _ENCODING is None:
        try:
            import tiktoken
            _ENCODING = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            _ENCODING = False  # сигнал "не пытаться снова"
    return _ENCODING if _ENCODING is not False else None


def count_tokens(text: str) -> int:
    """Оценка числа токенов через tiktoken (cl100k_base).
    DeepSeek V4 использует токенизатор, близкий к GPT-4.
    Без tiktoken — грубая оценка len//2."""
    enc = _get_encoding()
    if enc:
        return len(enc.encode(text))
    return len(text) // 2


def count_messages(messages: list) -> int:
    """Сумма токенов во всех сообщениях."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content)
        elif isinstance(content, list):
            for part in content:
                total += count_tokens(part.get("text", "")) if isinstance(part, dict) else 0
    return total


def format_tokens(n: int) -> str:
    """12,345,678 → формат с разделителями."""
    return f"{n:,}"


# ── Cost calculator ────────────────────────────────────────────

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    """Расчёт стоимости запроса в USD по ценам DeepSeek."""
    rates = PRICING.get(model, PRICING[DEFAULT_MODEL])
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost, 6),
    }


# ── UsageLogger ────────────────────────────────────────────────

class UsageLogger:
    """Логирует каждый API-вызов в JSONL-файл.
    Файл: ~/.local/var/deepseek-usage.jsonl (по умолчанию)."""

    def __init__(self, path: str = DEFAULT_LOG_PATH):
        self.path = path
        self._ensure_dir()

    def _ensure_dir(self):
        parent = os.path.dirname(self.path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    def log(self, model: str, prompt_tokens: int, completion_tokens: int,
            system_prompt_len: int = 0, tags: list | None = None):
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "system_prompt_len": system_prompt_len,
            "tags": tags or [],
        }
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        entry.update(cost)

        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # silent fail — логи не должны ломать запрос

    def summary(self) -> dict:
        """Итоги за всё время из существующего лога."""
        if not os.path.exists(self.path):
            return {"total_tokens": 0, "total_cost": 0.0, "by_model": {}}

        total_input = 0
        total_output = 0
        total_cost = 0.0
        counts = {}

        try:
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    m = entry.get("model", "unknown")
                    counts.setdefault(m, {"calls": 0, "input": 0, "output": 0, "cost": 0.0})
                    counts[m]["calls"] += 1
                    counts[m]["input"] += entry.get("prompt_tokens", 0)
                    counts[m]["output"] += entry.get("completion_tokens", 0)
                    counts[m]["cost"] += entry.get("total_cost", 0.0)
                    total_input += entry.get("prompt_tokens", 0)
                    total_output += entry.get("completion_tokens", 0)
                    total_cost += entry.get("total_cost", 0.0)
        except (OSError, json.JSONDecodeError):
            pass

        return {
            "total_tokens": total_input + total_output,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 6),
            "by_model": counts,
        }


_usage_logger = UsageLogger()


# ── Dynamic max_tokens ─────────────────────────────────────────

def _resolve_max_tokens(estimated_prompt: int, requested: int = MAX_TOKENS_DEFAULT) -> int:
    """Не запрашивать больше токенов, чем влезет в контекст 64K.
    Пример: промпт 50K → max_tokens = 64K - 50K - 1K = 13K (а не 8K)."""
    budget = CONTEXT_WINDOW - estimated_prompt - TOKEN_HEADROOM
    resolved = min(requested, budget)
    return max(resolved, MAX_TOKENS_MIN)


# ── Auto model selection (flash vs pro) ─────────────────────────

# Ключевые слова-маркеры: простые задачи → flash
_SIMPLE_MARKERS = {
    "translate", "summary", "summarize", "format", "spell", "grammar",
    "convert", "short", "hello", "hi", "test", "echo", "ping",
    "capitalize", "lowercase", "uppercase", "trim", "strip",
    "plural", "singular", "synonym", "antonym",
}

# Сложные задачи → pro
_COMPLEX_MARKERS = {
    "code", "implement", "debug", "refactor", "analyze", "architect",
    "design", "review", "optimize", "algorithm", "architecture",
    "complex", "async", "concurrency", "parallel", "distributed",
    "database", "query", "migration", "schema", "api", "endpoint",
    "authentication", "authorization", "encrypt", "decrypt",
    "performance", "benchmark", "profiling",
}


def _select_model(prompt: str, system: str = "", temperature: float | None = None,
                  json_mode: bool = False, model: str = DEFAULT_MODEL) -> str:
    """Автоматический выбор модели на основе эвристик.

    Правила:
    - Длина: < 200 токенов → склоняет к flash
    - Ключевые слова (word-boundary): translate/summarize → flash; code/implement → pro
    - Temperature: < 0.3 → flash (фактуальный); > 0.7 → pro (творческий)
    - JSON mode: → flash (структурные данные)
    - System prompt > 500 токенов → pro (серьёзная задача)

    Возвращает: "deepseek-v4-flash" или "deepseek-v4-pro"
    """
    if model != AUTO_MODEL:
        return model

    score = 0  # положительный → pro, отрицательный → flash

    # ── Длина промпта ──
    prompt_tok = count_tokens(prompt) + count_tokens(system)
    if prompt_tok < 200:
        score -= 1  # короткий → скорее простой
    elif prompt_tok > 2000:
        score += 1  # длинный → скорее сложный

    # ── Ключевые слова (word-boundary, регистронезависимо) ──
    # Используем \b чтобы "api" не совпало внутри "capital"
    lower = (prompt + " " + system).lower()

    simple_hits = 0
    complex_hits = 0
    for m in _SIMPLE_MARKERS:
        if re.search(rf"\b{re.escape(m)}\b", lower):
            simple_hits += 1
    for m in _COMPLEX_MARKERS:
        if re.search(rf"\b{re.escape(m)}\b", lower):
            complex_hits += 1

    # Первое совпадение решает (чтобы "test code" не пошло на flash)
    if complex_hits > 0:
        score += 1
    elif simple_hits > 0:
        score -= 1
    elif prompt_tok < 100 and "?" in prompt:
        score -= 1  # короткий вопрос без сложных маркеров → flash

    # ── Temperature (только если явно не дефолтная 0.7) ──
    if temperature is not None and temperature != 0.7:
        if temperature <= 0.3:
            score -= 1  # низкая → фактуальный → flash
        elif temperature >= 0.7:
            score += 1  # высокая → творческий → pro

    # ── JSON mode ──
    if json_mode:
        score -= 1  # структурные данные → flash

    # ── Итог ──
    if score <= -1:
        # score -1 уже основание для Flash:
        # короткий промпт, простой маркер, json_mode или низкая температура — каждый сам по себе
        return FAST_MODEL
    return DEFAULT_MODEL  # pro для score >= 0 (есть сложные маркеры или длинный/смешанный промпт)


# ── API key ────────────────────────────────────────────────────

def _api_key():
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY or ANTHROPIC_AUTH_TOKEN not set")
    return key


# ── Anti-meander warnings ──────────────────────────────────────

_WARN_THRESHOLD = 4000


def _check_prompt_length(system: str, prompt: str) -> list[str]:
    """Предупреждения если промпт/система выходят за разумные пределы."""
    system_tokens = count_tokens(system) if system else 0
    prompt_tokens = count_tokens(prompt)
    warnings = []

    if system_tokens > _WARN_THRESHOLD:
        warnings.append(
            f"⚠️ System prompt: {format_tokens(system_tokens)} токенов "
            f"(рекомендация < {format_tokens(_WARN_THRESHOLD)}). "
            "Каждый токен system prompt оплачивается при каждом вызове."
        )
    if prompt_tokens > _WARN_THRESHOLD:
        warnings.append(
            f"⚠️ Prompt: {format_tokens(prompt_tokens)} токенов. "
            "Это >6% контекстного окна (64K). "
            "Подумайте о сокращении."
        )
    total_est = system_tokens + prompt_tokens + TOKEN_HEADROOM
    if total_est > CONTEXT_WINDOW * 0.8:
        warnings.append(
            f"⚠️ Общий промпт ~{format_tokens(total_est)} токенов — "
            f">{format_tokens(int(CONTEXT_WINDOW * 0.8))} (80% контекста). "
            "Ответ может быть обрезан."
        )
    return warnings


# ── API call ───────────────────────────────────────────────────

def _api_call(messages, model=DEFAULT_MODEL, stream=False, json_mode=False,
              temperature=0.7, max_tokens=None, **kwargs):
    """Низкоуровневый вызов DeepSeek Chat API.

    Отличия от исходной версии:
    - dynamic max_tokens
    - возвращает (content, usage_dict | None)

    Returns:
        (content: str, usage: dict | None)
    """
    if max_tokens is None:
        max_tokens = MAX_TOKENS_DEFAULT

    estimated = count_messages(messages)
    resolved_max = _resolve_max_tokens(estimated, max_tokens)

    body = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": resolved_max,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    body.update(kwargs)

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

    return content, usage


# ── chat() ─────────────────────────────────────────────────────

def chat(prompt, system="", model=AUTO_MODEL, return_usage=False,
         usage_log=True, tags=None, **kwargs):
    """Вызов DeepSeek (не streaming).

    Args:
        prompt: текст запроса
        system: системный промпт
        model: "auto" (default) → выбирает flash/pro автоматически,
               или конкретная модель ("deepseek-v4-pro", "deepseek-v4-flash")
        return_usage: True → возвращает (content, usage_dict)
        usage_log: записывать в JSONL-лог
        tags: метки для лога

    Возвращает:
        str или (str, dict | None)
    """
    # Авто-выбор модели
    temperature = kwargs.get("temperature", 0.7)
    json_mode = kwargs.get("json_mode", False)
    resolved_model = _select_model(prompt, system, temperature, json_mode, model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # anti-meander: предупреждения в stderr
    warnings = _check_prompt_length(system, prompt)
    for w in warnings:
        print(w, file=sys.stderr)

    if model == AUTO_MODEL:
        print(f"  → {resolved_model}", file=sys.stderr)

    content, usage = _api_call(messages, model=resolved_model, stream=False, **kwargs)

    if usage_log and usage:
        _usage_logger.log(
            model=resolved_model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            system_prompt_len=count_tokens(system) if system else 0,
            tags=tags,
        )

    if return_usage:
        return content, usage
    return content


# ── stream_chat() ─────────────────────────────────────────────

def stream_chat(prompt, system="", model=AUTO_MODEL, callback=None,
                usage_log=True, tags=None, **kwargs):
    """Streaming вызов DeepSeek.

    DeepSeek в streaming-режиме шлёт usage
    в финальном chunk перед [DONE].

    Args:
        prompt: текст запроса
        system: системный промпт
        model: "auto" (default) → выбирает flash/pro автоматически,
               или конкретная модель
        callback: вызывается для каждого фрагмента
        usage_log: записывать в JSONL-лог
        tags: метки для лога

    Возвращает:
        (full_text: str, usage: dict | None)
    """
    # Авто-выбор модели
    temperature = kwargs.get("temperature", 0.7)
    json_mode = kwargs.get("json_mode", False)
    resolved_model = _select_model(prompt, system, temperature, json_mode, model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # anti-meander: выводим в stderr, чтобы не загрязнять stdout
    warnings = _check_prompt_length(system, prompt)
    for w in warnings:
        print(w, file=sys.stderr)

    if model == AUTO_MODEL:
        print(f"  → {resolved_model}", file=sys.stderr)

    estimated = count_messages(messages)
    resolved_max = _resolve_max_tokens(estimated, kwargs.pop("max_tokens", MAX_TOKENS_DEFAULT))

    body = {
        "model": resolved_model,
        "messages": messages,
        "stream": True,
        "temperature": kwargs.pop("temperature", 0.7),
        "max_tokens": resolved_max,
    }
    body.update(kwargs)

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    full = []
    usage = None
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                # DeepSeek шлёт usage в отдельном chunk
                if "usage" in chunk:
                    usage = chunk["usage"]
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    if callback:
                        callback(content)
                    else:
                        print(content, end="", flush=True)
                    full.append(content)
            except json.JSONDecodeError:
                continue

    if not callback:
        print()

    full_text = "".join(full)

    # Если usage не пришёл — fallback на estimation
    prompt_tokens = usage.get("prompt_tokens", 0) if usage else estimated
    completion_tokens = usage.get("completion_tokens", 0) if usage else count_tokens(full_text)

    if usage_log:
        _usage_logger.log(
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            system_prompt_len=count_tokens(system) if system else 0,
            tags=tags,
        )

    return full_text, usage


# ── Usage summary ──────────────────────────────────────────────

def get_usage_summary(path: str = DEFAULT_LOG_PATH) -> dict:
    """Сводка по расходу из JSONL-лога."""
    return UsageLogger(path).summary()


# ── Usage Audit ────────────────────────────────────────────────

_PRO_SCORE_THRESHOLD = -1  # score >= этого → Pro, иначе Flash


def _reroute_score(entry: dict) -> int:
    """Оценка: какой бы скор дала _select_model для этого запроса.
    Используется для аудита: если Pro-запрос имеет скор <= -1 → зря на Pro
    (порог синхронизирован с _select_model)."""
    # У нас нет полного prompt, system, temperature в логе.
    # Используем то, что есть: prompt_tokens, completion_tokens, model
    prompt_len = entry.get("prompt_tokens", 0)
    comp_len = entry.get("completion_tokens", 0)

    score = 0
    if prompt_len < 200:
        score -= 1  # короткий → flash
    elif prompt_len > 2000:
        score += 1  # длинный → pro

    # Если ответ очень короткий (< 100 токенов) — дополнительный сигнал к flash
    if comp_len > 0 and comp_len < 100 and prompt_len < 500:
        score -= 1  # короткий ответ + недлинный промпт → flash

    return score


def _model_key(entry: dict) -> str:
    """normalize 'auto' → resolved model, otherwise as-is."""
    m = entry.get("model", "unknown")
    if m == "auto":
        # В старых записях могло быть auto — определяем по стоимости
        cost_in = entry.get("input_cost", 0)
        # Input cost per token: Pro = 2e-6, Flash = 0.3e-6
        input_tok = entry.get("prompt_tokens", 1)
        if input_tok > 0 and cost_in > 0:
            rate = cost_in / (input_tok / 1_000_000)
            if rate > 1.0:
                return "deepseek-v4-pro"
            return "deepseek-v4-flash"
        return "unknown"
    return m


def audit_usage(path: str = DEFAULT_LOG_PATH) -> dict:
    """Анализ лога: поиск misrouting, waste, рекомендации.

    Returns:
        dict с разделами: summary, misrouted, waste, recommendations
    """
    if not os.path.exists(path):
        return {"error": f"Лог не найден: {path}"}

    with open(path) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    if not entries:
        return {"error": "Лог пуст"}

    result = {
        "total_calls": len(entries),
        "total_cost": 0.0,
        "pro_calls": 0,
        "flash_calls": 0,
        "pro_cost": 0.0,
        "flash_cost": 0.0,
        "misrouted": [],        # Pro-запросы, которые могли быть Flash
        "waste": [],            # max_tokens waste
        "recommendations": [],
    }

    for entry in entries:
        m = _model_key(entry)
        cost = entry.get("total_cost", 0)
        result["total_cost"] += cost

        is_pro = "pro" in m
        is_flash = "flash" in m

        if is_pro:
            result["pro_calls"] += 1
            result["pro_cost"] += cost

            # Проверка misrouting (порог синхронизирован с _select_model)
            score = _reroute_score(entry)
            if score <= -1:
                # Этот запрос мог быть Flash
                # Flash стоит ~15% от Pro (0.30 vs 2.00 за input, 1.20 vs 8.00 за output)
                flash_ratio = 0.15
                result["misrouted"].append({
                    "timestamp": entry.get("timestamp", ""),
                    "prompt_tokens": entry.get("prompt_tokens", 0),
                    "completion_tokens": entry.get("completion_tokens", 0),
                    "cost": cost,
                    "potential_saving": round(cost * (1 - flash_ratio), 6),
                })

        elif is_flash:
            result["flash_calls"] += 1
            result["flash_cost"] += cost

        # Waste: если completion_tokens << max_tokens
        # (max_tokens нет в логе, оцениваем по completion_tokens)
        comp = entry.get("completion_tokens", 0)
        if comp < 50 and is_pro and comp > 0:
            # Маленький ответ на Pro — переплата
            result["waste"].append({
                "timestamp": entry.get("timestamp", ""),
                "model": m,
                "completion_tokens": comp,
                "cost": cost,
            })

    # ── Рекомендации ──
    if result["misrouted"]:
        total_waste = sum(r["potential_saving"] for r in result["misrouted"])
        n = len(result["misrouted"])
        result["recommendations"].append(
            f"{n} Pro-запросов могли быть Flash (экономия ~${total_waste:.6f}). "
            f"Auto-routing решит это автоматически."
        )

    if result["waste"]:
        n = len(result["waste"])
        result["recommendations"].append(
            f"{n} Pro-запросов с очень короткими ответами (<50 токенов). "
            f"Возможно стоило использовать Flash."
        )

    # Оптимизация порога
    pro_share = result["pro_cost"] / result["total_cost"] * 100 if result["total_cost"] else 0
    flash_share = result["flash_cost"] / result["total_cost"] * 100 if result["total_cost"] else 0

    if pro_share > 90 and result["pro_calls"] > 5:
        result["recommendations"].append(
            f"Pro: {pro_share:.0f}% расходов ({result['pro_calls']} вызовов). "
            f"Порог уже снижен до -1. Если дисбаланс сохраняется — проверьте "
            f"маркеры _SIMPLE_MARKERS / _COMPLEX_MARKERS."
        )

    result["pro_share_pct"] = round(pro_share, 1)
    result["flash_share_pct"] = round(flash_share, 1)
    return result


def run_audit(path: str = DEFAULT_LOG_PATH):
    """Pretty-print audit report."""
    report = audit_usage(path)

    if "error" in report:
        print(f"Ошибка: {report['error']}")
        return

    print("=" * 50)
    print("  АУДИТ ПОТРЕБЛЕНИЯ DEEPSEEK")
    print("=" * 50)
    print()
    print(f"  Всего запросов:     {report['total_calls']}")
    print(f"  Pro:                {report['pro_calls']} (${report['pro_cost']:.6f}, {report['pro_share_pct']}%)")
    print(f"  Flash:              {report['flash_calls']} (${report['flash_cost']:.6f}, {report['flash_share_pct']}%)")
    print(f"  Общая стоимость:    ${report['total_cost']:.6f}")
    print()

    if report["misrouted"]:
        print("─" * 50)
        print("  ⚠️  MISROUTING (Pro → мог быть Flash)")
        print("─" * 50)
        total_saving = sum(r["potential_saving"] for r in report["misrouted"])
        for r in report["misrouted"]:
            print(f"  {r['timestamp']}")
            print(f"    prompt={r['prompt_tokens']} resp={r['completion_tokens']} "
                  f"cost=${r['cost']:.6f} → могло быть ${r['cost']-r['potential_saving']:.6f}")
        print(f"  Потенциальная экономия: ${total_saving:.6f}")
        print()

    if report["waste"]:
        print("─" * 50)
        print("  ⚠️  WASTE (маленький ответ на Pro)")
        print("─" * 50)
        for w in report["waste"]:
            print(f"  {w['timestamp']} | {w['model']} | "
                  f"{w['completion_tokens']} токенов | ${w['cost']:.6f}")
        print()

    if report["recommendations"]:
        print("─" * 50)
        print("  РЕКОМЕНДАЦИИ")
        print("─" * 50)
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")
        print()

    print("=" * 50)


# ── MCP / Plugin Optimization ─────────────────────────────────

_PLUGINS_DIR = os.path.expanduser("~/.claude/plugins")
_PLUGINS_CACHE = os.path.join(_PLUGINS_DIR, "cache")
_INSTALLED_JSON = os.path.join(_PLUGINS_DIR, "installed_plugins.json")


def _walk_plugin_versions() -> list[dict]:
    """Scan plugin cache: версия + размер + установленные копии."""
    results = []
    cache = _PLUGINS_CACHE
    if not os.path.isdir(cache):
        return results

    for namespace in os.listdir(cache):
        ns_path = os.path.join(cache, namespace)
        if not os.path.isdir(ns_path):
            continue
        for plugin in os.listdir(ns_path):
            plugin_path = os.path.join(ns_path, plugin)
            if not os.path.isdir(plugin_path):
                continue
            for version in os.listdir(plugin_path):
                ver_path = os.path.join(plugin_path, version)
                if not os.path.isdir(ver_path):
                    continue
                total_size = 0
                file_count = 0
                for root, _, files in os.walk(ver_path):
                    for f in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, f))
                            file_count += 1
                        except OSError:
                            pass
                results.append({
                    "namespace": namespace,
                    "plugin": plugin,
                    "version": version,
                    "path": ver_path,
                    "size": total_size,
                    "files": file_count,
                })
    return results


def audit_plugins() -> dict:
    """Анализ плагинов: дубликаты, размеры, оценка MCP токенов.

    Returns:
        {
            total_plugins, total_size, duplicate_versions: [],
            mcp_tool_estimate: токенов, recommendations: []
        }
    """
    versions = _walk_plugin_versions()

    # Группировка по имени плагина
    by_plugin: dict[str, list] = {}
    for v in versions:
        key = f"{v['namespace']}/{v['plugin']}"
        by_plugin.setdefault(key, []).append(v)

    total_size = sum(v["size"] for v in versions)
    duplicates = []
    for name, vers in by_plugin.items():
        if len(vers) > 1:
            # Сортируем по размеру — большая версия скорее актуальная
            vers.sort(key=lambda x: -x["size"])
            duplicates.append({
                "plugin": name,
                "versions": [
                    {"version": v["version"][:10],
                     "size_mb": round(v["size"] / 1024 / 1024, 1),
                     "is_largest": i == 0}
                    for i, v in enumerate(vers)
                ],
                "duplicates": len(vers) - 1,
                "waste_mb": round(sum(v["size"] for v in vers[1:]) / 1024 / 1024, 1),
            })

    # Оценка MCP tool token footprint
    # ~20-40 средних MCP tools, по ~40 токенов каждый
    mcp_tool_estimate = len(versions) * 2 * 44  # ~2 tools на плагин × ~44 токена
    mcp_tool_estimate = min(mcp_tool_estimate, 2500)  # потолок

    recommendations = []

    total_dup_waste = sum(d["waste_mb"] for d in duplicates)
    if total_dup_waste > 10:
        recommendations.append(
            f"Дубликаты плагинов: ~{total_dup_waste}MB можно освободить. "
            "Удалите user-scope установки (оставьте project-scope)."
        )

    if mcp_tool_estimate > 1200:
        recommendations.append(
            f"MCP tool описания: ~{mcp_tool_estimate} токенов в system prompt. "
            "Рассмотрите блокировку неиспользуемых плагинов."
        )

    # Тяжёлые плагины
    heavy = sorted(versions, key=lambda x: -x["size"])[:5]
    heavy_report = [
        f"{h['namespace']}/{h['plugin']} ({round(h['size']/1024/1024, 1)}MB)"
        for h in heavy
    ]
    recommendations.append(
        f"Самые тяжёлые: {', '.join(heavy_report)}. "
        "Если не используются → добавьте в blocklist."
    )

    return {
        "total_plugins": len(by_plugin),
        "total_versions": len(versions),
        "total_size_mb": round(total_size / 1024 / 1024, 1),
        "mcp_tool_estimate": mcp_tool_estimate,
        "duplicates": duplicates,
        "total_dup_waste_mb": total_dup_waste,
        "recommendations": recommendations,
    }


def run_audit_plugins():
    """Pretty-print plugin audit."""
    report = audit_plugins()

    print("=" * 50)
    print("  АУДИТ ПЛАГИНОВ / MCP")
    print("=" * 50)
    print()
    print(f"  Плагинов в кеше:   {report['total_plugins']}")
    print(f"  Версий (с копиями): {report['total_versions']}")
    print(f"  Размер кеша:       {report['total_size_mb']}MB")
    print(f"  MCP tools в prompt: ~{report['mcp_tool_estimate']} токенов")
    print()

    if report["duplicates"]:
        print("─" * 50)
        print("  ⚠️  ДУБЛИКАТЫ (project + user scope)")
        print("─" * 50)
        for d in report["duplicates"][:10]:
            print(f"  {d['plugin']}:")
            for v in d["versions"]:
                marker = " ← latest" if v["is_largest"] else ""
                print(f"    {v['version']}  {v['size_mb']}MB{marker}")
            print(f"    waste: {d['waste_mb']}MB ({d['duplicates']} копий)")
            print()

    print("─" * 50)
    print("  РЕКОМЕНДАЦИИ")
    print("─" * 50)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")
    print()
    print("=" * 50)


def run_optimize():
    """Полная оптимизация: DeepSeek audit + Plugin audit."""
    print()
    run_audit()
    print()
    run_audit_plugins()

def list_models():
    """Список доступных моделей."""
    req = urllib.request.Request(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {_api_key()}"},
    )
    with urllib.request.urlopen(req) as resp:
        return [m["id"] for m in json.loads(resp.read()).get("data", [])]
