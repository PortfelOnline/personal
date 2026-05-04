#!/bin/bash
# Graceful restart ds-proxy: старт на новом порту, переключение URL, kill старого
# Никогда не роняет работающее соединение.

NEW_PORT="${1:-8099}"
OLD_PORT=$(lsof -ti:8099 2>/dev/null | head -1 | xargs -I{} sh -c 'lsof -p {} -i -P -n 2>/dev/null | grep LISTEN | awk "{print \$9}" | sed "s/.*://"')

if [ -n "$OLD_PORT" ] && [ "$OLD_PORT" = "$NEW_PORT" ]; then
  # Если нужно перезапустить на том же порту — стартуем на соседнем, потом свапаем
  NEW_PORT=$((NEW_PORT + 1))
fi

echo "[restart] Starting on :$NEW_PORT → will swap to :$OLD_PORT"
nohup python3 ~/personal/claude-code-setup/ds-proxy.py --port "$NEW_PORT" >/tmp/ds-proxy-$NEW_PORT.log 2>&1 &
NEW_PID=$!
sleep 3

if ! kill -0 "$NEW_PID" 2>/dev/null; then
  echo "[restart] FAILED to start on :$NEW_PORT"
  tail -5 /tmp/ds-proxy-$NEW_PORT.log
  exit 1
fi

echo "[restart] Started PID $NEW_PID on :$NEW_PORT"

# Если был старый — обновляем ANTHROPIC_BASE_URL ссылку (файл для подгрузки)
echo "http://localhost:$NEW_PORT" >/tmp/anthropic_base_url

# Kill старого, если был
if [ -n "$OLD_PORT" ] && [ "$OLD_PORT" != "$NEW_PORT" ]; then
  OLD_PID=$(lsof -ti:"$OLD_PORT" 2>/dev/null)
  if [ -n "$OLD_PID" ]; then
    echo "[restart] Killing old PID $OLD_PID on :$OLD_PORT"
    kill "$OLD_PID" 2>/dev/null
    # Если нужно на старом порту — рестартуем
    if [ "$1" = "8099" ]; then
      sleep 1
      nohup python3 ~/personal/claude-code-setup/ds-proxy.py --port 8099 >/tmp/ds-proxy.log 2>&1 &
      echo "[restart] Re-started on :8099 PID $!"
      kill "$NEW_PID" 2>/dev/null
    fi
  fi
fi

echo "[restart] Done"
