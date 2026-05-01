#!/bin/bash
# PreToolUse hook: LIVE response shaping for large tool outputs
# Прочитает файл сам и отдаст модели сжатую версию — tool НЕ выполняется.
# Эффект: большие Read → модель видит ~800b вместо 5000-50000b
#
# Logika:
# 1. Если Read с большим limit или без limit → читаем сами, режем, exit 1
# 2. Модель видит [LIVE_SUMMARIZED] в stderr — как cache hit, но ДО кэша
# 3. response-cache-save.sh потом сохранит уже сжатую версию

STATE_DIR="/tmp/claude_antiloop"
mkdir -p "$STATE_DIR"

TOOL=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool',''))" 2>/dev/null)
TOOL_INPUT=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{})))" 2>/dev/null)

# === Параметры ===
MAX_LINES=60        # если > 60 строк → режем
MAX_BYTES=2000      # если оценка > 2000b → режем
TARGET_LINES=20     # показываем 20 строк
TARGET_BYTES=800    # ~800b

# === SHAPING для Read ===
if [ "$TOOL" = "Read" ]; then
  FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_path',''))" 2>/dev/null)
  OFFSET=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('offset',0))" 2>/dev/null || echo 0)
  LIMIT=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('limit',0))" 2>/dev/null || echo 0)

  [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ] && exit 0

  TOTAL_LINES=$(wc -l < "$FILE_PATH" 2>/dev/null || echo 0)
  [ "$TOTAL_LINES" -le 0 ] && exit 0

  # Реальный лимит: если limit=0 или не указан — читаем всё с offset
  if [ "$LIMIT" -le 0 ] || [ "$LIMIT" -gt "$((TOTAL_LINES - OFFSET))" ]; then
    EFFECTIVE_LINES=$((TOTAL_LINES - OFFSET))
  else
    EFFECTIVE_LINES=$LIMIT
  fi

  # === SEARCH ROUTING: grep first для поисковых задач ===
  # Не запрещаем Read, а требуем grep как первый шаг перед Read
  PROMPT=$(cat /tmp/claude_antiloop/current_prompt 2>/dev/null || echo "")
  SEARCH_KEYWORDS="find|search|where is|locate|найди|где |поиск|ищи"
  if echo "$PROMPT" | grep -qiE "$SEARCH_KEYWORDS"; then
    STEP=$(cat /tmp/claude_antiloop/step_count 2>/dev/null || echo 0)
    # Первый шаг + Read + ещё не было grep → блок
    if [ "$STEP" -le 1 ]; then
      GREP_DONE=$(tail -5 /tmp/claude_antiloop/tools_log 2>/dev/null | grep -c -i "grep")
      if [ "$GREP_DONE" -eq 0 ]; then
        echo "[SEARCH_ROUTING: первый шаг — используй grep, потом Read]" >&2
        echo "[HINT: Bash(grep -rn 'keyword' .) прицельно, потом Read с offset/limit]" >&2
        exit 1
      fi
    fi
  fi

  [ "$EFFECTIVE_LINES" -le "$MAX_LINES" ] && exit 0

  # === Live shaping: читаем сами и отдаём сжатую версию ===
  {
    echo "[LIVE_SUMMARIZED_FROM_${EFFECTIVE_LINES}_LINES]"
    echo "[PARTIAL_FILE_DO_NOT_ASSUME_COMPLETE]"
    sed -n "$((OFFSET + 1)),$((OFFSET + TARGET_LINES))p" "$FILE_PATH" 2>/dev/null
    echo "..."
    echo "[LIVE_SUMMARIZED: ${EFFECTIVE_LINES} lines → ${TARGET_LINES} lines]"
    echo "[HINT: используй offset/limit или grep для таргетного чтения]"
  } >&2

  # Помечаем что shaping был применён — response-cache-save не сохранит результат
  echo "shaped" > "$STATE_DIR/live_shaped"

  exit 1  # блокируем реальный tool → модель видит только stderr
fi

# === SHAPING для Bash(крупные команды без пайпа) ===
# Если Bash команда выглядит как "тяжёлая" и не имеет ограничения вывода
if echo "$TOOL" | grep -qE "^Bash$"; then
  COMMAND=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null)

  # Проверяем curl/wget без head/cut/grep в конце
  if echo "$COMMAND" | grep -qE "curl|wget" && ! echo "$COMMAND" | grep -qE "\|.*(head|cut|grep -o|tail|wc|sed)"; then
    # Не блокируем, но пишем предупреждение
    echo "[LIVE_SUMMARIZED_WARN: curl/wget без pipe|head — результат может быть большим]"
    echo "[LIVE_SUMMARIZED: добавь | head -c 2000 чтобы сократить]"
    echo "[LIVE_SUMMARIZED: PROCEEDING]"
  fi >&2
fi

exit 0
