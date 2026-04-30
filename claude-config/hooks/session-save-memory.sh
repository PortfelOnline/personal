#!/bin/bash
# Stop hook: save session patterns to memory + knowledge graph
# This runs at session end — quick and non-blocking

SESSION_ID=$(date -u +"%Y%m%d-%H%M%S")

# 1. Graphify: save session patterns to knowledge graph
if command -v graphify &>/dev/null; then
  REPO=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$REPO" ] && [ -f "$REPO/graphify-out/graph.json" ]; then
    graphify learn "$REPO" --session-id "$SESSION_ID" --quiet 2>/dev/null &
  fi
fi

# 2. Cross-session pattern auto-indexing (#8)
# Extract patterns from the most recent session transcript
PY_SCRIPT="$HOME/.claude/scripts/save-session-memory.py"
TRANSCRIPT_DIR="$HOME/.claude/projects/-Users-evgenijgrudev"

if [ -f "$PY_SCRIPT" ] && [ -d "$TRANSCRIPT_DIR" ]; then
  LATEST_TRANSCRIPT=$(ls -t "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | head -1)
  if [ -n "$LATEST_TRANSCRIPT" ]; then
    python3 "$PY_SCRIPT" "$LATEST_TRANSCRIPT" --goodmem 2>/dev/null &
  fi
fi

exit 0
