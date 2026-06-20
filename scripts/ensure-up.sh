#!/usr/bin/env bash
# Bring the Moonlight container up on-demand and return only when healthy.
# Used by the native macOS app (no browser). Prints READY or ERR:<reason>.
set -uo pipefail

# macOS GUI apps launch with a minimal PATH; restore docker's location.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
[ -x /Applications/Docker.app/Contents/Resources/bin/docker ] && \
  export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
PORT="${DASHBOARD_PORT:-8090}"
URL="http://127.0.0.1:${PORT}"
cd "$PROJECT_DIR"

# Start the translation worker on the HOST (uses the user's authenticated,
# non-root claude). Idempotent — only starts if not already running.
start_host_worker() {
  pgrep -f "claude-moonlight/app/worker.py" >/dev/null 2>&1 && return 0
  command -v pdftoppm >/dev/null 2>&1 || \
    echo "WARN: poppler(pdftoppm) 없음 — 그림 추출이 제한됩니다 (brew install poppler)" >&2
  local PY="$PROJECT_DIR/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
  MOONLIGHT_DATA="$PROJECT_DIR/data" \
  CLAUDE_CMD="$(command -v claude || echo claude)" \
  WORKER_CWD="$PROJECT_DIR/app" \
  WORKER_MODEL="${WORKER_MODEL:-claude-opus-4-8}" \
  WORKER_EFFORT="${WORKER_EFFORT:-high}" \
  WORKER_CONCURRENCY="${WORKER_CONCURRENCY:-2}" \
  nohup "$PY" "$PROJECT_DIR/app/worker.py" >> "$PROJECT_DIR/data/worker-host.log" 2>&1 &
}

command -v docker >/dev/null 2>&1 || { echo "ERR:NO_DOCKER"; exit 1; }

if ! docker info >/dev/null 2>&1; then
  open -a Docker 2>/dev/null || true
  for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 2; done
  docker info >/dev/null 2>&1 || { echo "ERR:DOCKER_DAEMON"; exit 1; }
fi

start_host_worker   # translation engine on the host

# already healthy?
if curl -fsS -m 3 "${URL}/api/health" >/dev/null 2>&1; then echo "READY"; exit 0; fi

# bring it up (compose builds the image automatically if missing)
docker compose up -d >/dev/null 2>&1 || { echo "ERR:COMPOSE"; exit 1; }

for _ in $(seq 1 60); do
  if curl -fsS -m 3 "${URL}/api/health" >/dev/null 2>&1; then echo "READY"; exit 0; fi
  sleep 2
done
echo "ERR:TIMEOUT"; exit 1
