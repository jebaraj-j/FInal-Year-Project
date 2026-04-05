@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Create it first with: py -3.9 -m venv .venv
  pause
  exit /b 1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
  echo.
  echo [ERROR] App failed to start.
  echo [INFO] Install dependencies with:
  echo        .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
