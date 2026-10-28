@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo       LabVision - ACCESO DIRECTO AL ESCRITORIO
echo ========================================================
echo.

set "VBS_TARGET=%~dp0Iniciar_LabVision.vbs"
set "SHORTCUT=%USERPROFILE%\Desktop\LabVision.lnk"
set "WORKING_DIR=%~dp0"
set "ICON_FILE=%~dp0labvision.ico"

if not exist "%ICON_FILE%" set "ICON_FILE=%SystemRoot%\System32\shell32.dll,21"

echo Creando acceso directo silencioso en el Escritorio...

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s = $ws.CreateShortcut('%SHORTCUT%'); " ^
  "$s.TargetPath = '%SystemRoot%\System32\wscript.exe'; " ^
  "$s.Arguments = '\"%VBS_TARGET%\"'; " ^
  "$s.WorkingDirectory = '%WORKING_DIR%'; " ^
  "$s.IconLocation = '%ICON_FILE%'; " ^
  "$s.Description = 'LabVision - Sistema de Captura de Laboratorio'; " ^
  "$s.Save()"

if exist "%SHORTCUT%" (
    echo.
    echo ========================================================
    echo   ACCESO DIRECTO CREADO EXITOSAMENTE EN TU ESCRITORIO
    echo   Ejecuta 100%% en silencio sin consola CMD negra.
    echo ========================================================
) else (
    echo [ERROR] No se pudo crear el acceso directo.
)

echo.
pause
exit /b 0

