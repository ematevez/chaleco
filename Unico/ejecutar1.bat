@echo off
:: Cambiar a la carpeta del script
cd /d "C:\Users\Lgistica\Desktop\chaleco\Unico\unico_6.py"

:: Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no está instalado. Por favor, instálalo antes de continuar.
    pause
    exit /b
)

:: Instalar las dependencias del archivo requirements.txt
echo Instalando dependencias...
pip install -r requirements.txt

:: Ejecutar el programa
echo Ejecutando el programa...
python unico_6.py

:: Pausar la ventana al finalizar
pause
