#!/bin/bash
# Graceful restart ds-proxy.
# Приоритет: POST /reload (in-place, zero-downtime) → fallback kill+start
# Все терминалы подхватывают через общий прокси на :8099

PORT="${1:-8099}"
PID=$(lsof -ti:"$PORT" 2>/dev/null | head -1)

if [ -n "$PID" ]; then
  echo "[restart] Sending reload signal to PID $PID on :$PORT"
  reload_ok=$(curl -s -X POST "http://localhost:$PORT/reload" 2>/dev/null)
  if [ -n "$reload_ok" ]; then
    echo "[restart] $reload_ok"
    sleep 2
    # Verify it's back up
    if lsof -ti:"$PORT" >/dev/null 2>&1; then
      echo "[restart] OK — proxy reloaded on :$PORT"
      exit 0
    fi
  fi
  echo "[restart] Reload failed, falling back to kill+start"
  kill "$PID" 2>/dev/null
  sleep 1
fi

nohup python3 ~/personal/claude-code-setup/ds-proxy.py --port "$PORT" >/tmp/ds-proxy.log 2>&1 &
NEW_PID=$!
sleep 2

if kill -0 "$NEW_PID" 2>/dev/null; then
  echo "[restart] Started PID $NEW_PID on :$PORT"
else
  echo "[restart] FAILED to start on :$PORT"
  tail -5 /tmp/ds-proxy.log
  exit 1
fi
