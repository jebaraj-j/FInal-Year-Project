@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   G-Vox - Build Standalone Windows App
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found.
  echo [INFO] Create it with: py -3.9 -m venv .venv
  pause
  exit /b 1
)

set "PYTHON=.venv\Scripts\python.exe"
set "PYINSTALLER=.venv\Scripts\pyinstaller.exe"

echo [1/4] Installing/Updating build tools...
"%PYTHON%" -m pip install --upgrade pip >nul
"%PYTHON%" -m pip install pyinstaller >nul

echo [2/4] Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "G-Vox.spec" del /q "G-Vox.spec"

echo [3/4] Building G-Vox.exe (windowed, no terminal)...
"%PYINSTALLER%" ^
  --noconfirm ^
  --clean ^
  --name "G-Vox" ^
  --windowed ^
  --onedir ^
  --add-data "gesture;gesture" ^
  --add-data "voice_assistant;voice_assistant" ^
  --add-data "extensions;extensions" ^
  --add-data "controller;controller" ^
  --add-data "ui;ui" ^
  --hidden-import PyQt5 ^
  --hidden-import cv2 ^
  --hidden-import mediapipe ^
  --hidden-import numpy ^
  --hidden-import pyautogui ^
  --hidden-import pyaudio ^
  --hidden-import vosk ^
  --hidden-import pyttsx3 ^
  --hidden-import speech_recognition ^
  --hidden-import screen_brightness_control ^
  --hidden-import pycaw ^
  --hidden-import comtypes ^
  --hidden-import fuzzywuzzy ^
  --collect-all vosk ^
  --collect-all pyaudio ^
  main.py

if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. Check errors above.
  pause
  exit /b 1
)

echo [4/4] Build complete.
echo.
echo EXE:
echo   dist\G-Vox\G-Vox.exe
echo.
echo Double-click G-Vox.exe to run without terminal.
echo.
pause
