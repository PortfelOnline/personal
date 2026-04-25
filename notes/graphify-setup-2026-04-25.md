# Graphify Setup — 2026-04-25

## Что сделано

Подключили [safishamsi/graphify](https://github.com/safishamsi/graphify) ко всем проектам для снижения потребления токенов AI.

### Зачем graphify
- Граф хранится в `graphify-out/graph.json` и живёт между сессиями
- `graphify query "..."` отвечает через BFS-обход графа вместо чтения всех файлов
- Экономия: ~50 токенов на запрос vs 10K–65K при чтении файлов напрямую
- AST-extraction детерминированный (без LLM, бесплатный)

### Созданные графы

| Проект | Путь | Узлы | Рёбра |
|--------|------|------|-------|
| personal | `~/personal/graphify-out/` | 67 | 81 |
| aitrading | `~/dev/aitrading/graphify-out/` | 42 | 88 |
| github-connect-hub | `~/kadmap/_repos/github-connect-hub/graphify-out/` | 96 | 37 |
| aiwaiter | `~/dev/aiwaiter/graphify-out/` | 248 | 263 |
| localai | `~/localai/localai/graphify-out/` | 103 | 150 |
| n8n_1 | `~/n8n_1/n8n_1/graphify-out/` | 715 | 1670 |
| kadmap/scripts | `~/kadmap/scripts/graphify-out/` | 67 | 45 |
| strategy-dashboard/server | `~/strategy-dashboard/server/graphify-out/` | 385 | 670 |
| strategy-dashboard/scripts | `~/strategy-dashboard/scripts/graphify-out/` | 215 | 149 |
| strategy-dashboard/client | `~/strategy-dashboard/client/graphify-out/` | 354 | 293 |
| **audioceh** (custom) | `~/audioceh/graphify-out/` | **1477** | **2450** |

audioceh: графифицированы только кастомные контроллеры из 17K+ файлов OpenCart:
- `admin/controller/editors/` (13 файлов)
- `admin/controller/agoo/` (10 файлов)
- `admin/controller/catalog/` (22 файла)
- `admin/controller/extension/module/` (107 файлов)

### Автоматизация

**Еженедельный update** — каждый понедельник 09:00, через `com.local.refs.update` (launchd):
- `~/.claude/scripts/update-refs.sh` вызывает `update-graphify.sh`
- `update-graphify.sh` запускает `graphify . --update` на всех 10 проектах

**Авто-graphify для новых проектов** — в `~/.zshrc`:
```bash
gclone() { git clone "$@"; ...; (cd "$dir" && graphify . --no-viz 2>/dev/null || true) & }
gfy() { graphify "${1:-.}"; }
```

**Workflow template** — `~/.claude/workflow-template.json`:
Паттерн planner/coder/validator/fixer — 3-4 LLM вызова вместо 5-7.
- planner: 300 max_tokens
- coder: 1200 max_tokens
- validator: 300 max_tokens (YES/NO + одна фраза)
- fixer: 800 max_tokens (только если validator вернул YES)

### Использование

```bash
# Запрос к графу (вместо чтения файлов)
cd ~/strategy-dashboard && graphify query "как работает rewriteArticle"

# Обновить граф после изменений
cd ~/audioceh && graphify . --update --no-viz

# Клонировать с автоматическим графом
gclone https://github.com/PortfelOnline/yoga
```

### Python interpreter
`/usr/local/bin/python3` — основной интерпретер graphify на этой машине.
Хранится в `graphify-out/.graphify_python` в каждом проекте.
