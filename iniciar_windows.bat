@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo O ambiente ainda nao foi instalado.
  echo Execute primeiro: instalar_windows.bat
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python server.py
pause
