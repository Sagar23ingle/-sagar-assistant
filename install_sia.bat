@echo off
title SIA Setup & Installer
echo =======================================================
echo              SIA ONE-CLICK SETUP & INSTALLER
echo =======================================================
echo.

cd /d "%~dp0"

echo [*] Checking uv package manager...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing standalone uv manager...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo [*] Provisioning Python 3.11 standalone...
uv python install 3.11

echo [*] Setting up virtual environment...
uv venv .venv --python 3.11

echo [*] Installing core dependencies...
uv pip install -r requirements.txt --python .venv\Scripts\python.exe

echo [*] Running SIA Diagnostics...
call .venv\Scripts\activate.bat
python scripts\diagnose.py

echo.
echo =======================================================
echo [SUCCESS] SIA is fully installed and ready to run!
echo Double click start_sia.bat to launch SIA.
echo =======================================================
pause
