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
".venv\Scripts\python.exe" system_launcher.py
