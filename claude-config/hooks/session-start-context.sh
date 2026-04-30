#!/bin/bash
# SessionStart hook: provide context about available tools and repo state
# stdout: JSON with systemMessage or hookSpecificOutput.additionalContext

REPO=$(git rev-parse --show-toplevel 2>/dev/null)
REPO_NAME=$(basename "$REPO" 2>/dev/null)

CONTEXT=""

# Graphify status
if [ -n "$REPO" ] && [ -f "$REPO/graphify-out/GRAPH_REPORT.md" ]; then
  GOD_COUNT=$(grep -c '^## ' "$REPO/graphify-out/GRAPH_REPORT.md" 2>/dev/null || echo 0)
  CONTEXT="$CONTEXT\n📊 Graphify: $GOD_COUNT god nodes in $REPO_NAME"
fi

# Recent git activity
if [ -n "$REPO" ]; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  LAST_COMMIT=$(git log -1 --format="%h %s" 2>/dev/null | cut -c1-80)
  CONTEXT="$CONTEXT\n📝 Git: $BRANCH | $LAST_COMMIT"
fi

if [ -n "$CONTEXT" ]; then
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"Session context:$CONTEXT\"}}"
fi

exit 0
