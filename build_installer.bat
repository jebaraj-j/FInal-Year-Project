@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   G-Vox - Build Windows Installer
echo ============================================
echo.

if not exist "dist\G-Vox\G-Vox.exe" (
  echo [INFO] App build not found. Building EXE first...
  call build_exe.bat
  if errorlevel 1 exit /b 1
)

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "%ISCC%" (
  echo [ERROR] Inno Setup not found.
  echo [INFO] Install Inno Setup 6 from:
  echo        https://jrsoftware.org/isinfo.php
  echo [INFO] Then run this file again.
  pause
  exit /b 1
)

if not exist installer (
  mkdir installer
)

"%ISCC%" "installer\G-Vox.iss"
if errorlevel 1 (
  echo.
  echo [ERROR] Installer build failed.
  pause
  exit /b 1
)

echo.
echo Installer created:
echo   dist_installer\G-Vox-Setup.exe
echo.
pause
