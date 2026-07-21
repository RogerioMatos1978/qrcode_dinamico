@echo off
echo ============================================
echo   IP desta maquina na rede local
echo ============================================
echo.
echo Procure a linha "IPv4 Address" (ou "Endereco IPv4") abaixo.
echo Esse numero (ex: 192.168.0.10) e o que voce vai usar no BASE_URL
echo do arquivo .env, no formato: http://SEU_IP:5000
echo.
ipconfig | findstr /i "IPv4"
echo.
pause
