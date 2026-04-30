#!/bin/bash
# notification.sh — Notification hook (#50)
# Обрабатывает системные уведомления: логирует, форвардит критические.
# Notification event срабатывает когда Claude Code отправляет уведомление.

set -o pipefail

STDIN=$(cat)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)
NOTIF_TYPE=$(echo "$STDIN" | jq -r '.notification_type // "unknown"' 2>/dev/null)
NOTIF_MSG=$(echo "$STDIN" | jq -r '.message // ""' 2>/dev/null)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/notifications.log"

# Ротация: > 1000 строк → оставить последние 500
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 1000 ]; then
  tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

# Логируем
echo "[$TS] [$SESSION_ID] [$NOTIF_TYPE] ${NOTIF_MSG:0:300}" >> "$LOG_FILE"

# Для критических уведомлений — systemMessage
CRITICAL_TYPES="error|failure|timeout|crash"
if echo "$NOTIF_TYPE" | grep -qiE "$CRITICAL_TYPES"; then
  echo "{\"systemMessage\": \"Критическое уведомление: [$NOTIF_TYPE] ${NOTIF_MSG:0:100}\"}"
fi

exit 0
