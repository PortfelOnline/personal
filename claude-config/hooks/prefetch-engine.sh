#!/bin/bash
# PostToolUse: prefetch engine v2 — speculative execution with quality control
# - Cache tagging: prefetch -> real on first use
# - TTL: timeout 2s per prefetch, killed if stuck
# - Shadow budget: max 10k prefetch tokens, disabled if exceeded
# - Scoring: probability threshold > 0.5
# - Non-blocking: always exit 0

CACHE_DIR="/tmp/claude_cache"
RESULTS_DIR="$CACHE_DIR/results"
mkdir -p "$RESULTS_DIR"

STATE_DIR="/tmp/claude_antiloop"
PREFETCH_TRIGGER="$STATE_DIR/prefetch_signal"
PREFETCH_BUDGET_FILE="$STATE_DIR/prefetch_tokens_used"
PREFETCH_DISABLED_FILE="$STATE_DIR/prefetch_disabled"
CURRENT_PROMPT_FILE="$STATE_DIR/current_prompt"
PROJECT_DIR=$(pwd)

# Detect available timeout
TIMEOUT_CMD=""
if command -v timeout &>/dev/null; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout &>/dev/null; then
  TIMEOUT_CMD="gtimeout"
fi

SIGNAL=$(cat "$PREFETCH_TRIGGER" 2>/dev/null || echo "")
: > "$PREFETCH_TRIGGER"

# === CANARY MODE — 10% chance to skip prefetch for quality comparison ===
CANARY_FILE="$STATE_DIR/prefetch_canary"
CANARY_ACTIVE=0
if [ -f "$CANARY_FILE" ]; then
  CANARY_ACTIVE=$(cat "$CANARY_FILE" 2>/dev/null || echo 0)
fi
if [ "$CANARY_ACTIVE" = "0" ] && [ "$(echo $((RANDOM % 10)))" = "0" ]; then
  echo "1" > "$CANARY_FILE"
  echo "PREFETCH: canary mode (10% chance) — skipping for quality baseline" >&2
  exit 0
fi

# === SHADOW BUDGET CHECK ===
PREFETCH_MAX=10000
DISABLED=0
if [ -f "$PREFETCH_DISABLED_FILE" ]; then
  DISABLED=$(cat "$PREFETCH_DISABLED_FILE" 2>/dev/null || echo 0)
fi
[ "$DISABLED" = "1" ] && exit 0

if [ ! -f "$PREFETCH_BUDGET_FILE" ]; then
  echo "0" > "$PREFETCH_BUDGET_FILE"
fi
PREFETCH_USED=$(cat "$PREFETCH_BUDGET_FILE" 2>/dev/null || echo 0)
if [ "$PREFETCH_USED" -gt "$PREFETCH_MAX" ]; then
  echo "1" > "$PREFETCH_DISABLED_FILE"
  echo "PREFETCH: shadow budget exceeded (${PREFETCH_USED}/${PREFETCH_MAX}), disabled." >&2
  exit 0
fi

# === HELPER: atomic prefetch write with tag ===
prefetch_write() {
  local hash="$1"
  local filepath="$2"
  local size_estimate="$3"
  local prob="$4"

  # Probability check
  [ "$(echo "$prob > 0.5" | bc 2>/dev/null || echo 1)" = "0" ] && return

  # Already cached
  [ -f "$RESULTS_DIR/$hash.txt" ] && return

  # Budget check
  PREFETCH_USED=$((PREFETCH_USED + size_estimate))
  echo "$PREFETCH_USED" > "$PREFETCH_BUDGET_FILE"
  if [ "$PREFETCH_USED" -gt "$PREFETCH_MAX" ]; then
    echo "1" > "$PREFETCH_DISABLED_FILE"
    return
  fi

  # Read file with timeout
  if [ -n "$TIMEOUT_CMD" ]; then
    $TIMEOUT_CMD 2s head -c 1500 "$filepath" > "$RESULTS_DIR/$hash.txt" 2>/dev/null
  else
    head -c 1500 "$filepath" > "$RESULTS_DIR/$hash.txt" 2>/dev/null
  fi

  # Write prefetch tag atomically
  if [ -f "$RESULTS_DIR/$hash.txt" ] && [ -s "$RESULTS_DIR/$hash.txt" ]; then
    echo "prefetch" > "$RESULTS_DIR/${hash}.tag" 2>/dev/null
  else
    rm -f "$RESULTS_DIR/$hash.txt" 2>/dev/null
  fi
}

# === HELPER: compute cache hash matching response-cache.sh ===
compute_hash() {
  local tool="$1"
  local input="$2"
  echo "$tool|$input" | shasum 2>/dev/null | cut -d' ' -f1 || echo ""
}

# === PREFETCH READ (after WebSearch/WebFetch) ===
if [ "$SIGNAL" = "prefetch:read" ]; then
  for target in "package.json" "CLAUDE.md" "settings.json" "README.md"; do
    [ ! -f "$target" ] && continue
    hash=$(compute_hash "Read" "{\"file_path\": \"$target\"}")
    prefetch_write "$hash" "$target" 200 0.6 &
    disown
  done
fi

# === PREFETCH SEARCH (after Read config) ===
# WebSearch via MCP can't be prefetched, but related files can
if [ "$SIGNAL" = "prefetch:websearch" ]; then
  for target in "CLAUDE.md" ".env"; do
    [ ! -f "$target" ] && continue
    hash=$(compute_hash "Read" "{\"file_path\": \"$target\"}")
    prefetch_write "$hash" "$target" 200 0.5 &
    disown
  done
fi

# === PREFETCH GRAPHIFY (after curl) ===
if [ "$SIGNAL" = "prefetch:graphify" ]; then
  GRAPHIFY_DIR=$(find "$PROJECT_DIR" -maxdepth 3 -name "graphify-out" -type d 2>/dev/null | head -1)
  if [ -n "$GRAPHIFY_DIR" ] && [ -f "$GRAPHIFY_DIR/GRAPH_REPORT.md" ]; then
    hash=$(compute_hash "Read" "{\"file_path\": \"$GRAPHIFY_DIR/GRAPH_REPORT.md\"}")
    prefetch_write "$hash" "$GRAPHIFY_DIR/GRAPH_REPORT.md" 300 0.4 &
    disown
  fi
fi

exit 0
