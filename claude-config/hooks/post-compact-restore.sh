#!/bin/bash
# post-compact-restore.sh — PostCompact hook (#37)
# Восстанавливает состояние после сжатия контекста.
# Non-blocking: всегда exit 0.

set -o pipefail

STDIN=$(cat)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)
CHECKPOINT_DIR="$HOME/.claude/checkpoints"
CHECKPOINT_FILE="$CHECKPOINT_DIR/${SESSION_ID}.json"

if [ -f "$CHECKPOINT_FILE" ]; then
  CT=$(cat "$CHECKPOINT_FILE" | jq -r '.compacted_at // "unknown"' 2>/dev/null)
  echo "{\"systemMessage\": \"Контекст восстановлен после сжатия. Чекпоинт: $CT. Проверьте текущий таск и продолжайте.\"}"
  # Не удаляем чекпоинт — может пригодиться для повторного сжатия
else
  echo "{\"systemMessage\": \"Контекст сжат. Чекпоинт не найден — продолжайте с последнего сохранённого состояния.\"}"
fi

exit 0
