@echo off
setlocal
cd /d "%~dp0"
if exist "AgateRemote.exe" (
  start "" "AgateRemote.exe"
  exit /b 0
)
if not exist ".venv\Scripts\pythonw.exe" (
  echo Execute instalar_windows.bat primeiro.
  pause
  exit /b 1
)
start "Agate Remote" .venv\Scripts\pythonw.exe server.py
