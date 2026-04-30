#!/bin/bash
# PreToolUse guard: HARD STOP on loops | v5 — final
# Rules:
#   - ADAPTIVE MAX_STEPS = estimate_complexity(prompt) -> 2-5
#   - Same file re-read = STOP
#   - >3 files in last 5 reads = STOP
#   - MAX_CALLS_PER_STEP = 2 (same tool chained)
#   - Dead-end detector (same input -> no new info)
#   - Tool priority (expensive tools blocked on late steps)
#   - Browser hard ban + curl/graphify fallback
#   - Cumulative budget + phase reset (floor=5k)
#   - Result reuse within step + error escape
#   - exit 1 = block tool, exit 0 = allow

STATE_DIR="/tmp/claude_antiloop"
mkdir -p "$STATE_DIR"
STEP_FILE="$STATE_DIR/step_count"
FILES_LOG="$STATE_DIR/files_log"
TOOLS_LOG="$STATE_DIR/tools_log"
CALLS_FILE="$STATE_DIR/total_calls"
PHASE_FILE="$STATE_DIR/current_phase"
TOOL_OUTPUTS_FILE="$STATE_DIR/step_output_hashes"
CURL_FAILED_FILE="$STATE_DIR/curl_failed"
GRAPHIFY_EMPTY_FILE="$STATE_DIR/graphify_empty"
TASK_TYPE_FILE="$STATE_DIR/task_type"
MAX_STEPS_FILE="$STATE_DIR/max_steps"
RESULT_TOKENS_FILE="$STATE_DIR/result_tokens_accumulated"
PREFETCH_TRIGGER="$STATE_DIR/prefetch_signal"
LAST_TOOL_FILE="$STATE_DIR/last_tool_hash"
LAST_ERROR_STEP="$STATE_DIR/last_error_step"
LAST_RESULT_ERROR="$STATE_DIR/last_result_error"

# Init on first run
if [ ! -f "$STEP_FILE" ] || [ "$(cat "$STEP_FILE")" = "0" ]; then
  echo "0" > "$STEP_FILE"
  : > "$FILES_LOG"
  : > "$TOOLS_LOG"
  echo "0" > "$CALLS_FILE"
  echo "init" > "$PHASE_FILE"
  : > "$TOOL_OUTPUTS_FILE"
  echo "0" > "$CURL_FAILED_FILE"
  echo "0" > "$GRAPHIFY_EMPTY_FILE"
  echo "" > "$TASK_TYPE_FILE"
  echo "5" > "$MAX_STEPS_FILE"
  echo "0" > "$RESULT_TOKENS_FILE"
  : > "$PREFETCH_TRIGGER"
  : > "$LAST_TOOL_FILE"
  echo "0" > "$LAST_ERROR_STEP"
  echo "0" > "$LAST_RESULT_ERROR"
fi

TOOL=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool',''))" 2>/dev/null)
TOOL_INPUT=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{})))" 2>/dev/null)
FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_path',''))" 2>/dev/null)

# === ADAPTIVE MAX_STEPS: estimate from prompt on first call ===
if [ ! -f "$MAX_STEPS_FILE" ] || [ "$(cat "$MAX_STEPS_FILE")" = "5" ]; then
  PROMPT=$(cat "$STATE_DIR/current_prompt" 2>/dev/null || echo "")
  PROMPT_LEN=${#PROMPT}

  if [ "$PROMPT_LEN" -lt 50 ]; then
    echo "2" > "$MAX_STEPS_FILE"
    echo "ADAPTIVE: MAX_STEPS=2 (short query, ${PROMPT_LEN}b)" >&2
  elif [ "$PROMPT_LEN" -lt 200 ]; then
    echo "3" > "$MAX_STEPS_FILE"
    echo "ADAPTIVE: MAX_STEPS=3 (medium query, ${PROMPT_LEN}b)" >&2
  elif echo "$PROMPT" | grep -qiE "architecture|design|refactor|arhitektur|refactor|sproektir"; then
    echo "5" > "$MAX_STEPS_FILE"
    echo "ADAPTIVE: MAX_STEPS=5 (architecture/refactoring)" >&2
  elif echo "$PROMPT" | grep -qiE "error|bug|oshibka|bag|fix|pochini|lomal"; then
    echo "4" > "$MAX_STEPS_FILE"
    echo "ADAPTIVE: MAX_STEPS=4 (bug/error)" >&2
  else
    echo "3" > "$MAX_STEPS_FILE"
    echo "ADAPTIVE: MAX_STEPS=3 (standard query)" >&2
  fi
fi

# === DETECT TASK TYPE for confidence thresholds ===
CURRENT_TASK_TYPE=$(cat "$TASK_TYPE_FILE" 2>/dev/null || echo "")
if [ -z "$CURRENT_TASK_TYPE" ] || [ "$CURRENT_TASK_TYPE" = "unknown" ]; then
  TOOL_HISTORY=$(cat "$TOOLS_LOG" 2>/dev/null || echo "")
  if echo "$TOOL_HISTORY" | grep -qE "WebSearch|WebFetch|curl|graphify.*query"; then
    echo "research" > "$TASK_TYPE_FILE"
  elif echo "$TOOL_HISTORY" | grep -qE "Write|Edit|Bash\(php|Bash\(python|Bash\(node|Bash\(npm"; then
    echo "code" > "$TASK_TYPE_FILE"
  elif echo "$TOOL_HISTORY" | grep -qE "Read|Grep|Glob"; then
    echo "explore" > "$TASK_TYPE_FILE"
  fi
fi

# === DETECT PHASE CHANGE for budget reset ===
PREV_PHASE=$(cat "$PHASE_FILE" 2>/dev/null || echo "init")
CURRENT_PHASE="$PREV_PHASE"
if echo "$TOOL" | grep -qE "Read|Grep|Glob"; then
  CURRENT_PHASE="read"
elif echo "$TOOL" | grep -qE "Write|Edit|Bash\(echo|Bash\(cat.*>"; then
  CURRENT_PHASE="write"
elif echo "$TOOL" | grep -qE "Bash\(git|Bash\(npm|Bash\(npx|Bash\(docker"; then
  CURRENT_PHASE="exec"
elif echo "$TOOL" | grep -qE "WebSearch|WebFetch|curl|Bash\(curl"; then
  CURRENT_PHASE="fetch"
elif echo "$TOOL" | grep -qE "playwright|browser|Browser"; then
  CURRENT_PHASE="browser"
fi

# Increment step and total calls
STEP=$(cat "$STEP_FILE")
STEP=$((STEP + 1))
echo "$STEP" > "$STEP_FILE"

TOTAL_CALLS=$(cat "$CALLS_FILE")
TOTAL_CALLS=$((TOTAL_CALLS + 1))
echo "$TOTAL_CALLS" > "$CALLS_FILE"

# Log tool (keep last 10)
echo "$STEP:$TOOL" >> "$TOOLS_LOG"
tail -10 "$TOOLS_LOG" > "${TOOLS_LOG}.tmp" && mv "${TOOLS_LOG}.tmp" "$TOOLS_LOG"

# Log read files (keep last 20)
if [ "$TOOL" = "Read" ] && [ -n "$FILE_PATH" ]; then
  echo "$STEP:$FILE_PATH" >> "$FILES_LOG"
  tail -20 "$FILES_LOG" > "${FILES_LOG}.tmp" && mv "${FILES_LOG}.tmp" "$FILES_LOG"
fi

# Track curl/graphify outcomes for browser fallback
if echo "$TOOL" | grep -qE "Bash\(curl|Bash\(wget"; then
  echo "1" > "$CURL_FAILED_FILE"
fi
if echo "$TOOL" | grep -qE "graphify.*query|graphify.*explain"; then
  echo "1" > "$GRAPHIFY_EMPTY_FILE"
fi

# === RESULT REUSE WITHIN STEP ===
TOOL_INPUT_HASH=$(echo "$TOOL|$TOOL_INPUT" | shasum 2>/dev/null | cut -d' ' -f1 || echo "")
if [ -n "$TOOL_INPUT_HASH" ]; then
  STEP_HASHES=$(cat "$TOOL_OUTPUTS_FILE" 2>/dev/null || echo "")
  if echo "$STEP_HASHES" | grep -qF "$TOOL_INPUT_HASH"; then
    # Escape: if previous result was error, allow retry
    ERROR_FLAG=$(cat "$LAST_RESULT_ERROR" 2>/dev/null || echo "0")
    if [ "$ERROR_FLAG" = "1" ]; then
      echo "REUSE: duplicate, but previous result was error -- retry allowed." >&2
      # Clear error flag so next retry follows normal rules
      echo "0" > "$LAST_RESULT_ERROR"
    else
      echo "REUSE: same tool+input already called this step. Blocked." >&2
      exit 1
    fi
  fi
  echo "$STEP:$TOOL_INPUT_HASH" >> "$TOOL_OUTPUTS_FILE"
  tail -10 "$TOOL_OUTPUTS_FILE" > "${TOOL_OUTPUTS_FILE}.tmp" && mv "${TOOL_OUTPUTS_FILE}.tmp" "$TOOL_OUTPUTS_FILE"
fi

# === DEAD-END DETECTOR: same input as last call = no new info ===
if [ -n "$TOOL_INPUT_HASH" ] && [ -f "$LAST_TOOL_FILE" ]; then
  PREV_HASH=$(cat "$LAST_TOOL_FILE" 2>/dev/null || echo "")
  if [ -n "$PREV_HASH" ] && [ "$PREV_HASH" = "$TOOL_INPUT_HASH" ]; then
    echo "DEAD-END: same input as previous call (no new information). STOP." >&2
    exit 1
  fi
fi
echo "$TOOL_INPUT_HASH" > "$LAST_TOOL_FILE"

# === REFLECTION COOLDOWN: skip if last error was < 2 steps ago ===
# Prevents micro-loop: error -> reflect -> same action -> error
ERROR_STEP=$(cat "$LAST_ERROR_STEP" 2>/dev/null || echo 0)
if [ "$ERROR_STEP" -gt 0 ] && [ "$((STEP - ERROR_STEP))" -le 1 ]; then
  ERROR_FLAG=$(cat "$LAST_RESULT_ERROR" 2>/dev/null || echo 0)
  if [ "$ERROR_FLAG" = "1" ]; then
    echo "REFLECTION COOLDOWN: last error was at step $ERROR_STEP (only ${STEP}b ago). STOP." >&2
    exit 1
  fi
fi

# Track error steps for cooldown
if [ -f "$LAST_RESULT_ERROR" ]; then
  ERROR_FLAG=$(cat "$LAST_RESULT_ERROR" 2>/dev/null || echo 0)
  if [ "$ERROR_FLAG" = "1" ]; then
    echo "$STEP" > "$LAST_ERROR_STEP"
  fi
fi

# === PHASE CHANGE: reset budget (with floor) ===
if [ "$CURRENT_PHASE" != "$PREV_PHASE" ] && [ "$PREV_PHASE" != "init" ]; then
  BUDGET_FILE="$STATE_DIR/tokens_used"
  if [ -f "$BUDGET_FILE" ]; then
    TOKENS_USED=$(cat "$BUDGET_FILE" 2>/dev/null || echo 0)
    TOKENS_USED=$((TOKENS_USED * 50 / 100))
    # Floor: prevent budget from being reset to near-zero on frequent phase changes
    if [ "$TOKENS_USED" -lt 5000 ]; then
      TOKENS_USED=5000
    fi
    echo "$TOKENS_USED" > "$BUDGET_FILE"
    echo "PHASE RESET: phase change $PREV_PHASE -> $CURRENT_PHASE, budget halved (floor=5k, ~${TOKENS_USED}t)" >&2
  fi
  echo "$CURRENT_PHASE" > "$PHASE_FILE"
fi

# === TRIGGER PREFETCH for speculative execution ===
if echo "$TOOL" | grep -qE "Read" && [ -n "$FILE_PATH" ]; then
  if echo "$FILE_PATH" | grep -qiE "config|settings|\.env|readme|guide|manual"; then
    echo "prefetch:websearch" > "$PREFETCH_TRIGGER"
  fi
elif echo "$TOOL" | grep -qE "WebSearch|WebFetch"; then
  echo "prefetch:read" > "$PREFETCH_TRIGGER"
elif echo "$TOOL" | grep -qE "Bash\(curl"; then
  echo "prefetch:graphify" > "$PREFETCH_TRIGGER"
fi

# === HARD STOPS (exit 1) ===

# 0. ADAPTIVE MAX_STEPS
MAX_STEPS=$(cat "$MAX_STEPS_FILE" 2>/dev/null || echo 5)
if [ "$STEP" -gt "$MAX_STEPS" ]; then
  echo "HARD STOP: step limit exceeded (ADAPTIVE MAX_STEPS=$MAX_STEPS)." >&2
  exit 1
fi

# 2. Same file re-read
if [ "$TOOL" = "Read" ] && [ -n "$FILE_PATH" ]; then
  COUNT=$(tail -6 "$FILES_LOG" 2>/dev/null | grep -cF "$FILE_PATH")
  if [ "$COUNT" -ge 2 ]; then
    echo "HARD STOP: re-reading file '$FILE_PATH' ($COUNT times in 6 steps)." >&2
    exit 1
  fi
fi

# 3. >3 files in last 5 reads
if [ "$TOOL" = "Read" ] && [ -n "$FILE_PATH" ]; then
  FILE_COUNT=$(tail -5 "$FILES_LOG" 2>/dev/null | awk -F: '{print $2}' | sort -u | wc -l)
  if [ "$FILE_COUNT" -gt 3 ]; then
    echo "HARD STOP: $FILE_COUNT different files in last 5 steps (max 3)." >&2
    exit 1
  fi
fi

# 4. MAX_TOTAL_CALLS
if [ "$TOTAL_CALLS" -gt 5 ]; then
  echo "HARD STOP: tool call limit exceeded (MAX_TOTAL_CALLS=5)." >&2
  exit 1
fi

# 5. Same tool chained 2+ times in last 3 calls
SAME_TOOL_COUNT=$(tail -3 "$TOOLS_LOG" 2>/dev/null | awk -F: '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $1}')
LAST_TOOL=$(tail -1 "$TOOLS_LOG" 2>/dev/null | awk -F: '{print $2}')
if [ "$SAME_TOOL_COUNT" -ge 2 ] && [ -n "$LAST_TOOL" ]; then
  echo "HARD STOP: tool chaining -- $LAST_TOOL called $SAME_TOOL_COUNT times in a row." >&2
  exit 1
fi

# 6. Tool priority
if [ "$STEP" -gt 2 ]; then
  HIGH_COST_PATTERNS="playwright|browser|WebSearch|Bash(docker)|Bash(npx playwright)"
  if echo "$TOOL" | grep -qE "$HIGH_COST_PATTERNS" 2>/dev/null; then
    echo "HARD STOP: expensive tool '$TOOL' at step $STEP (HIGH_COST only before step 2)." >&2
    exit 1
  fi
fi
if [ "$STEP" -gt 3 ]; then
  MEDIUM_COST_PATTERNS="Bash(curl)|Bash(ssh)|WebFetch|mcp__graphify"
  if echo "$TOOL" | grep -qE "$MEDIUM_COST_PATTERNS" 2>/dev/null; then
    echo "HARD STOP: tool '$TOOL' at step $STEP (MEDIUM_COST only before step 3)." >&2
    exit 1
  fi
fi

# 7. Hard ban: browser/playwright without strong signal
BROWSER_PATTERNS="playwright|browser|Browser"
if echo "$TOOL" | grep -qE "$BROWSER_PATTERNS" 2>/dev/null; then
  BROWSER_SIGNALS=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    s = str(d).lower()
    signals = ['login', 'signin', 'sign in', 'auth', 'oauth', 'dynamic',
               'requires browser', 'javascript', 'screenshot', 'after auth',
               'authenticate', 'session', 'cookie', 'webapp']
    found = [sig for sig in signals if sig in s]
    print(','.join(found) if found else 'NONE')
except:
    print('NONE')
" 2>/dev/null)

  CURL_FAILED=$(cat "$CURL_FAILED_FILE" 2>/dev/null || echo 0)
  GRAPHIFY_EMPTY=$(cat "$GRAPHIFY_EMPTY_FILE" 2>/dev/null || echo 0)
  if [ "$BROWSER_SIGNALS" = "NONE" ]; then
    if [ "$CURL_FAILED" = "1" ] && [ "$GRAPHIFY_EMPTY" = "1" ]; then
      echo "BROWSER FALLBACK: curl failed + graphify empty, browser allowed." >&2
    else
      echo "HARD STOP: browser/playwright without strong signal (login, dynamic, screenshot, auth)." >&2
      echo "   Browser only for: login, dynamic pages, screenshots after auth." >&2
      exit 1
    fi
  fi
fi

# 8. Cumulative budget
BUDGET_FILE="$STATE_DIR/tokens_used"
if [ ! -f "$BUDGET_FILE" ]; then
  echo "0" > "$BUDGET_FILE"
fi
TOKENS_USED=$(cat "$BUDGET_FILE")

ESTIMATE=0
if echo "$TOOL" | grep -qE "Read" 2>/dev/null; then
  ESTIMATE=800
elif echo "$TOOL" | grep -qE "Write|Edit" 2>/dev/null; then
  ESTIMATE=500
elif echo "$TOOL" | grep -qE "WebSearch|WebFetch" 2>/dev/null; then
  ESTIMATE=3000
elif echo "$TOOL" | grep -qE "Bash\(curl|Bash\(ssh" 2>/dev/null; then
  ESTIMATE=2000
elif echo "$TOOL" | grep -qE "playwright|browser|Browser" 2>/dev/null; then
  ESTIMATE=5000
elif echo "$TOOL" | grep -qE "graphify" 2>/dev/null; then
  ESTIMATE=1000
elif echo "$TOOL" | grep -qE "Bash\(git|Bash\(ls|Bash\(echo|Bash\(cat|Bash\(find" 2>/dev/null; then
  ESTIMATE=200
elif echo "$TOOL" | grep -qE "Bash\(docker" 2>/dev/null; then
  ESTIMATE=4000
elif echo "$TOOL" | grep -qE "Bash\(npx|Bash\(npm" 2>/dev/null; then
  ESTIMATE=1500
elif echo "$TOOL" | grep -qE "Bash\(php|Bash\(python3|Bash\(node" 2>/dev/null; then
  ESTIMATE=2000
else
  ESTIMATE=500
fi

TOKENS_USED=$((TOKENS_USED + ESTIMATE))
echo "$TOKENS_USED" > "$BUDGET_FILE"

SOFT_LIMIT=30000
HARD_LIMIT=50000
if [ "$TOKENS_USED" -gt "$HARD_LIMIT" ]; then
  echo "HARD STOP: task budget exceeded (HARD_LIMIT=$HARD_LIMIT, used ~${TOKENS_USED}t)." >&2
  exit 1
fi
if [ "$TOKENS_USED" -gt "$SOFT_LIMIT" ] && [ "$STEP" -gt 3 ]; then
  LOW_COST_PATTERNS="Read|Write|Edit|Bash\(ls|Bash\(git|Bash\(echo|Bash\(cat"
  if ! echo "$TOOL" | grep -qE "$LOW_COST_PATTERNS" 2>/dev/null; then
    echo "HARD STOP: exceeded SOFT_LIMIT=$SOFT_LIMIT (~${TOKENS_USED}t). LOW_COST only." >&2
    exit 1
  fi
fi

exit 0
