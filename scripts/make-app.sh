#!/usr/bin/env bash
# Build /Applications/claude-moonlight.app — double-clicking it brings the
# Moonlight container up on-demand and opens the viewer (see moonlight-launch.sh).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="claude-moonlight"
APP="${1:-/Applications}/${APP_NAME}.app"
PORT="${DASHBOARD_PORT:-8090}"
APP_URL="http://127.0.0.1:${PORT}"

command -v swiftc >/dev/null 2>&1 || { echo "swiftc 가 필요합니다 (xcode-select --install)"; exit 1; }

echo "→ building ${APP}"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# --- compile the native WKWebView shell (real app window, not a browser) ---
SRC="$(mktemp -d)/MoonlightApp.swift"
sed -e "s#__PROJECT_DIR__#${PROJECT_DIR}#g" -e "s#__APP_URL__#${APP_URL}#g" \
    "${PROJECT_DIR}/app/native/MoonlightApp.swift" > "$SRC"
swiftc -O -framework Cocoa -framework WebKit "$SRC" -o "$APP/Contents/MacOS/${APP_NAME}"
chmod +x "$APP/Contents/MacOS/${APP_NAME}"

# Info.plist
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key><string>Moonlight</string>
  <key>CFBundleIdentifier</key><string>com.moonlight.reader</string>
  <key>CFBundleVersion</key><string>0.3</string>
  <key>CFBundleShortVersionString</key><string>0.3</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>${APP_NAME}</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><false/>
  <!-- WKWebView blocks plain HTTP by default; allow loopback to the local server. -->
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST

# Simple generated icon (🌙 on dark) if iconutil/sips available; otherwise skip.
if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  TMP="$(mktemp -d)"; ICON_PNG="$TMP/icon.png"
  cat > "$TMP/icon.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">
  <rect width="1024" height="1024" rx="220" fill="#16181c"/>
  <circle cx="560" cy="470" r="250" fill="#f4e9c1"/>
  <circle cx="660" cy="400" r="250" fill="#16181c"/>
  <text x="512" y="880" font-size="120" fill="#4caf50" text-anchor="middle" font-family="Helvetica" font-weight="bold">Moonlight</text>
</svg>
SVG
  if command -v rsvg-convert >/dev/null 2>&1; then rsvg-convert -w 1024 -h 1024 "$TMP/icon.svg" -o "$ICON_PNG"
  elif command -v qlmanage >/dev/null 2>&1; then qlmanage -t -s 1024 -o "$TMP" "$TMP/icon.svg" >/dev/null 2>&1 && mv "$TMP/icon.svg.png" "$ICON_PNG" 2>/dev/null || true
  fi
  if [ -f "$ICON_PNG" ]; then
    ICONSET="$TMP/icon.iconset"; mkdir -p "$ICONSET"
    for s in 16 32 64 128 256 512; do
      sips -z $s $s "$ICON_PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null 2>&1 || true
      d=$((s*2)); sips -z $d $d "$ICON_PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1 || true
    done
    iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP"
fi

echo "✅ created ${APP}"
echo "   더블클릭하면 컨테이너가 자동 기동되고 뷰어가 열립니다."
