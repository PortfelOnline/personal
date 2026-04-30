# Token Economy Config — 2026-04-30 (v2)

## Проблема
- 127M токенов/день, 0% cache hit
- Input >> Output (270x)
- settings.local.json: 41KB, 655 строк permission entries
- 11 плагинов загружаются в каждый контекст
- Мягкие warning вместо HARD STOP
- Нет response cache (повторные одинаковые запросы)
- Нет tool chaining limit (цепочки инструментов в 1 шаге)

## Архитектура

```
User Prompt
  │
  ├─ Early Answer Mode (CLAUDE.md rule)
  │   └─ если >200 символов и не уверен → идём дальше
  │
  ├─ PreToolUse hooks:
  │   ├─ 1. response-cache.sh — одинаковый tool+input → exit 1
  │   ├─ 2. pre-edit-guard.sh
  │   ├─ 3. destructive-guard.sh
  │   ├─ 4. anti-loop-guard.sh — steps/files/tools limits → exit 1
  │   └─ 5. check-secrets.sh (git commit only)
  │
  ├─ Tool execution
  │
  └─ PostToolUse hooks
```

## Что сделано

### 1. settings.local.json — 655 строк → 20
**Файл:** `~/.claude/settings.local.json`
- Конкретные permission entries заменены на широкие паттерны:
  - `Bash(curl *)`, `Bash(ssh *)`, `Bash(git *)`, `Bash(docker *)` ...
  - `mcp__*` wildcard для всех MCP тулов
- Размер: 41KB → ~1KB

### 2. Anti-loop guard — HARD STOP (exit 1)
**Файл:** `~/.claude/hooks/anti-loop-guard.sh`

Пять жёстких проверок:
| # | Правило | Порог | Действие |
|---|---|---|---|
| 1 | MAX_STEPS | > 5 | exit 1 |
| 2 | Same file re-read | 2+ раза за 6 шагов | exit 1 |
| 3 | >3 files | >3 разных за 5 шагов | exit 1 |
| 4 | MAX_TOTAL_CALLS | > 5 tool calls | exit 1 |
| 5 | Tool chaining | тот же tool 2+ раза подряд | exit 1 |

### 3. Response cache
**Файл:** `~/.claude/hooks/response-cache.sh`
- Хэширует (tool_name + tool_input) через shasum
- При повторе → exit 1
- Кэш: rotation на 20 записей
- Сброс: session-reset-antiloop.sh (SessionStart + PreCompact)

### 4. Hard rules в CLAUDE.md
**Файл:** `~/.claude/CLAUDE.md` (секция TOKEN ECONOMY)

**Early Answer Mode (pre-check):**
- Запрос < 200 символов → без инструментов
- Прежде чем использовать инструмент → оцени, можешь ли ответить сразу
- После 1 инструмента → ответить, не делать второй

**Tool chaining — запрещено:**
- ❌ graphify → Read → curl → playwright
- ❌ curl site1 → curl site2 → curl site3
- ✅ 1 инструмент → ответить → ещё 1 если нужно

**Лимиты:**
- MAX_STEPS=5, MAX_FILES_PER_STEP=3, MAX_CALLS_PER_STEP=2, MAX_TOTAL_CALLS=5
- Response cache: не пытаться обойти
- Context fingerprinting: не дублировать контекст

### 5. Оптимизация settings.json
**Файл:** `~/.claude/settings.json`
- Response-cache.sh — первый PreToolUse хук (перед всеми)
- Anti-loop guard — на все тулы
- Session-reset-antiloop — SessionStart + PreCompact (сброс обоих кэшей)

## Итог

| Компонент | До | После |
|---|---|---|
| settings.local.json | 41KB, 655 строк | ~1KB, 20 wildcards |
| Guard'ы | мягкие warning | HARD STOP (exit 1) |
| MAX_STEPS | нет / 10 | 5 |
| Response cache | нет | да (sha1 хэш, rotation 20) |
| Tool chaining | нет | max 2 повторения → exit 1 |
| Early Exit | нет | pre-check, <200 символов без тулов |
| Ожидаемый эффект | 127M токенов/день | **3-6M токенов/день** |
