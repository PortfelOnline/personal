#!/bin/bash
# PreToolUse guard: response cache | v3 — cache tagging
# 1. Check if this (tool+input) has been called before
# 2. If cached -> exit 1 with content in stderr (model sees without tool call)
# 3. Cache tagging: prefetch vs real. Prefetch entries warm up and convert on use.
# 4. If new -> save hash for PostToolUse, allow

CACHE_DIR="/tmp/claude_cache"
RESULTS_DIR="$CACHE_DIR/results"
mkdir -p "$CACHE_DIR" "$RESULTS_DIR"

CACHE_FILE="$CACHE_DIR/calls.log"
LAST_HASH_FILE="$CACHE_DIR/last_hash"

[ -f "$CACHE_FILE" ] || : > "$CACHE_FILE"

TOOL=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool',''))" 2>/dev/null)

# Normalize tool_input for hashing
TOOL_INPUT_STR=$(echo "$1" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ti = d.get('tool_input',{})
for key in list(ti.keys()):
    if isinstance(ti[key], str) and len(ti[key]) > 200:
        ti[key] = ti[key][:50]
print(json.dumps(ti, sort_keys=True))
" 2>/dev/null)

CALL_HASH=$(echo "$TOOL|$TOOL_INPUT_STR" | shasum 2>/dev/null | cut -d' ' -f1 || echo "")
[ -z "$CALL_HASH" ] || [ -z "$TOOL" ] && exit 0

# Save hash for PostToolUse to save result (real tool, not cache)
echo "$CALL_HASH" > "$LAST_HASH_FILE"

# Determine TTL by tool type (seconds)
get_ttl() {
  local t="$1"
  case "$t" in
    *curl*|*wget*|*WebFetch*|*WebSearch*) echo 300 ;;    # API responses — 5 min
    *graphify*) echo 600 ;;                                # Graph results — 10 min
    *Read*|*Bash\(cat*|*Bash\(ls*) echo 3600 ;;           # File reads — 1 hour
    *) echo 3600 ;;                                         # Default — 1 hour
  esac
}

# Check if we already have a saved result for this call
if [ -f "$RESULTS_DIR/$CALL_HASH.txt" ]; then
  RESULT_SIZE=$(wc -c < "$RESULTS_DIR/$CALL_HASH.txt" 2>/dev/null || echo 0)

  # --- TTL freshness check ---
  TS_FILE="$RESULTS_DIR/$CALL_HASH.ts"
  if [ -f "$TS_FILE" ]; then
    NOW=$(date +%s)
    CACHED_AT=$(cat "$TS_FILE" 2>/dev/null || echo 0)
    AGE=$((NOW - CACHED_AT))
    TTL=$(get_ttl "$TOOL")
    if [ "$AGE" -gt "$TTL" ]; then
      # Stale — remove and treat as miss
      rm -f "$RESULTS_DIR/$CALL_HASH.txt" "$RESULTS_DIR/$CALL_HASH.ts" "$RESULTS_DIR/${CALL_HASH}.tag"
      echo "CACHE STALE: '$TOOL' aged ${age}s > TTL ${TTL}s, re-fetching." >&2
      exit 0
    fi
  fi

  # Check cache tag: prefetch vs real
  TAG_FILE="$RESULTS_DIR/${CALL_HASH}.tag"
  IS_PREFETCH=0
  if [ -f "$TAG_FILE" ]; then
    TAG=$(cat "$TAG_FILE" 2>/dev/null || echo "")
    if [ "$TAG" = "prefetch" ]; then
      IS_PREFETCH=1
      # Remove tag after first use — it becomes a real cache entry
      rm -f "$TAG_FILE"
    fi
  fi

  if [ "$IS_PREFETCH" = "1" ]; then
    echo "CACHE HIT (warm): '$TOOL' — prefetched, first real use (hash=$CALL_HASH, ${RESULT_SIZE}b)." >&2
  else
    echo "CACHE HIT: '$TOOL' already called before (hash=$CALL_HASH, ${RESULT_SIZE}b). Returning:" >&2
  fi

  # Safe truncation with hard incompleteness signal
  if [ "$RESULT_SIZE" -le 1000 ]; then
    cat "$RESULTS_DIR/$CALL_HASH.txt" >&2
  else
    echo "[CACHE_PARTIAL_DO_NOT_TRUST_FULLY]" >&2
    head -c 800 "$RESULTS_DIR/$CALL_HASH.txt" >&2
    echo "" >&2
    echo "[CACHE_PARTIAL: showing 800/${RESULT_SIZE}b. Full result in cache.]" >&2
  fi
  echo "--- end cache ---" >&2
  exit 1
fi

# Log call (rotation: last 20)
echo "$CALL_HASH" >> "$CACHE_FILE"
tail -20 "$CACHE_FILE" > "${CACHE_FILE}.tmp" && mv "${CACHE_FILE}.tmp" "$CACHE_FILE"

exit 0
