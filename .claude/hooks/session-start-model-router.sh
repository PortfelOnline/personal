#!/bin/bash
# ============================================================
# Session-start Auto Router — выбирает оптимальную модель
# ============================================================
# Читает первый запрос пользователя и определяет сложность:
# - simple → deepseek-v4-flash (3€/мес, быстро)
# - medium → claude-sonnet (оптимальный баланс)
# - complex → claude-opus (архитектура, сложные баги)
# - draft → claude-haiku (быстрые черновики)
#
# Переопределяет ~/.claude/settings.json → model

SESSION_ID="$1"
PROMPT_FILE="${2:-/dev/null}"

# Читаем первый запрос (если передан файлом)
USER_PROMPT=""
if [ -f "$PROMPT_FILE" ] && [ -s "$PROMPT_FILE" ]; then
  USER_PROMPT=$(cat "$PROMPT_FILE" 2>/dev/null | head -c 4000)
fi

# Если нет файла — пропускаем (используем текущую модель)
if [ -z "$USER_PROMPT" ]; then
  exit 0
fi

# === Анализ сложности ===
# Ключевые маркеры сложных задач
COMPLEX_MARKERS="архитектур|architecture|рефактор|refactor|security|безопасност|migration|миграц|design pattern|паттерн|database schema|DDL|concurrency|race condition|performance profile|оптимизац.*глубок|memory leak|deadlock"
MEDIUM_MARKERS="bug|баг|fix|исправ|feature|фич|implement|реализовать|test|тест|review|обзор|deploy|debug|отлад"
SIMPLE_MARKERS="как дела|what.*new|git.*status|какие файлы|ls|list|read|покажи|show|explain.*simple|объясни|что такое|спроси"

COMPLEXITY="medium"  # default
REASON=""

# Подсчитываем сигналы
COMPLEX_SCORE=0
MEDIUM_SCORE=0
SIMPLE_SCORE=0

for marker in $(echo "$COMPLEX_MARKERS" | tr '|' ' '); do
  if echo "$USER_PROMPT" | grep -qi "$marker" 2>/dev/null; then
    COMPLEX_SCORE=$((COMPLEX_SCORE + 1))
  fi
done

for marker in $(echo "$MEDIUM_MARKERS" | tr '|' ' '); do
  if echo "$USER_PROMPT" | grep -qi "$marker" 2>/dev/null; then
    MEDIUM_SCORE=$((MEDIUM_SCORE + 1))
  fi
done

for marker in $(echo "$SIMPLE_MARKERS" | tr '|' ' '); do
  if echo "$USER_PROMPT" | grep -qi "$marker" 2>/dev/null; then
    SIMPLE_SCORE=$((SIMPLE_SCORE + 1))
  fi
done

# === Дополнительные эвристики ===
PROMPT_LEN=$(echo "$USER_PROMPT" | wc -c)
WORDS=$(echo "$USER_PROMPT" | wc -w | tr -d ' ')

# Длинный запрос → сложная задача
if [ "$PROMPT_LEN" -gt 2000 ]; then
  COMPLEX_SCORE=$((COMPLEX_SCORE + 3))
elif [ "$PROMPT_LEN" -gt 800 ]; then
  MEDIUM_SCORE=$((MEDIUM_SCORE + 2))
elif [ "$PROMPT_LEN" -lt 100 ]; then
  SIMPLE_SCORE=$((SIMPLE_SCORE + 2))
fi

# Многословный запрос → сложнее
if [ "$WORDS" -gt 200 ] 2>/dev/null; then
  COMPLEX_SCORE=$((COMPLEX_SCORE + 2))
fi

# === Выбор модели ===
SELECTED_MODEL=""

if [ "$COMPLEX_SCORE" -ge 3 ]; then
  SELECTED_MODEL="claude-opus-4-7"
  REASON="complex ($COMPLEX_SCORE signals: архитектура/рефакторинг/миграция)"
elif [ "$MEDIUM_SCORE" -ge 3 ]; then
  SELECTED_MODEL="claude-sonnet-4-20250514"
  REASON="medium ($MEDIUM_SCORE signals: баги/фичи/деплой)"
elif [ "$SIMPLE_SCORE" -ge 3 ]; then
  SELECTED_MODEL="deepseek-v4-flash"
  REASON="simple ($SIMPLE_SCORE signals: быстрые вопросы, просмотр)"
else
  # По умолчанию: смотрим длину
  if [ "$PROMPT_LEN" -gt 2000 ]; then
    SELECTED_MODEL="claude-sonnet-4-20250514"
    REASON="medium (long prompt: $WORDS words)"
  elif [ "$PROMPT_LEN" -lt 200 ]; then
    SELECTED_MODEL="deepseek-v4-flash"
    REASON="simple (short prompt: $WORDS words)"
  else
    SELECTED_MODEL="claude-sonnet-4-20250514"
    REASON="medium (default)"
  fi
fi

# === Применяем модель ===
CURRENT_MODEL=$(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(d.get('model','unknown'))" 2>/dev/null)

if [ "$CURRENT_MODEL" != "$SELECTED_MODEL" ]; then
  # Переключение через claude config
  command claude config set model "$SELECTED_MODEL" 2>/dev/null && \
    echo "[auto-router] Model: $CURRENT_MODEL → $SELECTED_MODEL ($REASON)" >&2 || \
    echo "[auto-router] WARNING: could not switch model to $SELECTED_MODEL" >&2
else
  echo "[auto-router] Model stays: $CURRENT_MODEL ($REASON)" >&2
fi

# Лог для аудита
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | model=$SELECTED_MODEL | reason=$REASON | prompt_len=$PROMPT_LEN | words=$WORDS" >> ~/.claude/logs/model-router.log 2>/dev/null || true

exit 0
