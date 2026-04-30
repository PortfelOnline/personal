#!/bin/bash
# PostToolUse: track tool outcomes for anti-loop-guard decisions
# - curl/graphify outcomes for browser fallback
# - Tool error status for result reuse escape
# - Non-blocking: always exit 0

STATE_DIR="/tmp/claude_antiloop"
mkdir -p "$STATE_DIR"
CURL_FAILED_FILE="$STATE_DIR/curl_failed"
GRAPHIFY_EMPTY_FILE="$STATE_DIR/graphify_empty"
LAST_RESULT_ERROR="$STATE_DIR/last_result_error"

STDIN=$(cat)

# Detect tool
TOOL=$(echo "$STDIN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_name', d.get('tool', '')))
" 2>/dev/null)

# Extract result for size check
RESULT=$(echo "$STDIN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
result = d.get('tool_result', {}) or {}
if isinstance(result, dict):
    print(json.dumps(result))
else:
    print(str(result))
" 2>/dev/null)
RESULT_SIZE=${#RESULT}

# Get exit code if available
EXIT_CODE=$(echo "$STDIN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('exit_code', d.get('tool_result', {}).get('exit_code', '0')))
" 2>/dev/null)
EXIT_CODE=${EXIT_CODE:-0}

# --- General error tracking for retry escape ---
# Check for error conditions
IS_ERROR=0
if [ "$EXIT_CODE" != "0" ]; then
  IS_ERROR=1
elif [ "$RESULT_SIZE" -lt 10 ]; then
  # Empty/minimal result = likely error
  IS_ERROR=1
elif echo "$RESULT" | grep -qiE "error|exception|timeout|fail|not found|permission denied|connection refused"; then
  IS_ERROR=1
fi

echo "$IS_ERROR" > "$LAST_RESULT_ERROR"

# --- Runtime logging (lightweight, < 1ms) ---
LOG_FILE="$HOME/.claude/logs/runtime.log"
mkdir -p "$(dirname "$LOG_FILE")"
ROTATION_MAX=500
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt "$ROTATION_MAX" ]; then
  tail -200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
STEP=$(cat /tmp/claude_antiloop/step_count 2>/dev/null || echo "?")
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | step=$STEP | tool=$TOOL | size=${RESULT_SIZE}b | exit=$EXIT_CODE | error=$IS_ERROR" >> "$LOG_FILE"

# --- Curl failure detection ---
if echo "$TOOL" | grep -qE "Bash\(curl|Bash\(wget"; then
  if [ "$EXIT_CODE" != "0" ] || [ "$IS_ERROR" = "1" ]; then
    echo "1" > "$CURL_FAILED_FILE"
  fi
fi

# --- Graphify empty detection ---
if echo "$TOOL" | grep -qE "graphify"; then
  if [ "$RESULT_SIZE" -lt 50 ]; then
    echo "1" > "$GRAPHIFY_EMPTY_FILE"
  fi
fi

# --- Reset signals on successful data fetches ---
if echo "$TOOL" | grep -qE "WebFetch|WebSearch|Bash\(curl|Bash\(wget"; then
  if [ "$EXIT_CODE" = "0" ] && [ "$RESULT_SIZE" -ge 50 ]; then
    echo "0" > "$CURL_FAILED_FILE"
  fi
fi

exit 0
