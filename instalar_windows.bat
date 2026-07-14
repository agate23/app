@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 ou superior nao foi encontrado.
  echo Baixe em https://www.python.org/downloads/windows/ e marque Add Python to PATH.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto erro
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto erro
start "Agate Remote" .venv\Scripts\pythonw.exe server.py
echo Agate Remote instalado e iniciado.
exit /b 0
:erro
echo Nao foi possivel instalar o Agate Remote.
pause
exit /b 1
