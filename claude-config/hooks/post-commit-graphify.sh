#!/bin/bash
# PostToolUse hook: update knowledge graph after git commit
# stdin: JSON with tool_input (Bash with git commit)

# Check if graphify is available for this project
REPO=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$REPO" ] && [ -f "$REPO/graphify-out/graph.json" ]; then
  # Update graph in background (don't block the user)
  (cd "$REPO" && graphify update . --quiet 2>/dev/null &)
fi

exit 0
