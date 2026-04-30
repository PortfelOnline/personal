#!/bin/bash
# session-report.sh — Stop hook (#38)
# Генерирует структурированный сессионный отчёт при завершении сессии.
# Сохраняет JSON в ~/.claude/reports/ и выводит systemMessage со сводкой.

set -o pipefail

STDIN=$(cat)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TS_LOCAL=$(date -u -v+5H -v+30M +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

REPORT_DIR="$HOME/.claude/reports"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/session-${SESSION_ID}.json"

# Попытка собрать статистику из логов
TOOL_FAILURES=$(grep -c "\[$SESSION_ID\]" "$HOME/.claude/logs/tool-failures.log" 2>/dev/null || echo "0")
CHECKPOINT_FILE="$HOME/.claude/checkpoints/${SESSION_ID}.json"
COMPACT_COUNT=0
[ -f "$CHECKPOINT_FILE" ] && COMPACT_COUNT=$(jq '.compactions // 0' "$CHECKPOINT_FILE" 2>/dev/null || echo "0")

# Формируем отчёт
cat > "$REPORT_FILE" <<EOF
{
  "session_id": "$SESSION_ID",
  "ended_at": "$TS",
  "ended_at_local": "$TS_LOCAL",
  "stats": {
    "tool_failures": $TOOL_FAILURES,
    "compactions": $COMPACT_COUNT
  },
  "artifacts": {
    "checkpoint": "$([ -f "$CHECKPOINT_FILE" ] && echo "saved" || echo "none")",
    "tool_failure_log": "$([ "$TOOL_FAILURES" -gt 0 ] && echo "has_errors" || echo "clean")"
  }
}
EOF

# Системное сообщение со сводкой
if [ "$TOOL_FAILURES" -gt 0 ]; then
  echo "{\"systemMessage\": \"Сессия завершена. Отчёт: $REPORT_FILE | Ошибок инструментов: $TOOL_FAILURES | Сжатий: $COMPACT_COUNT\"}"
else
  echo "{\"systemMessage\": \"Сессия завершена. Отчёт: $REPORT_FILE | Ошибок: 0 | Сжатий: $COMPACT_COUNT\"}"
fi

exit 0
