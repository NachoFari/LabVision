@echo off
setlocal EnableDelayedExpansion
title LabVision - Verificacion de Instalacion y Diagnostico
color 0A
chcp 65001 >nul 2>&1
cd /d "%~dp0"

:DIAG_LOOP
cls
echo ==============================================================================
echo       LabVision - HERRAMIENTA DE VERIFICACION Y DIAGNOSTICO
echo ==============================================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -CheckOnly
echo.
echo ==============================================================================
echo   ACCIONES DISPONIBLES:
echo ==============================================================================
echo   [1] Reparar / Recrear Accesos Directos (Escritorio y Menu Inicio)
echo   [2] Ejecutar Instalacion / Reparacion Completa
echo   [3] Probar Inicio de LabVision (Modo Silencioso)
echo   [4] Desinstalar Accesos Directos
echo   [5] Volver a Ejecutar Diagnostico
echo   [6] Salir
echo.
set /p "CHOICE= Seleccione una accion (1-6) [6]: "
if "%CHOICE%"=="" set "CHOICE=6"

if "%CHOICE%"=="1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -SkipDeps
    pause
    goto DIAG_LOOP
)
if "%CHOICE%"=="2" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1"
    pause
    goto DIAG_LOOP
)
if "%CHOICE%"=="3" (
    echo Iniciando aplicacion...
    start "" wscript.exe "%~dp0Iniciar_LabVision.vbs"
    echo [OK] Aplicacion lanzada.
    timeout /t 3 >nul 2>&1 || ping -n 4 127.0.0.1 >nul
    goto DIAG_LOOP
)
if "%CHOICE%"=="4" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -Uninstall
    pause
    goto DIAG_LOOP
)
if "%CHOICE%"=="5" (
    goto DIAG_LOOP
)
if "%CHOICE%"=="6" (
    exit /b 0
)

goto DIAG_LOOP

