#!/bin/bash
# === Smart Model Switch ===
# Автоматически выби��ает оптимальную модель в зависимости от задачи
# Usage: source ~/personal/claude-code-setup/smart-model-switch.sh <task-type>
#   task-type: simple | medium | complex | audit | research | cost-save
#
# Модели и их стоимость (input / output):
#   deepseek-v4-flash     — $0.15/M / $0.60/M  (⚠️ раундтрипы)
#   deepseek-v4-pro       — $2.00/M / $8.00/M  (⚠️ раундтрипы)
#   claude-haiku          — $0.80/M / $4.00/M  (кэш 90%, быстрый)
#   claude-sonnet         — $3.00/M / $15.00/M (кэш 90%, баланс)
#   claude-opus           — $15.00/M / $75.00/M(кэш 90%, сложные)

MODE="${1:-cost-save}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$MODE" in
  # ==== СУПЕР ДЕШЁВЫЕ ====
  simple|cost-save)
    echo "=== MODE: SIMPLE/COST-SAVE → deepseek-v4-flash ==="
    source "$SCRIPT_DIR/switch-to-deepseek.sh"
    claude config set model deepseek-v4-flash 2>/dev/null
    echo "💡 Best for: typos, simple edits, git operations, ls/cat"
    echo "   Cost: ~3€/month (90% cache hits on context)"
    ;;

  # ==== СРЕДНИЕ ЗАДАЧИ ====
  medium|balanced)
    echo "=== MODE: MEDIUM/BALANCED → claude-sonnet ==="
    source "$SCRIPT_DIR/switch-to-claude-pro.sh"
    claude config set model claude-sonnet-4-20250514 2>/dev/null
    echo "💡 Best for: feature development, bug fixes, code review"
    echo "   Cost: Sonnet ~€0.50-2/session (с кэшем)"
    ;;

  # ==== СЛОЖНЫЕ ЗАДАЧИ ====
  complex|deep-research)
    echo "=== MODE: COMPLEX → claude-opus (with sonnet priming) ==="
    source "$SCRIPT_DIR/switch-to-claude-pro.sh"
    claude config set model claude-opus-4-7 2>/dev/null
    echo "💡 Best for: architecture decisions, complex refactoring"
    echo "   Cost: Opus ~€3-8/session — используй точечно!"
    ;;

  # ==== БЫСТРЫЕ ЧЕРНОВИКИ ====
  draft|quick)
    echo "=== MODE: DRAFT/QUICK → claude-haiku ==="
    source "$SCRIPT_DIR/switch-to-claude-pro.sh"
    claude config set model claude-haiku-4-5-20251001 2>/dev/null
    echo "💡 Best for: brainstorming, drafts, summaries, quick questions"
    echo "   Cost: Haiku ~€0.10-0.30/session"
    ;;

  # ==== PRO для сложных через DeepSeek ====
  pro|deepseek-pro)
    echo "=== MODE: PRO → deepseek-v4-pro ==="
    source "$SCRIPT_DIR/switch-to-deepseek.sh"
    claude config set model deepseek-v4-pro 2>/dev/null
    echo "💡 DeepSeek Pro — когда нужен DeepSeek, но качество лучше flash"
    echo "   Cost: ~15-20€/мес"
    ;;

  # ==== АУДИТ ТОКЕНОВ ====
  audit)
    echo "=== MODE: AUDIT ==="
    echo "Текущие настройки:"
    echo "  model: $(claude config get model 2>/dev/null || echo 'N/A')"
    echo "  ANTHROPIC_BASE_URL: ${ANTHROPIC_BASE_URL:-"(not set)"}"
    echo "  DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:+'set ✓'}"
    echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+'set ✓'}"
    echo ""
    echo "Статистика токенов:"
    python3 -c "
import json
try:
    with open('$HOME/.claude/stats-cache.json') as f:
        d = json.load(f)
    mu = d.get('modelUsage', {})
    for m, v in sorted(mu.items()):
        inp = v.get('inputTokens', 0)
        out = v.get('outputTokens', 0)
        cache_r = v.get('cacheReadInputTokens', 0)
        cache_c = v.get('cacheCreationInputTokens', 0)
        total_cost = v.get('costUSD', 0)
        total_m = (inp + cache_r + cache_c) / 1_000_000
        print(f'  {m}:')
        print(f'    input: {inp/1e6:.1f}M | output: {out/1e6:.1f}M')
        print(f'    cache_read: {cache_r/1e6:.1f}M | cache_create: {cache_c/1e6:.1f}M')
        print(f'    total_volume: {total_m:.1f}M tokens | cost: \${total_cost:.2f}')
except Exception as e:
        print(f'  Error: {e}')
    "
    echo ""
    echo "💡 Recommendation:"
    echo "   Если задачи простые — используй DeepSeek Flash |Haiku"
    echo "   Если нужен quality — используй Claude Sonnet (лучший balance)"
    echo "   Opus только для сложных архитектурных решений"
    ;;

  *)
    echo "Usage: source smart-model-switch.sh <mode>"
    echo ""
    echo "Modes:"
    echo "  simple|cost-save  → deepseek-v4-flash (3€/мес)"
    echo "  medium|balanced   → claude-sonnet (оптимальный)"
    echo "  complex           → claude-opus (сложные задачи)"
    echo "  draft|quick       → claude-haiku (быстрые)"
    echo "  pro|deepseek-pro  → deepseek-v4-pro"
    echo "  audit             → показать статистику токенов"
    ;;
esac
