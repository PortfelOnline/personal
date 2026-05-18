#!/bin/bash
# PreToolUse guard for Bash: ask before destructive / server-risky commands.
# stdin: JSON with tool_input.command
CMD=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
[ -z "$CMD" ] && exit 0

REASON=""
case "$CMD" in
  *"rm -rf "*|*"rm -fr "*)                                REASON="rm -rf";;
  *"chmod 777"*|*"chown -R "*|*"> /dev/sd"*|*"dd if="*)   REASON="filesystem destructive";;
  *"mkfs."*|*":(){ :|:& };:"*)                            REASON="filesystem destructive";;
  *"DROP TABLE"*|*"DROP DATABASE"*|*"TRUNCATE TABLE"*)    REASON="SQL destructive (DROP/TRUNCATE)";;
  *"iptables -F"*|*"iptables -X"*|*"ip6tables -F"*)       REASON="iptables flush";;
  *"git reset --hard"*|*"git push --force"*|*"git push -f"*) REASON="git destructive";;
  *"grep -rn /application/"*|*"grep -rn /application "*)  REASON="recursive grep /application/ (Zabbix-alert rule)";;
  *.bak\ /application/*|*"/application/"*.bak*)           REASON=".bak in /application/ (banned)";;
esac

[ -n "$REASON" ] && printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Server safety net: %s. Confirm before running."}}\n' "$REASON"
exit 0
