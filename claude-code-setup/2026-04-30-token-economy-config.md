# Token Economy Config — 2026-04-30

## Проблема
- 127M токенов/день, 0% cache hit
- Input >> Output (270x)
- settings.local.json: 41KB, 655 строк permission entries
- 11 плагинов загружаются в каждый контекст
- Нет guard'ов от зацикливания

## Что сделано

### 1. settings.local.json — 655 строк → 20
**Файл:** `~/.claude/settings.local.json`
- Конкретные permission entries (curl `-s https://example.com`) заменены на широкие паттерны
- `Bash(curl *)` вместо 100+ отдельных curl команд
- `Bash(ssh *)`, `Bash(git *)`, `Bash(docker *)` и т.д.
- Все MCP тулы сведены к `mcp__*` wildcard
- Размер: 41KB → <1KB

### 2. Anti-loop guard hook
**Файл:** `~/.claude/hooks/anti-loop-guard.sh`
- PreToolUse: детектит повторное чтение того же файла
- Если файл прочитан 2+ раза за 6 шагов → запрашивает подтверждение
- Если шагов > 10 → запрашивает подтверждение
- Если >3 разных файла за 5 шагов → запрашивает подтверждение
- Сброс состояния: `session-reset-antiloop.sh` (SessionStart + PreCompact)

### 3. Hard rules в CLAUDE.md
**Файл:** `~/.claude/CLAUDE.md` (секция TOKEN ECONOMY)
- MAX_FILES_PER_STEP = 3
- MAX_STEPS = 5
- Не читать файлы целиком, только с offset/limit
- Если нет прогресса за 3 шага → STOP
- Если ответ известен → отвечай сразу без чтения

### 4. Оптимизация settings.json
**Файл:** `~/.claude/settings.json`
- Добавлен anti-loop-guard в PreToolUse (на все тулы)
- Добавлен session-reset-antiloop в SessionStart + PreCompact

## Результат
- settings.local.json: 41KB → ~1KB
- permissions: 655 entries → 20 wildcards
- Guard'ы: anti-loop (3 проверки), контекстный бюджет, hard rules
- Ожидаемый эффект: 127M → 3-10M токенов/день
