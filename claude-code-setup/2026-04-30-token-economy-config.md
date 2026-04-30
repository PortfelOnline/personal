# Token Economy Config — 2026-04-30

## Проблема
- 127M токенов/день, 0% cache hit
- Input >> Output (270x)
- settings.local.json: 41KB, 655 строк permission entries
- 11 плагинов загружаются в каждый контекст
- Нет guard'ов от зацикливания (мягкие warning вместо STOP)

## Что сделано

### 1. settings.local.json — 655 строк → 20
**Файл:** `~/.claude/settings.local.json`
- Конкретные permission entries заменены на широкие паттерны
  - `Bash(curl *)` вместо 100+ отдельных curl команд
  - `Bash(ssh *)`, `Bash(git *)`, `Bash(docker *)` и т.д.
  - `mcp__*` wildcard для всех MCP тулов
- Размер: 41KB → ~1KB

### 2. Anti-loop guard hook — HARD STOP
**Файл:** `~/.claude/hooks/anti-loop-guard.sh`

Три жёстких правила с `exit 1` (не warning, не ask — блокировка):
- **MAX_STEPS = 5** — на 6-м шаге HARD STOP
- **Same file re-read** — если файл прочитан 2+ раза за 6 шагов → STOP
- **>3 файлов за 5 шагов** — превышение лимита → STOP

Сброс состояния: `session-reset-antiloop.sh` (SessionStart + PreCompact)

### 3. Hard rules в CLAUDE.md
**Файл:** `~/.claude/CLAUDE.md` (секция TOKEN ECONOMY)

Основные правила:
- **Early Answer Mode**: если >70% уверенности — отвечай без инструментов
- MAX_STEPS = 5, MAX_FILES_PER_STEP = 3
- Анти-Partial-Read loop: прочитал часть файла — не читай другую часть
- graphify_query: budget ≤ 500 (simple=300, code=800, default=500)
- Context Reuse: не пересылай одинаковые куски контекста
- curl/tool discipline: не делать цепочек проверок

### 4. Оптимизация settings.json
**Файл:** `~/.claude/settings.json`
- Anti-loop guard добавлен в PreToolUse (на все тулы, без matcher)
- Session-reset-antiloop добавлен в SessionStart + PreCompact

## Итог

| Компонент | До | После |
|---|---|---|
| settings.local.json | 41KB, 655 строк | ~1KB, 20 wildcards |
| Guard'ы | мягкие warning | HARD STOP (exit 1) |
| MAX_STEPS | нет / 10 | 5 |
| Early Exit | нет | >70% → без тулов |
| Ожидаемый эффект | 127M токенов/день | 3-8M токенов/день |
