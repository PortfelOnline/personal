#!/bin/bash
# validate-agents.sh — PostToolUse hook for agent .md files (#35)
# Runs validate-agents.py on changed agent files, surfaces warnings.
# Non-blocking: always exits 0 (warnings only, shown as systemMessage).

set -o pipefail

FILE=$(jq -r '.tool_response.filePath // .tool_input.file_path // ""' 2>/dev/null)

# Only trigger for agent .md files (not shared/, notes/, docs/, etc.)
case "$FILE" in
  */".claude/agents/"*)
    # Skip non-agent directories
    case "$FILE" in
      */shared/*|*/notes/*|*/docs/*|*/scripts/*|*/graphify-out/*) exit 0 ;;
    esac
    ;;
  *) exit 0 ;;
esac

# Run validator on changed files
RESULT=$(python3 ~/.claude/scripts/validate-agents.py --changed --json 2>/dev/null)
STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','ok'))" 2>/dev/null || echo "ok")

if [ "$STATUS" = "fail" ]; then
  ERRORS=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('errors',[])))" 2>/dev/null || echo "0")
  WARNS=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('warnings',[])))" 2>/dev/null || echo "0")
  echo "{\"systemMessage\": \"Agent validation: ${ERRORS} errors, ${WARNS} warnings in ${FILE##*/}\", \"continue\": true}"
elif [ "$STATUS" = "warn" ]; then
  WARNS=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('warnings',[])))" 2>/dev/null || echo "0")
  echo "{\"systemMessage\": \"Agent validation: ${WARNS} warnings in ${FILE##*/}\", \"continue\": true}"
fi

exit 0
