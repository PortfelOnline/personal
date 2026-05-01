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

STDIN_RAW=$(cat)
if [ -z "$STDIN_RAW" ]; then
  # Nothing on stdin — can't log
  exit 0
fi

# Parse stdin once. Claude Code PostToolUse format:
# {"tool_name":"...","tool_input":{...},"tool_result":"...","exit_code":0}
# NOTE: tool_result may be a string (not nested JSON).
TOOL=$(echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(d.get('tool_name', d.get('tool', '')))
" 2>/dev/null)
TOOL=${TOOL:-unknown}

# Extract result size from raw JSON — robust even if tool_result has control chars
# We parse the JSON once and measure the string length of tool_result
PARSED=$(echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
result = d.get('tool_result', d.get('result', ''))
if isinstance(result, str):
    print(len(result))
elif isinstance(result, dict) or isinstance(result, list):
    print(len(json.dumps(result)))
else:
    print(len(str(result)))
" 2>/dev/null)
RESULT_SIZE=${PARSED:-0}

# Get exit code
EXIT_CODE=$(echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
# Try several possible field names
ec = d.get('exit_code', d.get('exitCode', d.get('code', '0')))
print(ec)
" 2>/dev/null)
EXIT_CODE=${EXIT_CODE:-0}

# --- General error tracking for retry escape ---
# Check for error conditions from exit code only
# NOTE: we do NOT grep result content for error keywords —
# that would false-positive on normal text containing words like "fail" or "error".
IS_ERROR=0
if [ "$EXIT_CODE" != "0" ]; then
  IS_ERROR=1
elif [ "$RESULT_SIZE" -lt 10 ]; then
  # Empty/minimal result = likely error (no data returned)
  IS_ERROR=1
fi

echo "$IS_ERROR" > "$LAST_RESULT_ERROR"

# === ONE-SHOT EXEMPT: если ошибка или мало данных → разрешаем второй tool ===
# При ошибке или результате <50 токенов модель может вызвать ещё один tool
ONE_SHOT_EXEMPT_FILE="$STATE_DIR/one_shot_exempt"
if [ "$IS_ERROR" = "1" ] || [ "$RESULT_SIZE" -lt 100 ]; then
  echo "1" > "$ONE_SHOT_EXEMPT_FILE"
else
  echo "0" > "$ONE_SHOT_EXEMPT_FILE"
fi

# --- Runtime logging (lightweight, < 1ms) ---
LOG_FILE="$HOME/.claude/logs/runtime.log"
mkdir -p "$(dirname "$LOG_FILE")"
ROTATION_MAX=500
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt "$ROTATION_MAX" ]; then
  tail -200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
STEP=$(cat /tmp/claude_antiloop/step_count 2>/dev/null || echo "?")
SIZE_HUMAN="$RESULT_SIZE"
if [ "$RESULT_SIZE" -ge 1048576 ]; then
  SIZE_HUMAN="$(echo "scale=1; $RESULT_SIZE/1048576" | bc 2>/dev/null)MB"
elif [ "$RESULT_SIZE" -ge 1024 ]; then
  SIZE_HUMAN="$(echo "scale=1; $RESULT_SIZE/1024" | bc 2>/dev/null)KB"
else
  SIZE_HUMAN="${RESULT_SIZE}b"
fi
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | step=$STEP | tool=$TOOL | size=$SIZE_HUMAN | exit=$EXIT_CODE | error=$IS_ERROR" >> "$LOG_FILE"

# Debug: log raw field names from stdin once to detect format mismatches
FIELD_NAMES_FILE="$STATE_DIR/stdin_field_names"
if [ ! -f "$FIELD_NAMES_FILE" ]; then
  echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
print(','.join(sorted(d.keys())))
" 2>/dev/null > "$FIELD_NAMES_FILE"
fi

# --- Curl failure detection: check tool_input for curl/wget commands ---
if [ "$TOOL" = "Bash" ]; then
  COMMAND=$(echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
ti = d.get('tool_input', {})
if isinstance(ti, dict):
    print(ti.get('command', ''))
else:
    print(str(ti))
" 2>/dev/null)
  if echo "$COMMAND" | grep -qiE "^curl|^wget"; then
    if [ "$EXIT_CODE" != "0" ] || [ "$IS_ERROR" = "1" ]; then
      echo "1" > "$CURL_FAILED_FILE"
    fi
  fi
fi

# --- Graphify empty detection ---
if echo "$TOOL" | grep -qiE "graphify"; then
  if [ "$RESULT_SIZE" -lt 50 ]; then
    echo "1" > "$GRAPHIFY_EMPTY_FILE"
  fi
fi

# --- Reset signals on successful data fetches ---
RESET_CURL=0
if [ "$TOOL" = "Bash" ]; then
  COMMAND=$(echo "$STDIN_RAW" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
ti = d.get('tool_input', {})
if isinstance(ti, dict):
    print(ti.get('command', ''))
else:
    print(str(ti))
" 2>/dev/null)
  if echo "$COMMAND" | grep -qiE "^curl|^wget"; then
    RESET_CURL=1
  fi
elif echo "$TOOL" | grep -qiE "WebFetch|WebSearch"; then
  RESET_CURL=1
fi

if [ "$RESET_CURL" = "1" ] && [ "$EXIT_CODE" = "0" ] && [ "$RESULT_SIZE" -ge 50 ]; then
  echo "0" > "$CURL_FAILED_FILE"
fi

exit 0
