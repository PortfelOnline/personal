#!/bin/bash
# pre-compact-checkpoint.sh — PreCompact hook (#37)
# Сохраняет чекпоинт состояния перед сжатием контекста.
# Non-blocking: всегда exit 0.

set -o pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
CHECKPOINT_DIR="$HOME/.claude/checkpoints"
mkdir -p "$CHECKPOINT_DIR"

# Читаем stdin
STDIN=$(cat)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)
COMPACT_TYPE=$(echo "$STDIN" | jq -r '.compact_type // "unknown"' 2>/dev/null)

CHECKPOINT_FILE="$CHECKPOINT_DIR/${SESSION_ID}.json"

# Сохраняем компактный чекпоинт
cat > "$CHECKPOINT_FILE" <<EOF
{
  "compacted_at": "$TS",
  "session_id": "$SESSION_ID",
  "compact_type": "$COMPACT_TYPE",
  "survival_kit": {
    "note": "Полный чекпоинт в MEMORY.md. Этот файл — сигнал для PostCompact восстановления."
  }
}
EOF

echo "{\"systemMessage\": \"Контекст сжат. Чекпоинт сохранён: $CHECKPOINT_FILE\"}"
exit 0
