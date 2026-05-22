# Serena MCP: переход на локальный клон

**Дата:** 2026-05-22  
**Проблема:** `serena` MCP падал с таймаутом 30s при `/mcp reconnect`.  
**Причина:** `uvx --from git+https://github.com/oraios/serena` при холодном кэше клонирует репо + устанавливает 80 зависимостей → не укладывается в 30s лимит Claude Code.

## Решение

Переключил MCP-конфиг в `~/.claude.json` (scope: project `/Users/evgenijgrudev`) на локальный клон:

```json
"command": "sh",
"args": ["-c", "cd ~/serena && uv run --frozen serena start-mcp-server --enable-web-dashboard false"]
```

- Warm startup: ~8s (vs 6-46s у uvx)
- `--frozen` использует `uv.lock` — не пересоздаёт env при каждом запуске
- `~/serena` обновляется автоматически через refs extra.list (пн 09:00)

## Обновление клона

Локальный клон был на `1.3.1.dev0-7c7d5eef` (18 мая), upstream на `1.5.2.dev0`.  
Обновил: `git merge --ff-only origin/main && uv sync --frozen`.

Теперь совпадает с тем, что тянул uvx git+main.
