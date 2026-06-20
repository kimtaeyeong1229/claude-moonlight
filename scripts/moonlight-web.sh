#!/usr/bin/env bash
# Web-mode launcher (Linux / macOS fallback): bring the stack up on-demand,
# then open the dashboard in the default browser. (macOS users normally use the
# native app instead — see scripts/make-app.sh.)
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export PROJECT_DIR
URL="http://127.0.0.1:${DASHBOARD_PORT:-8090}"

# ensure-up.sh: starts the host worker + container, prints READY/ERR:* when done.
result="$(bash "$PROJECT_DIR/scripts/ensure-up.sh" | tail -1)"
if [ "$result" != "READY" ]; then
  echo "Moonlight 시작 실패: ${result}" >&2
  echo "Docker 가 실행 중인지, Claude CLI 로그인이 되어 있는지 확인하세요." >&2
  exit 1
fi

case "$(uname -s)" in
  Darwin) open "$URL" ;;
  *) xdg-open "$URL" 2>/dev/null || sensible-browser "$URL" 2>/dev/null \
       || x-www-browser "$URL" 2>/dev/null || echo "브라우저에서 다음 주소를 여세요: $URL" ;;
esac
