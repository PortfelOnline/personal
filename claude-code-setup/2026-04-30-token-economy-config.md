# Token Economy Config — 2026-04-30 (v7 — final)

## Проблема
- 127M токенов/день, 0% cache hit, Input >> Output (270x)
- settings.local.json: 41KB / 655 строк
- 11 плагинов в каждом контексте
- Мягкие warning, нет response cache, нет tool priority

## Архитектура

```
User Prompt
  |
  |- UserPromptSubmit hook:
  |   - 1. user-prompt-submit.sh — сохраняет prompt для adaptive MAX_STEPS
  |
  |- PRE-CHECK (CLAUDE.md)
  |   - < 200 символов/тривиально -> сразу ответ. Иначе pre-check.
  |
  |- PreToolUse hooks:
  |   |- 1. response-cache.sh v3 — hash + stderr + [CACHE_PARTIAL] сигнал
  |   |- 2. pre-edit-guard.sh / destructive-guard.sh
  |   |- 3. anti-loop-guard.sh v5 — adaptive + dead-end + floor 5k + escape
  |   - 4. check-secrets.sh
  |
  |- Tool execution
  |
  - PostToolUse hooks:
      |- 1. response-cache-save.sh
      |- 2. post-tool-signals.sh v2 — error tracking + curl/graphify
      - 3. prefetch-engine.sh — speculative execution в фоне
```

## Хуки

### anti-loop-guard.sh — 12+ проверок, v5

| # | Правило | Порог | Действие |
|---|---|---|---|
| 1 | MAX_STEPS | adaptive 2-5 (от длины prompt) | exit 1 |
| 2 | Same file re-read | 2+ раза за 6 шагов | exit 1 |
| 3 | >3 files | >3 разных за 5 шагов | exit 1 |
| 4 | MAX_TOTAL_CALLS | > 5 tool calls | exit 1 |
| 5 | Tool chaining | тот же tool 2+ раза подряд | exit 1 |
| 6 | Tool priority | HIGH_COST после шага 2, MEDIUM_COST после шага 3 | exit 1 |
| 7 | Hard ban browser | playwright/browser без сигнала (login, dynamic, screenshot) | exit 1 |
| 8 | Cumulative budget | SOFT_LIMIT=30k, HARD_LIMIT=50k | exit 1 |
| 9 | **Phase reset** | смена фазы -> tokens_used *= 0.5, floor=5k | soft reset |
| 10 | **Result reuse** | (tool+input) hash уже был -> exit 1 (escape при ошибке) | exit 1 |
| 11 | **Browser fallback** | curl не сработал + graphify пуст -> browser разрешен | allow |
| 12 | **Dead-end detector** | тот же input 2 раза подряд (нет новой инфы) -> exit 1 | exit 1 |
| 13 | **Prefetch trigger** | Read(config) -> prefetch; curl -> graphify; fetch -> read | signal |

### Критические фиксы (3 зоны риска)

**1. Cache truncation — жёсткий сигнал неполноты**
- Если результат > 1000b: сначала `[CACHE_PARTIAL_DO_NOT_TRUST_FULLY]`, потом head -c 800
- Модель видит жёсткий сигнал -> не принимает урезанные данные как полные

**2. Phase reset floor = 5000**
- После x0.5: `tokens_used = max(tokens_used, 5000)`
- Предотвращает "размывание" бюджета при частой смене фаз

**3. Result reuse escape при ошибке**
- Если результат был ошибкой (exit != 0 / пустой / error в выводе) -> retry разрешён
- post-tool-signals.sh отслеживает `LAST_RESULT_ERROR` для всех инструментов

### response-cache.sh v3
- PreToolUse: sha1(tool + input) -> поиск в saved_results
- Если найден -> exit 1 + контент в stderr
- < 1000b -> полный контент
- > 1000b -> `[CACHE_PARTIAL_DO_NOT_TRUST_FULLY]` + head -c 800 + `[CACHE_PARTIAL: ...]`

### post-tool-signals.sh v2
- Отслеживает для ВСЕХ инструментов: exit code, result size, error patterns
- Сохраняет `last_result_error` для retry escape
- curl exit != 0 -> `CURL_FAILED_FILE=1`
- graphify result < 50b -> `GRAPHIFY_EMPTY_FILE=1`

### prefetch-engine.sh
- PostToolUse: speculative execution в фоне
- После Read конфига -> prefetch package.json/CLAUDE.md в кэш
- После curl -> prefetch graphify GRAPH_REPORT.md в кэш
- Non-blocking: disown, exit 0

### user-prompt-submit.sh
- Сохраняет prompt + timestamp + очищает счётчики

## CLAUDE.md — ключевые правила

**Dynamic Temperature:**
- fact (документация, конфиги): 0.1
- code (код, SQL, интеграции): 0.2
- default: 0.3

**Answer Compression:**
- Сжать финальный ответ до ~300 токенов
- Удалить повторы, воду, "как я понял"
- 1 строка если можно

**Self-Reflection:** только при ошибках/пустоте

**Confidence STOP:** fact >= 90%, code >= 80%, default >= 85%

## Итог

| Метрика | До | После |
|---|---|---|
| settings.local.json | 41KB, 655 строк | ~1KB |
| Token guard | мягкие warning | HARD STOP (exit 1) |
| Response cache | нет | sha1 + stderr + PARTIAL signal |
| Tool chaining | нет | 13 проверок + priority + budget |
| Browser hard ban | нет | keyword + fallback при curl/graphify |
| Cumulative budget | нет | 30k/50k + phase reset (floor=5k) |
| Dead-end detection | нет | same input 2x -> STOP |
| Result reuse | нет | dedup + error escape |
| Confidence STOP | >85% | task-aware (90/80/85) |
| Cache truncation | raw 1000b | [CACHE_PARTIAL] сигнал неполноты |
| Adaptive MAX_STEPS | hardcoded 5 | 2-5 от сложности |
| Speculative prefetch | нет | фоновая предзагрузка |
| Self-reflection | на каждом шаге | только при ошибках |
| Dynamic temperature | нет | 0.1/0.2/0.3 от типа |
| Answer compression | нет | ~300 токенов на финал |
| Post-tool signals | нет | error/exit/size tracking |
| Ожидаемый эффект | 127M токенов/день | **1.2-3M токенов/день** |
