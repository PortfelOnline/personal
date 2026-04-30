#!/bin/bash
# statusLine — lock-aware git status display
# Предотвращает index.lock race condition: проверяет lock-файл перед git-операциями

input=$(cat)

d=$(echo "$input" | jq -r '.workspace.project_dir // .workspace.current_dir // empty')
[ -z "$d" ] && { printf '? | ? | 0t | OK'; exit 0; }

m=$(echo "$input" | jq -r '.model.id // empty')

# Проверяем lock-файл ПЕРЕД git-операциями — это root cause index.lock
if [ -f "$d/.git/index.lock" ]; then
    # Git занят — возвращаем кешированное значение если есть
    cache_file="/tmp/statusline-cache-$(echo "$d" | md5 -q 2>/dev/null || echo "$d" | md5sum | cut -d' ' -f1)"
    if [ -f "$cache_file" ]; then
        cat "$cache_file"
        exit 0
    fi
    printf '? | %s | ?t | ...' "${m:-?}"
    exit 0
fi

b=$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)

# Используем git diff --stat вместо status --porcelain — короче, без локов
u=$(git -C "$d" diff --stat 2>/dev/null; git -C "$d" diff --cached --stat 2>/dev/null | wc -l | tr -d ' ')

# TODO/FIXME через rg (быстрее), fallback на grep -r (без --porcelain блокировок)
if command -v rg &>/dev/null; then
    t=$(rg -l 'TODO|FIXME|HACK' "$d" --max-depth 5 2>/dev/null | wc -l | tr -d ' ')
else
    t=$(git -C "$d" grep -l -E 'TODO|FIXME|HACK' -- '*.ts' '*.tsx' '*.js' '*.py' '*.php' '*.sh' '*.css' 2>/dev/null | wc -l | tr -d ' ')
fi

[ "$u" -gt 0 ] 2>/dev/null && us="*$u" || us="OK"

result=$(printf '%s | %s | %st | %s' "${b:-?}" "${m:-?}" "${t:-0}" "$us")

# Кешируем на 2 секунды
cache_file="/tmp/statusline-cache-$(echo "$d" | md5 -q 2>/dev/null || echo "$d" | md5sum | cut -d' ' -f1)"
echo "$result" > "$cache_file"

printf '%s' "$result"
