@echo off
cd /d "C:\BOT_APUESTAS_PRO\Bet_Pro_Futbol"
title SINCRONIZADOR PREDI-GOL PRO
color 0B

echo ===========================================
echo       ACTUALIZANDO WEB
echo ===========================================
echo.

:: Ejecuta el script que organiza y sube todo
python Sincronizar_Nube.py

echo.
echo [INFO] Ya puedes cerrar esta ventana y apagar tu PC.
echo [INFO] La web seguira funcionando en tu celular.
pause