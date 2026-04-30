#!/bin/bash
# PostToolUse hook: save tool result to response cache
# Reads last_hash from PreToolUse, saves stdout+stderr to cache
# stdin: JSON with tool_result, tool_input, stdout, stderr, etc.

CACHE_DIR="/tmp/claude_cache"
RESULTS_DIR="$CACHE_DIR/results"
mkdir -p "$RESULTS_DIR"

LAST_HASH_FILE="$CACHE_DIR/last_hash"

# Read the hash saved by PreToolUse
if [ ! -f "$LAST_HASH_FILE" ]; then
  exit 0
fi

CALL_HASH=$(cat "$LAST_HASH_FILE")
rm -f "$LAST_HASH_FILE"

if [ -z "$CALL_HASH" ]; then
  exit 0
fi

# Don't overwrite existing cached result
if [ -f "$RESULTS_DIR/$CALL_HASH.txt" ]; then
  exit 0
fi

# Extract result from stdin (save stdout/stderr)
echo "$1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
output = ''

# Try to get actual result content
result = d.get('tool_result', {}) or {}
if isinstance(result, dict):
    output = json.dumps(result, indent=2, ensure_ascii=False)
else:
    output = str(result)

# Also capture stdout/stderr if available
stdout = d.get('stdout', '') or ''
stderr = d.get('stderr', '') or ''

combined = ''
if stdout and stdout != output:
    combined = '=== STDOUT ===\n' + stdout[:2000] + '\n'
combined += '=== RESULT ===\n' + output[:2000]
if stderr:
    combined += '\n=== STDERR ===\n' + stderr[:500]

open('$RESULTS_DIR/$CALL_HASH.txt', 'w').write(combined[:5000])
" 2>/dev/null

# Save timestamp for TTL freshness check
date +%s > "$RESULTS_DIR/$CALL_HASH.ts"

exit 0
