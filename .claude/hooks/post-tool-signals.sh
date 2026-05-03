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
TMP_JSON="$STATE_DIR/last_stdin.json"

# Save stdin to temp file (avoids shell quoting issues with control chars)
cat > "$TMP_JSON"

# --- Tool name ---
TOOL=$(python3 -c "
import sys, json, re
with open('$TMP_JSON') as f:
    raw = f.read()
d = None
try:
    d = json.loads(raw)
except:
    import re
    cleaned = re.sub(r'[\x00-\x1f]', '', raw)
    try:
        d = json.loads(cleaned)
    except:
        print('Bash')
        sys.exit(0)
print(d.get('tool_name', d.get('tool', 'Bash')))
" 2>/dev/null)
TOOL="${TOOL:-Bash}"

# --- Interrupted / error status ---
INTERRUPTED=$(python3 -c "
import sys, json, re
with open('$TMP_JSON') as f:
    raw = f.read()
d = None
try:
    d = json.loads(raw)
except:
    cleaned = re.sub(r'[\x00-\x1f]', '', raw)
    try:
        d = json.loads(cleaned)
    except:
        print('false')
        sys.exit(0)
tr = d.get('tool_response') or {}
print(str(tr.get('interrupted', 'false')).lower())
" 2>/dev/null)

# --- Result size from tool_response ---
RESULT_SIZE=$(python3 -c "
import sys, json, re
with open('$TMP_JSON') as f:
    raw = f.read()
d = None
try:
    d = json.loads(raw)
except:
    cleaned = re.sub(r'[\x00-\x1f]', '', raw)
    try:
        d = json.loads(cleaned)
    except:
        print('0')
        sys.exit(0)
tr = d.get('tool_response') or {}
total = 0
if isinstance(tr, dict):
    for k in ('stdout', 'stderr', 'content', 'text', 'data', 'result', 'response', 'output', 'message', 'body', 'error'):
        v = tr.get(k, '')
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, dict):
            total += sum(len(str(vv)) for vv in v.values() if isinstance(vv, str))
elif isinstance(tr, str):
    total = len(tr)
print(str(total))
" 2>/dev/null)
RESULT_SIZE="${RESULT_SIZE:-0}"

# --- Error tracking ---
# No exit_code field in PostToolUse — use interrupted + empty result
# Исключения: Read/Edit/Task*/Write/AskUserQuestion — их размер <10b НЕ является ошибкой
IS_ERROR=0
if [ "$INTERRUPTED" = "true" ]; then
  IS_ERROR=1
elif [ "$RESULT_SIZE" -lt 10 ]; then
  # Для Read/Edit/Task/Write/AskUserQuestion — пустой результат нормален
  case "$TOOL" in
    Read|Edit|Write|TaskCreate|TaskUpdate|TaskOutput|TaskStop|AskUserQuestion|Monitor)
      IS_ERROR=0 ;;
    *)
      IS_ERROR=1 ;;
  esac
fi

echo "$IS_ERROR" > "$LAST_RESULT_ERROR"

# --- ONE-SHOT EXEMPT ---
ONE_SHOT_EXEMPT_FILE="$STATE_DIR/one_shot_exempt"
if [ "$IS_ERROR" = "1" ] || [ "$RESULT_SIZE" -lt 100 ]; then
  echo "1" > "$ONE_SHOT_EXEMPT_FILE"
else
  echo "0" > "$ONE_SHOT_EXEMPT_FILE"
fi

# --- Runtime logging ---
LOG_FILE="$HOME/.claude/logs/runtime.log"
mkdir -p "$(dirname "$LOG_FILE")"
ROTATION_MAX=1000
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt "$ROTATION_MAX" ]; then
  tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
STEP=$(cat /tmp/claude_antiloop/step_count 2>/dev/null || echo "?")
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | step=$STEP | tool=$TOOL | size=${RESULT_SIZE}b | interrupted=$INTERRUPTED | error=$IS_ERROR" >> "$LOG_FILE"

# --- Curl failure detection (check command, not tool name) ---
CMD=$(python3 -c "
import sys, json
with open('$TMP_JSON') as f:
    d = json.loads(f.read())
ti = d.get('tool_input') or {}
print(str(ti.get('command', '')))
" 2>/dev/null)
if echo "$CMD" | grep -qE "^(curl|wget)\s"; then
  if [ "$IS_ERROR" = "1" ]; then
    echo "1" > "$CURL_FAILED_FILE"
  fi
fi

# --- Graphify empty detection ---
if echo "$TOOL" | grep -qE "graphify"; then
  if [ "$RESULT_SIZE" -lt 50 ]; then
    echo "1" > "$GRAPHIFY_EMPTY_FILE"
  fi
fi

# --- Reset signals on successful data fetches (check command, not tool) ---
if echo "$CMD" | grep -qE "^(curl|wget)\s"; then
  if [ "$IS_ERROR" = "0" ] && [ "$RESULT_SIZE" -ge 50 ]; then
    echo "0" > "$CURL_FAILED_FILE"
  fi
fi

exit 0
