@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Gerador de QR Code Dinamico
echo ============================================
echo.

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo Usando: %PYTHON%
echo.
echo Iniciando o servidor em http://localhost:5000
echo (Para outros computadores da rede acessarem, use o IP desta maquina - veja o README.md)
echo Para parar o servidor, feche esta janela ou pressione CTRL+C.
echo.

%PYTHON% app.py

echo.
echo O servidor foi encerrado.
pause
