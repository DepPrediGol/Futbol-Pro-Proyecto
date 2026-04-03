@echo off
TITLE ACTUALIZADOR BET PRO FUTBOL
:: Navegar a la carpeta donde reside este archivo .bat
cd /d "%~dp0"

echo ===========================================
echo       ACTUALIZANDO WEB
echo ===========================================

:: Ejecutar el script usando la ruta relativa
python Sincronizar_Nube.py

echo.
echo [INFO] Ya puedes cerrar esta ventana y apagar tu PC.
echo [INFO] La web seguira funcionando en tu celular.
pause