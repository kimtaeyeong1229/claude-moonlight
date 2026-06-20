#!/usr/bin/env bash
# Explicitly stop the Moonlight container (on-demand model: nothing runs at boot).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PROJECT_DIR"
pkill -f "claude-moonlight/app/worker.py" 2>/dev/null && echo "호스트 워커 정지" || true
docker compose down
echo "🌙 Moonlight 컨테이너를 정지했습니다."
