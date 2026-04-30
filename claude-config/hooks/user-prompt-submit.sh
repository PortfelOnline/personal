#!/bin/bash
# user-prompt-submit.sh — UserPromptSubmit hook (#49)
# Логирует все пользовательские промпты для аналитики и отладки.
# Сохраняет в ~/.claude/logs/prompts.log с ротацией.
# Также сохраняет в /tmp/claude_antiloop/current_prompt для adaptive MAX_STEPS.

STDIN=$(cat)
SESSION_ID=$(echo "$STDIN" | jq -r '.session_id // "unknown"' 2>/dev/null)
PROMPT=$(echo "$STDIN" | jq -r '.prompt // ""' 2>/dev/null)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/prompts.log"

# Ротация: > 2000 строк → оставить последние 1000
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 2000 ]; then
  tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

# Логируем (первые 500 символов промпта)
PROMPT_SHORT=$(echo "$PROMPT" | cut -c1-500)
echo "[$TS] [$SESSION_ID] ${PROMPT_SHORT}" >> "$LOG_FILE"

# Сохраняем промпт для adaptive MAX_STEPS и prefetch engine
mkdir -p /tmp/claude_antiloop
echo "$PROMPT" > /tmp/claude_antiloop/current_prompt
echo "$TS" > /tmp/claude_antiloop/prompt_time
# Очищаем счётчики шагов для новой сессии
echo "0" > /tmp/claude_antiloop/step_count
echo "0" > /tmp/claude_antiloop/total_calls
: > /tmp/claude_antiloop/tools_log
: > /tmp/claude_antiloop/files_log
: > /tmp/claude_antiloop/step_output_hashes

# --- Session soft reset: каждые 25 промптов очищаем кэш ---
PROMPT_COUNT_FILE="/tmp/claude_antiloop/prompt_count"
COUNT=0
if [ -f "$PROMPT_COUNT_FILE" ]; then
  COUNT=$(cat "$PROMPT_COUNT_FILE" 2>/dev/null || echo 0)
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$PROMPT_COUNT_FILE"

if [ "$COUNT" -ge 25 ]; then
  # Soft reset: очищаем кэш, но сохраняем счётчики
  rm -rf /tmp/claude_cache/
  echo "SOFT RESET: session cache cleared after ${COUNT} prompts" >> /tmp/claude_antiloop/soft_reset.log
  echo "0" > "$PROMPT_COUNT_FILE"
fi

exit 0
