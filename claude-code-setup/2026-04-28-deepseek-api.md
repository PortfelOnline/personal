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
export DEEPSEEK_API_KEY="sk-a25ff0053b784671b4ca6e283a8f66ab"
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

## Примечания

- API-ключ один и тот же для обеих конечных точек (v1 и anthropic)
- Streaming по умолчанию в CLI, `--no-stream` для одного ответа
- `--list-models` показывает доступные модели
- JSON mode через `-j` флаг добавляет `response_format: json_object`
