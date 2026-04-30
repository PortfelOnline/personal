#!/bin/bash
# post-tool-failure.sh — PostToolUseFailure hook (#36)
# Логирует ошибки инструментов для feedback loop.
# Non-blocking: всегда exit 0.

set -o pipefail

STDIN=$(cat)
TOOL=$(echo "$STDIN" | jq -r '.tool_name // "unknown"' 2>/dev/null)
FILE=$(echo "$STDIN" | jq -r '.tool_input.file_path // .tool_input.command // ""' 2>/dev/null)
ERROR=$(echo "$STDIN" | jq -r '.tool_response.error // .tool_response // "unknown"' 2>/dev/null | head -c 300)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/tool-failures.log"

# Ротация: макс 1000 строк
[ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 1000 ] && tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

# Запись в лог
cat >> "$LOG_FILE" <<< "[$TS] [$SESSION_ID] $TOOL | $FILE | ${ERROR:0:200}"

# Системное сообщение
SEVERE_TOOLS="Bash|Write|Edit"
if echo "$TOOL" | grep -qE "$SEVERE_TOOLS"; then
  echo "{\"systemMessage\": \"Инструмент $TOOL упал: ${ERROR:0:100}\"}"
fi

exit 0
