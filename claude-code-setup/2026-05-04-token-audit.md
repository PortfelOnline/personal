# Аудит token economy — 2026-05-04

## Итог: 25.6M токенов за ~4 дня (6.4M/день)

---

## 🔥 ТОП-3 утечки токенов

### 1. CLAUDE.md = 4,584 токенов системных правил (20% от каждого запроса!)

`personal/CLAUDE.md` + `~/.claude/CLAUDE.md` = **9,168 токенов** правил в system prompt.
Сжимаются до 967 tok через `ds-proxy.py` (нормализация пробелов), но даже так:
- 967 tok × 775 запросов = **749K токенов сожжено на правила**
- **Ирония**: правила token economy сами тратят больше всех токенов
- 40% секций CLAUDE.md не используются в 90% запросов (Search routing, Partial Read,
  Response Shaping, Dynamic Temperature, Answer Compression — только для LLM, не для человека)

**Фикс**: вынести редко-используемые правила в `/hooks/` скрипты.
CLAUDE.md → оставить только: модель, репозитории, DeepSeek rules (70% rule), лимиты.
Экономия: **~500 tok/запрос = 387K токенов за 4 дня**.

### 2. Растущая история разговора = 59% всех токенов (15M/25.6M)

| Категория | Запросов | % | Средний расход |
|-----------|----------|---|----------------|
| Tiny (<5K) | 122 | 16% | 1,617 tok |
| Small (5-30K) | 190 | 25% | 16,566 tok |
| **Medium (30-55K)** | **341** | **44%** | **43,983 tok** |
| Large (55K+) | 122 | 16% | 59,912 tok |

- **44% запросов тратят 30-55K токенов** — это раздутая история разговора
- Средний рост за turn: **11,763 токенов**
- После 10 turn'ов: **~113K токенов** (превышает бюджет 96K → truncation)
- Без prompt caching (DeepSeek не поддерживает) — **вся история пересылается каждый раз**

**Фикс**: агрессивнее жать tool_result через `_compress_content` + авто-truncation
после 5 turn'ов. Добавить сигнал "история растёт" в метрики.

### 3. MCP tool definitions = скрытый налог на каждый запрос

Все MCP сервера (graphify, ruflo, playwright, serena, github, plugin_github) имеют
десятки инструментов, каждый с JSON Schema. Они в каждом запросе, даже если не используются.
Примерная оценка: **~2000 токенов на tool definitions** (80+ инструментов × ~25 tok/описание).

**Фикс**: lazy-load MCP tools — отправлять только если запрос похож на их использование.

---

## 📊 Flash vs Pro: анализ использования

| Модель | Вызовов | Средний prompt | Средний completion | Всего токенов | Доля |
|--------|---------|---------------|-------------------|---------------|------|
| Flash | 6 | 14 tok | 96 tok | 670 tok | 13% |
| Pro | 8 | 13 tok | 558 tok | 4,576 tok | 87% |

**Проблема**: данные из `deepseek-usage.jsonl` неполные — только 14 записей против 775 реальных
запросов. Логирование `_log_jsonl()` срабатывает только для не-streaming запросов с `selected_model`.

**Алгоритм `_should_use_flash()`**: определяет flash/pro по длине последнего user-сообщения + keywords.
- < 100 tok → всегда flash
- < 200 tok → flash
- > 3000 tok → pro
- Иначе keyword matching

**Оптимально?** Частично. Не хватает:
1. Контекстной сложности (сколько tool_use цепочек ожидается?)
2. Истории (если уже 10 turn'ов → pro даже для короткого запроса)

---

## 🐳 Docker агент на сервере n

| Контейнер | Статус | RAM | CPU | Порт |
|-----------|--------|-----|-----|------|
| deepseek-agent | Up 3d | 37MB | 0.02% | 8766 |
| test-ds-proxy | Up 3d | ? | ? | 8099 |
| proxy_checker | Up 13d | ? | ? | 8765 |
| bot_dashboard | Up 3d | ? | ? | 4000 |

**deepseek-agent**: работает, почти не используется (0.02% CPU).
37MB RAM — очень легковесный. Можно поднять **ещё 10 таких агентов** без проблем.

**Для второго агента**: клонировать docker-compose, сменить порт, запустить.
Сервер n имеет 15.6GB RAM, текущая нагрузка минимальна.

---

## 🧩 Gap analysis: наш стек vs Claude Code vs Codex

### Что есть ✅
- [x] Tool calling (10 инструментов через DeepSeek API)
- [x] Multi-turn /chat с историей
- [x] Streaming ответов
- [x] Health check + Docker
- [x] Auto model selection (flash/pro)
- [x] Token economy (сжатие, truncation)
- [x] Хуки (PreToolUse, PostToolUse, etc.)
- [x] MCP сервера (graphify, playwright, github, ruflo)

### Чего не хватает vs Claude Code ❌

| Фича | Claude Code | Наш стек | Приоритет |
|------|-------------|----------|-----------|
| **Prompt caching** | ✅ Авто | ❌ DeepSeek не поддерживает | 🔴 Critical |
| **Thinking/CoT** | ✅ Extended thinking | ❌ DeepSeek не поддерживает | 🟡 Medium |
| **Sub-agents** | ✅ Agent tool | ❌ Нет оркестрации | 🟡 Medium |
| **Background agents** | ✅ Async dispatch | ❌ Только 1 агент | 🟡 Medium |
| **File watching** | ✅ Авто-обнаружение | ❌ | 🟢 Low |
| **IDE plugins** | ✅ VS Code, JetBrains | ❌ | 🟢 Low |
| **Auth flow** | ✅ OAuth / API key | ✅ API key (проще) | ✅ OK |
| **Permission system** | ✅ allow/deny/ask | ❌ Нет | 🟡 Medium |

### Чего не хватает vs Codex ❌

| Фича | Codex | Наш стек | Приоритет |
|------|-------|----------|-----------|
| **Sandbox** | ✅ Изолированное выполнение | ❌ Bash напрямую | 🟡 Medium |
| **Git интеграция** | ✅ PR, review, commit | ❌ Только git commands | 🟡 Medium |
| **Multi-model** | ✅ Claude + GPT + Gemini | ✅ DeepSeek flash/pro | ✅ OK |
| **Terminal sharing** | ✅ Сессии | ❌ | 🟢 Low |
| **LSP интеграция** | ✅ Go-to-def, references | ❌ (Serena MCP — частично) | 🟡 Medium |

### Приоритеты (что делать прямо сейчас)

1. **🔴 Prompt caching** — самый большой рычаг. Без него 59% токенов уходит на повторную отправку истории.
   Решение: клиентский кэш в ds-proxy (LRU cache на system prompt + tool definitions).
   Экономия: **~40% токенов**.

2. **🔴 Сжать CLAUDE.md** — выкинуть 60% редко используемых правил в hooks.
   Экономия: **~500 tok/запрос**.

3. **🟡 Второй агент на n** — можно запустить прямо сейчас (другой порт, другой docker compose).
   Риск нулевой — 15.6GB RAM, агент жрёт 37MB.

4. **🟡 Sub-agent orchestration** — dispatch параллельных агентов для сложных задач.
   Базовый PoC: 1 coordinator → N worker agents.

---

## 📈 Конкретные цифры для action items

| Action | Экономия tok/день | Сложность | Время |
|--------|-------------------|-----------|-------|
| Сжать CLAUDE.md (убрать 60%) | ~96K | 30 мин | Сегодня |
| System prompt cache в прокси | ~2.5M | 2 часа | Эта неделя |
| Tool definition lazy-load | ~500K | 4 часа | Эта неделя |
| Улучшить сжатие tool_result | ~400K | 1 час | Сегодня |
