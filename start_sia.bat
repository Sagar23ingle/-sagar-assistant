@echo off
title SIA - Sagar's AI Assistant
echo =======================================================
echo          STARTING SIA - SAGAR'S AI ASSISTANT
echo =======================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run install_sia.bat first.
    pause
    exit /b 1
)

echo [*] Activating local Python environment...
call .venv\Scripts\activate.bat

echo [*] Launching SIA Core Server on http://127.0.0.1:8000...
start "" http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
