#!/bin/bash
# PreToolUse guard: verify file exists before Edit/Write
# stdin: JSON with tool_input.file_path

FILE=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [ -n "$FILE" ] && [ ! -f "$FILE" ] && [ ! -d "$(dirname "$FILE")" ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Target directory does not exist: '"$FILE"'"}}'
  exit 0
fi

# File doesn't exist but directory does — likely a Write (create) not Edit
# Allow it through
exit 0
