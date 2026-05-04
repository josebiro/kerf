#!/usr/bin/env bash
set -euo pipefail

shutdown() {
    trap - TERM INT
    [[ -n "${UVICORN_PID:-}" ]] && kill -TERM "$UVICORN_PID" 2>/dev/null || true
    [[ -n "${NODE_PID:-}"    ]] && kill -TERM "$NODE_PID"    2>/dev/null || true
    [[ -n "${CADDY_PID:-}"   ]] && kill -TERM "$CADDY_PID"   2>/dev/null || true
    wait
}
trap shutdown TERM INT

cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8001 &
UVICORN_PID=$!

cd /app/frontend
PORT=3000 HOST=127.0.0.1 ORIGIN="${ORIGIN:-http://localhost:8000}" node build &
NODE_PID=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Exit if any supervised process dies
wait -n
EXIT_CODE=$?
shutdown
exit "$EXIT_CODE"
