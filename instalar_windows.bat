@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo Instalacao do Agate Remote
echo ==============================================

where py >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado.
  echo Instale o Python 3.11 ou superior e marque Add Python to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :erro
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :erro
pip install -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo Instalacao concluida. Iniciando o servidor...
python server.py
pause
exit /b 0

:erro
echo.
echo A instalacao falhou. Confira a mensagem acima.
pause
exit /b 1
