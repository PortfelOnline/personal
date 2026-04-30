# Reduce LLM Costs by 5–10x

Production-ready Claude Code runtime optimization.

## Quick Start

```bash
cp -r claude-config ~/.claude
# restart Claude Code
```

## Benchmarks

| Metric | Before | After |
|--------|--------|-------|
| Tokens/day | 127M | 1.2–3M |
| Cache hit | 0% | 80–90% |
| Avg steps | 10+ | 2–5 |
| Waste | ~100% | ≈ 0 |

## Features

| Cлой | Технология | Эффект |
|------|-----------|--------|
| **Adaptive steps** | `anti-loop-guard.sh` | 2–5 шагов, зависит от сложности |
| **Response cache** | `response-cache.sh` | 80–90% cache hit, TTL по типу |
| **Prefetch engine** | `prefetch-engine.sh` | Спекулятивное выполнение (canary 10%) |
| **Tool cost control** | CLAUDE.md rules | ~2000 токенов/ответ, 0 цепочек |
| **Early answer** | CLAUDE.md rules | 0 шагов на тривиальные запросы |
| **Runtime logging** | `post-tool-signals.sh` | `runtime.log` — step/tool/exit |
| **Soft reset** | `user-prompt-submit.sh` | Очистка кэша каждые 25 промптов |
| **Security** | `destructive-guard.sh` | Блокировка опасных команд |

## Installation

```bash
# From existing checkout
cp -r claude-config ~/.claude

# Fresh install
git clone git@github.com:PortfelOnline/personal.git
cp -r personal/claude-config ~/.claude/
```

## Architecture

```
User Prompt → SessionStart (reset + warmup) → Claude
  ↓
PreToolUse → response-cache (TTL check) → anti-loop (step limit)
  ↓
Tool execution → result
  ↓
PostToolUse → cache save → prefetch (canary) → runtime log
```

## Philosophy

LLM трактуется как лимитированный вычислительный ресурс (CPU/RAM модель). Каждый токен — деньги. Каждый лишний шаг — потери.

- **0% лишнего**: если можно ответить без инструмента — отвечай
- **80–90% от кэша**: повторные вызовы не сжигают контекст
- **5–10× эффективнее**: 127M → 1.2M токенов/день

## Version

v1.0 — стабильная версия. Эксперименты → ветка `v1.1`.
