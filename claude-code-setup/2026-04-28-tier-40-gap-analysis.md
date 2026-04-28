# Tier 40+: Gap Analysis — DeepSeek Agent vs Claude Code CLI

**Дата**: 2026-04-28
**Статус**: Анализ
**Цель**: Сравнить текущий стек DeepSeek Agent с Claude Code CLI и определить следующие шаги.

## Текущий стек (Tiers 1–39)

| Категория | Инструментов | Что умеет |
|-----------|-------------|-----------|
| FS | 6 | read, write, edit, ls, grep, glob |
| Git | 5 | status, diff, log, commit, push |
| Bash | 1 | bash |
| Web | 2 | web_search, web_fetch |
| MCP | 66 | 5 серверов (GitHub, FS, Postgres×2, Playwright) |
| Tasks | 4 | create, update, list, delete |
| Memory | 4 | set, get, search, delete |
| Notify | 1 | notify (лог + Telegram) |
| **Итого** | **~90** | Базовые инструменты + персистентность |

## Ключевые гэпы

### 1. Sub-agents (Agent tool) — самый важный

**Claude Code**: spawn-ит специализированных агентов (Explore, code-review-expert, typescript-type-expert, etc.) в изолированных контекстах.

**У нас**: монолит — агент вызывает только инструменты, не может делегировать подзадачи.

**Impact**: нет параллельной работы, нет специализации, один контекст на всё.

### 2. Plan mode

**Claude Code**: EnterPlanMode → explore codebase → design approach → user approval → ExitPlanMode → implement.

**У нас**: нет — агент сразу пишет код.

**Impact**: нет структурированного планирования перед сложными изменениями.

### 3. Auto-memory

**Claude Code**: авто-сохранение фактов о пользователе, проекте, предпочтениях, фидбеке без явного tool call.

**У нас**: только ручной memory_set/get/search/delete.

**Impact**: знания теряются между сессиями, если агент сам не догадался сохранить.

### 4. Monitor (long-running processes)

**Claude Code**: Monitor tool — tail -f логов, CI watcher, поток событий с уведомлениями.

**У нас**: нет — только синхронные tool call'ы.

**Impact**: нельзя наблюдать за деплоем, батчами, длительными задачами.

### 5. Cron / Scheduling (in-agent)

**Claude Code**: CronCreate/CronDelete/CronList — in-agent планировщик.

**У нас**: только docker-level cron на хосте (2 задачи через system cron).

**Impact**: нельзя динамически создавать расписания через API.

### 6. Hooks (structured)

**Claude Code**: pre/post hooks — pre-command (risk assessment), post-edit (learning), post-task (recording).

**У нас**: есть `./hooks/` + `hook_loader.py`, но только базовый — нет типизированных хук-событий.

**Impact**: нет автоматизации рабочих процессов.

### 7. LSP / Code Intelligence

**Claude Code**: goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, incomingCalls, outgoingCalls.

**У нас**: нет — только grep/glob для поиска по коду.

**Impact**: нет навигации по коду, типов, рефакторинга.

### 8. Skills система

**Claude Code**: `/skill` — доменные экспертные агенты с чеклистами, процесс-флоу, доменными знаниями.

**У нас**: нет.

**Impact**: каждый раз заново объяснять контекст задачи.

## План закрытия гэпов (Tiers 40–49)

| Tier | Что | Сложность | Приоритет |
|------|-----|-----------|-----------|
| **40** | **Sub-agents** — делегирование подзадач в изолированные контексты | Высокая | 🔴 Критический |
| **41** | **Plan mode** — structured plan → approval → implement | Средняя | 🔴 Критический |
| **42** | **Auto-memory** — автоматическое сохранение фактов | Низкая | 🟡 Средний |
| **43** | **Monitor** — long-running process watcher | Средняя | 🟡 Средний |
| **44** | **In-agent cron** — CronCreate/CronDelete/CronList | Низкая | 🟢 Низкий |
| **45** | **Structured hooks** — pre/post command, edit, task | Средняя | 🟡 Средний |
| **46** | **Skills system** — domain experts via config | Высокая | 🟢 Низкий |
| **47** | **LSP integration** — code intelligence | Высокая | 🟢 Низкий |
| **48** | **Async background tasks** — очередь + статус | Средняя | 🟡 Средний |
| **49** | **CI integration** — GitHub Actions gate | Низкая | 🟢 Низкий |

## Итого

**Главный гэп** — Sub-agents. Без них агент не может:
- Параллельно выполнять независимые задачи
- Использовать специализированные модели (Opus для аудита, Haiku для быстрых задач)
- Изолировать контекст между разными типами задач

**Следующий шаг**: Tier 40 — архитектура sub-agents.
