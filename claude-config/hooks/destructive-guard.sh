#!/bin/bash
# PreToolUse guard: ask before destructive Bash commands
# stdin: JSON with tool_input.command

CMD=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Check for destructive patterns
if echo "$CMD" | grep -qE 'rm -rf|sudo |chmod 777|chown -R|> /dev/sd|dd if=|mkfs\.|:(){ :|:& };:'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Destructive command detected. Confirm execution."}}'
  exit 0
fi

exit 0
