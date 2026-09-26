@echo off
title SIA Diagnostics
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scripts\diagnose.py
echo.
pause
