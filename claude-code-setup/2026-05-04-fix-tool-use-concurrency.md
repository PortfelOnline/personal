# Фикс: API Error 400 tool use concurrency

**Дата**: 2026-05-04
**Проблема**: В Claude Code CLI (2.1.126) c `deepseek-v4-flash` через `ds-proxy.py`
периодически выпадает `API Error: 400 due to tool use concurrency issues`.
`/rewind` восстанавливает сессию, но теряется прогресс.

## Причина

DeepSeek API возвращает слишком много параллельных `tool_use` блоков
в одном ответе (10+). Claude Code пытается выполнить их все параллельно,
что превышает лимит конкурентности Anthropic API → HTTP 400.

## Фикс

В `ds-proxy.py` добавлено ограничение: максимум **3** параллельных
`tool_use` блока за один ответ.

### Non-streaming (`_limit_tool_use_blocks`)
```python
MAX_PARALLEL_TOOLS = 3

def _limit_tool_use_blocks(blocks: list) -> list:
    tool_count = 0
    limited = []
    for block in blocks:
        if block.get("type") == "tool_use":
            tool_count += 1
            if tool_count > MAX_PARALLEL_TOOLS:
                continue
        limited.append(block)
    return limited
```

Применяется в JSON-ответе перед отправкой клиенту.

### Streaming (SSE)
В streaming-режиме отслеживаются `content_block_start` события с
`type=tool_use`. После превышения лимита `content_block_delta` и
`content_block_stop` для избыточных блоков отбрасываются.

## Почему 3

- Claude Code нормально работает с 1-5 параллельными tool calls
- 3 — консервативный лимит, исключающий ошибку
- Если понадобится увеличить: поменять `MAX_PARALLEL_TOOLS = 5` в `ds-proxy.py`

## Проверка

```bash
# Рестарт прокси
kill $(lsof -ti:8099)
python3 ~/personal/claude-code-setup/ds-proxy.py --port 8099 &
```

После фикса ошибка не воспроизводится при нормальной работе.
