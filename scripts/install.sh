#!/usr/bin/env bash
# Moonlight installer — OS-aware.
#   macOS         → build the native app (/Applications/claude-moonlight.app)
#   Linux         → web mode: a launcher + .desktop entry that opens the browser
#   Windows (git-bash/WSL) → web mode via scripts/moonlight-web.bat
#
# In all cases the backend runs in Docker (server) + a host worker (translation,
# needs an authenticated Claude CLI). See plans/v0.4.md §1.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OS="$(uname -s)"

echo "🌙 Moonlight 설치 — 감지된 OS: ${OS}"

case "$OS" in
  Darwin)
    echo "→ macOS: 네이티브 앱을 빌드합니다."
    bash "$PROJECT_DIR/scripts/make-app.sh"
    echo
    echo "✅ 완료. /Applications/claude-moonlight.app 를 더블클릭하세요."
    ;;

  Linux)
    echo "→ Linux: 웹 모드(브라우저) 로 설치합니다."
    chmod +x "$PROJECT_DIR/scripts/moonlight-web.sh"
    APPS="$HOME/.local/share/applications"
    mkdir -p "$APPS"
    cat > "$APPS/claude-moonlight.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Moonlight
Comment=arXiv 논문 한국어 2단 대조 리더
Exec=/bin/bash "$PROJECT_DIR/scripts/moonlight-web.sh"
Terminal=false
Categories=Education;Office;
EOF
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
    echo
    echo "✅ 완료. 앱 메뉴의 'Moonlight' 또는 아래 명령으로 실행:"
    echo "     bash $PROJECT_DIR/scripts/moonlight-web.sh"
    echo "   (전제: Docker 실행 중 + Claude CLI 로그인)"
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "→ Windows: 웹 모드로 실행합니다."
    echo "   scripts\\moonlight-web.bat 을 더블클릭하거나 실행하세요 (컨테이너 기동 + 브라우저)."
    echo "   ⚠️  번역 워커(PTY)는 POSIX 전용이라 Windows 호스트에서는 동작하지 않습니다."
    echo "      → 번역까지 쓰려면 WSL2 에서 이 install.sh 를 Linux 로 실행하는 것을 권장합니다."
    ;;

  *)
    echo "지원하지 않는 OS: ${OS} (macOS/Linux/Windows 만 지원)"; exit 1 ;;
esac
