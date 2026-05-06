#!/bin/bash
# === Switch to Claude Code Pro (Anthropic API напрямую) ===
# Usage: source ~/personal/claude-code-setup/switch-to-claude-pro.sh
# Или: . ~/personal/claude-code-setup/switch-to-claude-pro.sh

echo "🔄 Switching to Claude Code Pro (Anthropic API)..."

# 1. Убираем прокси
unset ANTHROPIC_BASE_URL

# 2. Ставим настоящий Anthropic API ключ
# Загружаем из системного keychain или env
if [ -f "$HOME/.anthropic.env" ]; then
  source "$HOME/.anthropic.env"
  echo "   ✅ ANTHROPIC_API_KEY loaded from ~/.anthropic.env"
else
  echo "   ⚠️  ~/.anthropic.env not found — will use claude CLI OAuth"
fi

# 3. Меняем модель на Claude Sonnet (оптимальный баланс)
# Используем CLI напрямую для смены модели
claude config set model claude-sonnet-4-20250514 2>/dev/null || \
  echo "   ⚠️  Model switch via CLI failed — change manually: claude config set model claude-sonnet-4-20250514"

# 4. Останавливаем DeepSeek прокси если запущен
DS_PROXY_PID=$(lsof -ti:8099 2>/dev/null)
if [ -n "$DS_PROXY_PID" ]; then
  kill "$DS_PROXY_PID" 2>/dev/null
  echo "   ✅ DeepSeek proxy (port 8099) stopped"
fi

# 5. Создаём алиас для запуска claude БЕЗ wrapper'а
alias claude-pro='ANTHROPIC_BASE_URL="" command claude'
alias cl-pro='ANTHROPIC_BASE_URL="" command claude'

echo ""
echo "🎯 NOW USING: Claude Code Pro (Sonnet)"
echo "   Models: Haiku / Sonnet / Opus — all Anthropic direct"
echo "   To switch back: source ~/personal/claude-code-setup/switch-to-deepseek.sh"
echo "   To use directly: claude-pro (без wrapper'а)"
echo ""
echo "   Models available:"
echo "     claude config set model claude-haiku-4-5-20251001   # дешёвый, быстрый"
echo "     claude config set model claude-sonnet-4-20250514    # основной (оптим.)"
echo "     claude config set model claude-opus-4-7             # сложные задачи"
