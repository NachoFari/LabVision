@echo off
title LabVision - Iniciando...
cd /d "%~dp0"

echo ========================================================
echo       LabVision - INICIANDO APLICACION
echo             Creado por NachoFari
echo ========================================================
echo.

set PYTHON_CMD=

:: 1. Verificar runtime portable local
if exist "%~dp0runtime\python.exe" (
    set PYTHON_CMD="%~dp0runtime\python.exe"
    goto RUN
)

:: 2. Verificar entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_CMD="%~dp0.venv\Scripts\python.exe"
    goto RUN
)

:: 3. Verificar python en PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto RUN
)

:: 4. Verificar py launcher
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto RUN
)

echo [ERROR] No se encontro ninguna instalacion de Python en el sistema.
echo Por favor asegurese de tener Python 3.10+ instalado o el runtime en la carpeta de la aplicacion.
pause
exit /b 1

:RUN
echo Iniciando interfaz de usuario con %PYTHON_CMD%...
start "" %PYTHON_CMD% app.py
exit
