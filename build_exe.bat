@echo off
title GestureVox — PyInstaller Build

echo ============================================
echo   GestureVox — Building Standalone EXE
echo ============================================
echo.

cd /d e:\projectnew

:: Install PyInstaller if not present
pip install pyinstaller --quiet

:: Build the executable
pyinstaller ^
  --name GestureVox ^
  --onefile ^
  --windowed ^
  --add-data "gesture;gesture" ^
  --add-data "voice_assistant;voice_assistant" ^
  --add-data "extensions;extensions" ^
  --add-data "controller;controller" ^
  --add-data "ui;ui" ^
  --hidden-import PyQt5 ^
  --hidden-import mediapipe ^
  --hidden-import cv2 ^
  --hidden-import pyautogui ^
  --hidden-import vosk ^
  --hidden-import pyttsx3 ^
  main.py

echo.
echo ============================================
if exist dist\GestureVox.exe (
  echo   BUILD SUCCESS!
  echo   EXE location: dist\GestureVox.exe
) else (
  echo   BUILD FAILED — check errors above
)
echo ============================================
pause
