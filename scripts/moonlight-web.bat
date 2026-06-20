@echo off
REM Moonlight web-mode launcher for Windows: start the container and open the
REM dashboard in the default browser.
REM NOTE: the translation worker uses POSIX PTY/fork and does NOT run on Windows
REM hosts. For translation, run scripts/install.sh inside WSL2 (Linux) instead.
cd /d "%~dp0\.."
echo Starting Moonlight container...
docker compose up -d
if errorlevel 1 (
  echo Docker compose failed. Is Docker Desktop running?
  pause
  exit /b 1
)
echo Waiting for the server...
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:8090"
echo Opened http://127.0.0.1:8090
