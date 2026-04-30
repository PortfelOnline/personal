# Token Economy Config — 2026-04-30 (v6 — speculative + adaptive)

## Проблема
- 127M токенов/день, 0% cache hit, Input >> Output (270x)
- settings.local.json: 41KB / 655 строк
- 11 плагинов в каждом контексте
- Мягкие warning, нет response cache, нет tool priority

## Архитектура

```
User Prompt
  │
  ├─ UserPromptSubmit hook:
  │   └─ 1. user-prompt-submit.sh — сохраняет prompt для adaptive MAX_STEPS
  │
  ├─ PRE-CHECK (CLAUDE.md)
  │   └─ < 200 символов/тривиально → сразу ответ. Иначе pre-check.
  │
  ├─ PreToolUse hooks:
  │   ├─ 1. response-cache.sh — hash -> exit 1 + контент в stderr
  │   ├─ 2. pre-edit-guard.sh / destructive-guard.sh
  │   ├─ 3. anti-loop-guard.sh v4 — adaptive MAX_STEPS + prefetch trigger
  │   └─ 4. check-secrets.sh
  │
  ├─ Tool execution
  │
  └─ PostToolUse hooks:
      ├─ 1. response-cache-save.sh — сохраняет результат в кэш
      ├─ 2. post-tool-signals.sh — curl exit / graphify size tracking
      └─ 3. prefetch-engine.sh — speculative execution в фоне
```

## Хуки

### anti-loop-guard.sh — 11+ проверок, adaptive MAX_STEPS, exit 1

| # | Правило | Порог | Действие |
|---|---|---|---|
| 1 | MAX_STEPS | adaptive 2-5 (от длины prompt) | exit 1 |
| 2 | Same file re-read | 2+ раза за 6 шагов | exit 1 |
| 3 | >3 files | >3 разных за 5 шагов | exit 1 |
| 4 | MAX_TOTAL_CALLS | > 5 tool calls | exit 1 |
| 5 | Tool chaining | тот же tool 2+ раза подряд | exit 1 |
| 6 | Tool priority | HIGH_COST после шага 2, MEDIUM_COST после шага 3 | exit 1 |
| 7 | Hard ban browser | playwright/browser без сигнала (login, dynamic, screenshot) | exit 1 |
| 8 | Cumulative budget | SOFT_LIMIT=30k, HARD_LIMIT=50k, LOW_COST only после 30k | exit 1 |
| 9 | **Phase reset budget** | смена фазы (read->write->fetch->browser) -> tokens_used *= 0.5 | soft reset |
| 10 | **Result reuse** | (tool+input) hash уже был в этом шаге -> exit 1 | exit 1 |
| 11 | **Browser fallback** | curl не сработал + graphify пуст -> browser разрешен | allow |
| 12 | **Prefetch trigger** | Read(config) -> prefetch:websearch; curl -> prefetch:graphify | signal |

**Adaptive MAX_STEPS:**
| Длина запроса | Тип | MAX_STEPS |
|---|---|---|
| < 50 символов | короткий | 2 |
| < 200 символов | средний | 3 |
| >= 200, баг/ошибка | debug | 4 |
| >= 200, архитектура/рефакторинг | arch | 5 |
| стандартный | normal | 3 |

**Tool priority:**
- LOW_COST (всегда): Read, Write, Edit, Bash(ls|git|find|cat|echo)
- MEDIUM_COST (шаг < 4): Bash(curl), Bash(ssh), WebFetch, graphify
- HIGH_COST (шаг < 2): playwright, browser, WebSearch, docker

### response-cache.sh + response-cache-save.sh
- PreToolUse: sha1(tool + input) -> поиск в saved_results
- Если найден -> exit 1 + контент в stderr (модель видит контент без вызова тула)
- Безопасная обрезка: если < 1000b -> полный контент; иначе head -c 800 + [TRUNCATED]
- PostToolUse: сохраняет результат в `$RESULTS_DIR/$HASH.txt`
- Повтор identical вызова -> контент из stderr, тул не вызывается

### post-tool-signals.sh
- PostToolUse: отслеживает curl exit code и graphify result size
- curl exit != 0 -> `CURL_FAILED_FILE=1`
- graphify result < 50b -> `GRAPHIFY_EMPTY_FILE=1`
- Используется anti-loop-guard.sh для browser fallback

### prefetch-engine.sh (новое)
- PostToolUse: speculative execution в фоне
- После Read конфига -> prefetch package.json/CLAUDE.md/settings.json в кэш
- После curl -> prefetch graphify GRAPH_REPORT.md в кэш
- Non-blocking: disown, всегда exit 0
- Результаты подхватываются response-cache.sh как cache hit

### user-prompt-submit.sh (обновлён)
- Сохраняет prompt в /tmp/claude_antiloop/current_prompt
- Используется anti-loop-guard.sh для adaptive MAX_STEPS
- Очищает счётчики шагов для новой сессии

### session-reset-antiloop.sh
- Сброс `/tmp/claude_antiloop/` + `/tmp/claude_cache/`

## CLAUDE.md — ключевые правила

**Early Answer Mode:**
- < 200 символов -> 0 инструментов
- Pre-check перед каждым инструментом
- После 1 инструмента -> ответить, не делать второй

**Self-Reflection — только при ошибках:**
- Разрешена только если инструмент вернул ошибку / пустой результат
- Запрещена на каждом шаге
- 1 рефлексия = 1 fix. Не углубляться.
- Если fix не сработал -> STOP

**Cost Model:**
| Действие | ~токенов |
|---|---|
| Read (100 строк) | 500-1000 |
| curl / WebFetch | 1000-3000 |
| WebSearch | 2000-5000 |
| graphify | 500-1500 |
| playwright/browser | 3000-10000 |

**Context Threshold:** <50 токенов -> 1 retry allowed, второй раз -> STOP

**Confidence STOP:**
- **fact** (вопросы, документация, конфиги): порог >= 90% -> STOP
- **code** (код, SQL, скрипты, интеграции): порог >= 80% -> STOP
- **default** (всё остальное): порог >= 85% -> STOP

## Итог

| Компонент | До | После |
|---|---|---|
| settings.local.json | 41KB, 655 строк | ~1KB, 20 wildcards |
| Guard'ы | мягкие warning | HARD STOP (exit 1) |
| Response cache | нет | sha1 + контент в stderr |
| Tool chaining | нет | 12 проверок + priority + budget |
| Browser hard ban | нет | playwright без сигнала -> exit 1 (+ fallback) |
| Cumulative budget | нет | SOFT=30k, HARD=50k + phase reset |
| Result reuse | нет | dedup внутри шага |
| Confidence STOP | >85% | task-type aware (fact=90%, code=80%, default=85%) |
| Cache truncation | head -c 1000 без сигнала | <1000b=full, >1000b=head -c 800 + TRUNCATED |
| Browser fallback | нет | curl_failed + graphify_empty -> allow browser |
| Adaptive MAX_STEPS | hardcoded 5 | 2-5 от сложности запроса |
| Speculative prefetch | нет | фоновая предзагрузка вероятных след. данных |
| Self-reflection | на каждом шаге | только при ошибках |
| Post-tool signals | нет | curl exit, graphify size |
| Ожидаемый эффект | 127M токенов/день | **1.5-3.5M токенов/день** |
