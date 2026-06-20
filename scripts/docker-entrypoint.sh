#!/usr/bin/env bash
# Container entrypoint. By default the translation worker runs on the HOST (where
# the user's Claude CLI is authenticated and runs non-root), so the container
# normally serves only the dashboard. Set RUN_WORKER=1 to also run the worker
# inside the container (requires an authenticated, non-root claude in the image).
set -e
cd /app

trap 'kill 0 2>/dev/null' TERM INT

if [ "${RUN_WORKER:-0}" = "1" ]; then
  export WORKER_REQUEUE="${WORKER_REQUEUE:-1}"
  echo "[entrypoint] starting in-container worker (interactive claude, PTY) …"
  python3 worker.py &
fi

echo "[entrypoint] starting Moonlight dashboard on :${DASHBOARD_PORT:-8090} …"
exec python3 server.py
