# DeepSeek API — прямой доступ без Claude Code

**Дата**: 2026-04-28
**Цель**: возможность работать с DeepSeek V4 напрямую, независимо от Claude Code API

## Архитектура

```
~/.local/bin/deepseek          # CLI (интерфейс пользователя)
        ↓
~/.local/lib/deepseek_api.py   # Библиотека (логика)
        ↓
api.deepseek.com/v1            # OpenAI-совместимый эндпоинт
```

DeepSeek API имеет **двойную совместимость**:
- `api.deepseek.com/v1` — OpenAI-формат (используем)
- `api.deepseek.com/anthropic` — Anthropic-формат

Один и тот же API-ключ работает на обоих эндпоинтах.

## Модели

| Модель | Назначение |
|--------|------------|
| `deepseek-v4-pro` | Основная (default) |
| `deepseek-v4-flash` | Быстрая |

## Использование CLI

```bash
# Streaming (по умолчанию) — читает stdin
echo "Привет, как дела?" | deepseek

# Не-streaming
deepseek -p "Вопрос" --no-stream

# Быстрая модель
deepseek -m deepseek-v4-flash -p "Быстрый ответ"

# Системный промпт
deepseek -s "Ты — ассистент" -p "Задача"

# JSON mode
deepseek -j -p '{"key": "value"}'

# Temperature
deepseek -t 0.3 -p "Точный ответ"

# Список моделей
deepseek --list-models
```

## Использование из Python

```python
from deepseek_api import chat, stream_chat

# Простой вызов
answer = chat("Вопрос")

# Быстрая модель + системный промпт
answer = chat("Вопрос", system="Ты — эксперт", model="deepseek-v4-flash")

# Streaming с callback
def on_chunk(text):
    print(text, end="", flush=True)

stream_chat("Длинный ответ", callback=on_chunk)
```

## Переменные окружения

```bash
export DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY"
export PYTHONPATH="$HOME/.local/lib${PYTHONPATH:+:$PYTHONPATH}"
```

Добавлены в `~/.bashrc` и `~/.zshrc`.
API-ключ также читается из `ANTHROPIC_AUTH_TOKEN` (fallback).

## Файлы

| Файл | Назначение |
|------|-----------|
| `~/.local/lib/deepseek_api.py` | Библиотека: `chat()`, `stream_chat()`, `list_models()` |
| `~/.local/bin/deepseek` | CLI-инструмент |
| `~/.bashrc` | DEEPSEEK_API_KEY + PYTHONPATH |
| `~/.zshrc` | DEEPSEEK_API_KEY + PYTHONPATH |

## Оптимизация токенов (2026-04-30)

Добавлен pre-call и post-call токен-каунтинг с tiktoken (cl100k_base).

### TokenCounter
- `count_tokens(text)` — оценка через tiktoken (fallback `len//2` без tiktoken)
- `count_messages(messages)` — сумма по всем сообщениям
- Без tiktoken не падает, использует char-based fallback

### Dynamic max_tokens
- DeepSeek V4 context window = 64K токенов
- `max_tokens = min(requested, 64K - estimated_prompt - 1K headroom)`
- Нижняя граница: 256 токенов
- Предотвращает запрос большего числа токенов, чем влезает в контекст

### Usage из API
- `_api_call()` возвращает `(content, usage_dict)` где `usage = {prompt_tokens, completion_tokens, total_tokens}`
- `chat(return_usage=True)` — возвращает кортеж вместо строки (backward compat)
- `stream_chat()` — ловит usage из финального chunk перед `[DONE]`

### Cost calculator
- Pro: $2/$8 за 1M input/output
- Flash: $0.30/$1.20 за 1M input/output
- `calculate_cost(model, input_tokens, output_tokens) -> dict`

### UsageLogger (JSONL)
- Файл: `~/.local/var/deepseek-usage.jsonl`
- Поля: timestamp, model, prompt/completion/total tokens, стоимость, system_prompt_len, tags
- Автосоздание директории, silent fail при ошибках записи
- `get_usage_summary()` — сводка за всё время

### CLI флаги
- `--show-usage` — показать usage после ответа (в stderr, не мешает pipe)
- `--usage-summary` — сводка расхода из лога

### Anti-meander
- Предупреждения в stderr если system prompt > 4000 токенов или общий промпт > 80% контекста

### Файлы под git
Исходники скопированы в `personal/claude-code-setup/deepseek/`:
- `deepseek_api.py` — библиотека
- `deepseek` — CLI

## Примечания

- API-ключ один и тот же для обеих конечных точек (v1 и anthropic)
- Streaming по умолчанию в CLI, `--no-stream` для одного ответа
- `--list-models` показывает доступные модели
- JSON mode через `-j` флаг добавляет `response_format: json_object`
