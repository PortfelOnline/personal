#!/bin/bash
# SessionStart: warm start cache — prefetch common files before first use.
# Reduces first-response latency by having data ready in response cache.
# Non-blocking: always exit 0
#
# Relevance check: only prefetch if file is likely relevant to session.
# - CLAUDE.md: always relevant (session config)
# - settings.json: always relevant (runtime config)
# - package.json: only if project has node_modules
# - graphify: only if project has graphify-out dir

CACHE_DIR="/tmp/claude_cache"
RESULTS_DIR="$CACHE_DIR/results"
mkdir -p "$RESULTS_DIR"

PROJECT_DIR=$(pwd)

# Compute cache hash matching response-cache.sh algorithm
compute_hash() {
  local tool="$1"
  local input="$2"
  echo "$tool|$input" | shasum 2>/dev/null | cut -d' ' -f1 || echo ""
}

warm_cache() {
  local file="$1"
  local hash="$2"
  local prob="$3"
  local result_file="$RESULTS_DIR/${hash}.txt"
  local tag_file="$RESULTS_DIR/${hash}.tag"

  # Skip if already cached
  [ -f "$result_file" ] && return 0

  # Probability gate
  RAND_VAL=$((RANDOM % 100))
  PROB_INT=$(echo "$prob * 100" | bc 2>/dev/null | sed 's/\..*//' || echo 50)
  [ "$RAND_VAL" -ge "$PROB_INT" ] && return 0

  # Check relevance: file should exist and be reasonably sized
  if [ ! -f "$file" ]; then
    return 0
  fi

  # Size check: skip files > 50KB
  local size
  size=$(wc -c < "$file" 2>/dev/null || echo 0)
  if [ "$size" -gt 50000 ]; then
    return 0
  fi

  # Read file and prefetch
  cat "$file" > "$result_file"
  echo "prefetch" > "$tag_file"
}

# Prefetch CLAUDE.md (always relevant — session config)
CLAUDE_FILE=$(find "$PROJECT_DIR" -maxdepth 3 -name "CLAUDE.md" -type f 2>/dev/null | head -1)
if [ -n "$CLAUDE_FILE" ]; then
  hash=$(compute_hash "Read" "{\"file_path\": \"$CLAUDE_FILE\"}")
  warm_cache "$CLAUDE_FILE" "$hash" 0.9
fi

# Prefetch settings.json (always relevant — runtime config)
SETTINGS_FILE="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
  hash=$(compute_hash "Read" "{\"file_path\": \"$SETTINGS_FILE\"}")
  warm_cache "$SETTINGS_FILE" "$hash" 0.8
fi

# Prefetch package.json only if node_modules exists (relevance check)
if [ -d "$PROJECT_DIR/node_modules" ]; then
  PKG_FILE=$(find "$PROJECT_DIR" -maxdepth 1 -name "package.json" -type f 2>/dev/null | head -1)
  if [ -n "$PKG_FILE" ]; then
    hash=$(compute_hash "Read" "{\"file_path\": \"$PKG_FILE\"}")
    warm_cache "$PKG_FILE" "$hash" 0.6
  fi
fi

# Prefetch graphify report if present
GRAPHIFY_DIR=$(find "$PROJECT_DIR" -maxdepth 3 -name "graphify-out" -type d 2>/dev/null | head -1)
if [ -n "$GRAPHIFY_DIR" ] && [ -f "$GRAPHIFY_DIR/GRAPH_REPORT.md" ]; then
  hash=$(compute_hash "Read" "{\"file_path\": \"$GRAPHIFY_DIR/GRAPH_REPORT.md\"}")
  warm_cache "$GRAPHIFY_DIR/GRAPH_REPORT.md" "$hash" 0.4
fi

exit 0
