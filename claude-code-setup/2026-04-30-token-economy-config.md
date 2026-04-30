# Token Economy Config — 2026-04-30 (v8 — prefetch quality control)

## Проблема
- 127M токенов/день, 0% cache hit, Input >> Output (270x)
- settings.local.json: 41KB / 655 строк
- 11 плагинов в каждом контексте
- Мягкие warning, нет response cache, нет tool priority

## Архитектура

```
User Prompt
  |
  |- SessionStart hooks:
  |   |- session-reset-antiloop.sh — clean state
  |   |- warm-start-cache.sh — prefetch common files before first use
  |   - session-start-context.sh — context loading
  |
  |- UserPromptSubmit hook:
  |   - user-prompt-submit.sh — save prompt for adaptive steps + reset counters
  |
  |- PRE-CHECK (CLAUDE.md)
  |   - < 200 символов/тривиально -> сразу ответ
  |
  |- PreToolUse hooks:
  |   |- 1. response-cache.sh v3 — hash + cache tagging (prefetch vs real)
  |   |- 2. pre-edit-guard.sh / destructive-guard.sh
  |   |- 3. anti-loop-guard.sh v6 — adaptive + dead-end + floor + escape + cooldown
  |   - 4. check-secrets.sh
  |
  |- Tool execution
  |
  - PostToolUse hooks:
      |- 1. response-cache-save.sh — save real result
      |- 2. post-tool-signals.sh v2 — error tracking + browser signals
      - 3. prefetch-engine.sh v2 — speculative execution (tagged + budget + TTL)
```

## Хуки

### anti-loop-guard.sh — 14 проверок, v6

| # | Правило | Порог | Действие |
|---|---|---|---|
| 1 | MAX_STEPS | adaptive 2-5 | exit 1 |
| 2 | Same file re-read | 2+ раза за 6 шагов | exit 1 |
| 3 | >3 files | >3 разных за 5 шагов | exit 1 |
| 4 | MAX_TOTAL_CALLS | > 5 tool calls | exit 1 |
| 5 | Tool chaining | тот же tool 2+ раза подряд | exit 1 |
| 6 | Tool priority | HIGH_COST после шага 2, MEDIUM_COST после шага 3 | exit 1 |
| 7 | Hard ban browser | без сигнала (login, auth, dynamic, screenshot) | exit 1 |
| 8 | Cumulative budget | SOFT=30k, HARD=50k | exit 1 |
| 9 | Phase reset | x0.5, floor=5k | reset |
| 10 | Result reuse | (tool+input) дубликат (escape при ошибке) | exit 1 |
| 11 | Browser fallback | curl_failed + graphify_empty | allow |
| 12 | Dead-end detector | тот же input 2x подряд (нет новой инфы) | exit 1 |
| 13 | Reflection cooldown | ошибка < 2 шагов назад -> STOP (micro-loop) | exit 1 |
| 14 | Prefetch trigger | Read(config) -> prefetch; fetch -> read; curl -> graphify | signal |

### response-cache.sh v3 — cache tagging
- **Cache tagging:** prefetch vs real. Prefetched entries have `.tag` file.
- **First real use:** prefetch tag removed -> entry becomes regular cache.
- **Truncation:** < 1000b = full; > 1000b = `[CACHE_PARTIAL_DO_NOT_TRUST_FULLY]` + head -c 800.
- Prefetch data is "warm cache" — usable but marked provisional.

### prefetch-engine.sh v2 — quality control
- **Cache tagging:** writes `.tag` files for prefetched entries.
- **TTL:** all prefetch wrapped in `timeout 2s` — killed if stuck.
- **Shadow budget:** max 10k prefetch tokens, disabled if exceeded.
- **Scoring:** probability threshold > 0.5. Config files=0.6, docs=0.5, related=0.3-0.4.
- **Non-blocking:** `& disown`, always exit 0.

### post-tool-signals.sh v2 — full error tracking
- Tracks error status for ALL tools (exit code + result size + error patterns).
- `LAST_RESULT_ERROR` used by result reuse escape and reflection cooldown.

### warm-start-cache.sh (новое)
- SessionStart: prefetches CLAUDE.md, package.json, settings.json, graphify report.
- Write-once: checks if already cached, skips if so.
- Uses same cache hash as response-cache.sh -> seamless integration.
- All warm entries tagged "prefetch" -> converted to "real" on first use.

## CLAUDE.md — ключевые правила

**Reflection cooldown:** < 2 steps since last reflection -> skip.
**Dynamic temperature:** fact=0.1, code=0.2, default=0.3.
**Confidence STOP:** fact >= 90%, code >= 80%, default >= 85%.
**Answer compression:** compress final output to ~300 tokens.
**Self-reflection:** only on error/empty. 1 fix = enough.

## Итог

| Метрика | До | После v8 |
|---|---|---|
| Token guard | мягкие warning | 14 проверок, HARD STOP |
| Response cache | нет | tagging (prefetch vs real) |
| Cache noise | prefetch без контроля | tagged + shadow budget + scoring |
| Prefetch budget | не было | 10k лимит, автоотключение |
| Prefetch TTL | disown без контроля | timeout 2s + kill |
| Warm start | нет | prefetch common files на старте |
| Dead-end | нет | same input 2x -> STOP |
| Reflection loop | 1 попытка | cooldown < 2 шагов -> STOP |
| Prefetch scoring | нет | prob > 0.5 |
| Ожидаемый эффект | 127M/день | **1.2-3M/день**, cache 80-90% |
