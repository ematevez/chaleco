@echo off
:: Cambiar a la carpeta del script
cd /d "C:\Users\Lgistica\Desktop\chaleco\Unico\unico_6.py"
:: Verificar si venv existe, si no, crear un entorno virtual
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
)

:: Activar el entorno virtual
call venv\Scripts\activate

:: Instalar las dependencias
pip install -r requirements.txt

:: Ejecutar el programa
python unico_6.py

:: Desactivar el entorno virtual
deactivate

:: Pausar la ventana al finalizar
pause
