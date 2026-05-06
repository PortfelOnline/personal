#!/bin/bash
# === Switch to DeepSeek API (через ds-proxy) ===
# Usage: source ~/personal/claude-code-setup/switch-to-deepseek.sh

echo "🔄 Switching to DeepSeek API (via ds-proxy)..."

# 1. Ставим прокси
export ANTHROPIC_BASE_URL="http://127.0.0.1:8099"

# 2. Грузим DeepSeek API ключ
source "$HOME/.deepseek.env" 2>/dev/null || true
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  echo "   ✅ DEEPSEEK_API_KEY loaded"
else
  echo "   ⚠️  DEEPSEEK_API_KEY not set (check ~/.deepseek.env)"
fi

# 3. Меняем модель на DeepSeek flash (дешёвый, быстрый)
claude config set model deepseek-v4-flash 2>/dev/null || \
  echo "   ⚠️  Model switch failed"

# 4. Запускаем прокси если не запущен
PROXY_SCRIPT="$HOME/personal/claude-code-setup/ds-proxy.py"
if ! lsof -nP -iTCP:8099 -sTCP:LISTEN >/dev/null 2>&1; then
  if [ -f "$PROXY_SCRIPT" ]; then
    nohup python3 "$PROXY_SCRIPT" &>/tmp/ds-proxy.log &
    sleep 1
    echo "   ✅ DeepSeek proxy started (port 8099)"
  fi
fi

# 5. Алиасы для прямых вызовов
alias claude-ds='ANTHROPIC_BASE_URL="http://127.0.0.1:8099" command claude'
alias cl-ds='ANTHROPIC_BASE_URL="http://127.0.0.1:8099" command claude'

echo ""
echo "�� NOW USING: DeepSeek API (via ds-proxy :8099)"
echo "   Models: deepseek-v4-flash (default) / deepseek-v4-pro"
echo "   To switch back: source ~/personal/claude-code-setup/switch-to-claude-pro.sh"
echo ""
echo "   Cost: flash ~\$0.15/M input, pro ~\$2.00/M input"
echo "   Models:"
echo "     claude config set model deepseek-v4-flash   # 3€/мес (кэш 90%)"
echo "     claude config set model deepseek-v4-pro     # 15-20€/мес"
