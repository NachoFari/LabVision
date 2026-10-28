@echo off
title LabVision - Iniciando...
cd /d "%~dp0"

echo ========================================================
echo       LabVision - INICIANDO APLICACION
echo             Creado por NachoFari
echo ========================================================
echo.

set PYTHON_CMD=

:: 1. Verificar entorno virtual preferido
if exist "C:\Users\farin\.venv\Scripts\python.exe" (
    set PYTHON_CMD="C:\Users\farin\.venv\Scripts\python.exe"
    goto RUN
)

:: 2. Verificar python en PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto RUN
)

:: 3. Verificar py launcher
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto RUN
)

echo [ERROR] No se encontro ninguna instalacion de Python en el sistema.
echo Por favor asegurese de tener Python 3.10+ instalado.
pause
exit /b 1

:RUN
echo Iniciando interfaz de usuario con %PYTHON_CMD%...
start "" %PYTHON_CMD% app.py
exit

