@echo off
setlocal EnableDelayedExpansion
title LabVision - Instalador y Configurador Oficial
color 0B
chcp 65001 >nul 2>&1
cd /d "%~dp0"

:MENU
cls
echo ==============================================================================
echo   _           _    __     ___     _               ____            
echo  ^| ^|    __ _ ^| ^|__ \ \   / (_)___(_) ___  _ __   ^|  _ \ _ __ ___  
echo  ^| ^|   / _` ^|^| '_ \ \ \ / /^| / __^| ^|/ _ \^| '_ \  ^| ^|_) ^| '__/ _ \ 
echo  ^| ^|__^| (_^| ^|^|^| ^|_) ^| \ V / ^| \__ \ ^| (_) ^| ^| ^| ^| ^|  __/^| ^| ^| (_) ^|
echo  ^|_____\__,_^|^|^|_.__/   \_/  ^|_^|___/_^|\___/^|_^| ^|_^| ^|_^|   ^|_^|  \___/ 
echo                                             EDICION PROFESIONAL v0.3
echo        Sistema Inteligente de Captura de Pantallas de Laboratorio
echo ==============================================================================
echo.
echo  Bienvenido al asistente de instalacion y configuracion de LabVision.
echo  Ubicacion del sistema: %~dp0
echo.
echo  ----------------------------------------------------------------------
echo   OPCIONES DISPONIBLES:
echo  ----------------------------------------------------------------------
echo    [1] Instalacion Completa Recomendada (Verificar, Dependencias y Accesos)
echo    [2] Crear / Reparar Accesos Directos (Escritorio y Menu Inicio)
echo    [3] Diagnostico Rapido y Verificacion del Sistema
echo    [4] Desinstalar Accesos Directos
echo    [5] Iniciar LabVision Ahora (Modo Silencioso)
echo    [6] Salir
echo  ----------------------------------------------------------------------
echo.
set /p "OPC= Seleccione una opcion (1-6) [predeterminado: 1]: "
if "%OPC%"=="" set "OPC=1"

if "%OPC%"=="1" goto INSTALAR_TODO
if "%OPC%"=="2" goto CREAR_ACCESOS
if "%OPC%"=="3" goto VERIFICAR
if "%OPC%"=="4" goto DESINSTALAR
if "%OPC%"=="5" goto INICIAR_APP
if "%OPC%"=="6" goto SALIR

echo.
echo [!] Opcion invalida. Intente de nuevo.
timeout /t 2 >nul 2>&1 || ping -n 3 127.0.0.1 >nul
goto MENU

:INSTALAR_TODO
cls
echo.
echo ==============================================================================
echo       LabVision - EJECUTANDO INSTALACION COMPLETA
echo ==============================================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if %EXIT_CODE% equ 0 (
    echo ==============================================================================
    echo   TODO LISTO: La instalacion ha finalizado con exito.
    echo ==============================================================================
    echo.
    set /p "RUN_NOW= Desea iniciar LabVision ahora mismo? (S/N) [S]: "
    if "!RUN_NOW!"=="" set "RUN_NOW=S"
    if /i "!RUN_NOW!"=="S" (
        echo Iniciando aplicacion...
        start "" wscript.exe "%~dp0Iniciar_LabVision.vbs"
    )
) else (
    echo [ERROR] Hubo un problema durante la instalacion. Revise los mensajes arriba.
)
echo.
pause
goto MENU

:CREAR_ACCESOS
cls
echo.
echo ==============================================================================
echo       LabVision - CREACION DE ACCESOS DIRECTOS
echo ==============================================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -SkipDeps
echo.
pause
goto MENU

:VERIFICAR
cls
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -CheckOnly
echo.
pause
goto MENU

:DESINSTALAR
cls
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_installer.ps1" -Uninstall
echo.
pause
goto MENU

:INICIAR_APP
cls
echo.
echo ==============================================================================
echo   Iniciando LabVision en segundo plano de forma silenciosa...
echo ==============================================================================
start "" wscript.exe "%~dp0Iniciar_LabVision.vbs"
echo.
echo [OK] Aplicacion lanzada exitosamente.
timeout /t 3 >nul 2>&1 || ping -n 4 127.0.0.1 >nul
goto MENU

:SALIR
cls
echo Gracias por usar LabVision. Hasta pronto!
timeout /t 2 >nul 2>&1 || ping -n 3 127.0.0.1 >nul
exit /b 0

