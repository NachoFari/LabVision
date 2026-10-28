# ==============================================================================
# LabVision - Setup & Installation Engine (PowerShell)
# Autor: NachoFari / LabVision Team
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Uninstall,
    [switch]$SkipDeps,
    [switch]$Quiet
)

# Configurar codificacion de salida a UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = "E:\reotaxis" }

# Colores y Formato
function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "   $Text" -ForegroundColor White -NoNewline
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host " [$Step] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [!] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "  [ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
}

function Show-AsciiBanner {
    Write-Host "  _           _    __     ___     _               ____            " -ForegroundColor Cyan
    Write-Host " | |    __ _ | |__ \ \   / (_)___(_) ___  _ __   |  _ \ _ __ ___  " -ForegroundColor Cyan
    Write-Host " | |   / _`` || '_ \ \ \ / /| / __| |/ _ \| '_ \  | |_) | '__/ _ \ " -ForegroundColor Cyan
    Write-Host " | |__| (_| || |_) | \ V / | \__ \ | (_) | | | | |  __/| | | (_) |" -ForegroundColor Cyan
    Write-Host " |_____\__,_||_.__/   \_/  |_|___/_|\___/|_| |_| |_|   |_|  \___/ " -ForegroundColor Cyan
    Write-Host "                                            EDICION PROFESIONAL v0.3" -ForegroundColor DarkCyan
    Write-Host "      Sistema Inteligente de Captura de Pantallas de Laboratorio" -ForegroundColor Gray
}

# ==============================================================================
# DETECCION DE PYTHON
# ==============================================================================
function Find-PythonEnvironment {
    Write-Step "1/3" "Buscando entorno de ejecucion de Python..."

    $candidates = [System.Collections.Generic.List[string]]::new()
    
    # 1. Virtual environments conocidos
    [void]$candidates.Add("C:\Users\farin\.venv\Scripts\python.exe")
    [void]$candidates.Add((Join-Path $env:USERPROFILE ".venv\Scripts\python.exe"))
    [void]$candidates.Add((Join-Path $ScriptDir ".venv\Scripts\python.exe"))

    # 2. Rutas estandar de Python en Windows
    $localApp = $env:LOCALAPPDATA
    if ($localApp) {
        $pyDirs = Get-ChildItem -Path (Join-Path $localApp "Programs\Python") -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($dir in $pyDirs) {
            [void]$candidates.Add((Join-Path $dir.FullName "python.exe"))
        }
    }

    # 3. Directorios raiz clasicos
    foreach ($v in @("312", "311", "310", "39")) {
        [void]$candidates.Add("C:\Python$v\python.exe")
        [void]$candidates.Add("C:\Program Files\Python$v\python.exe")
    }

    # 4. PATH del sistema (filtrando stub de WindowsApps si existe)
    try {
        $wherePys = where.exe python 2>$null
        if ($wherePys) {
            foreach ($p in $wherePys) {
                if ($p -notlike "*WindowsApps*") {
                    [void]$candidates.Add($p)
                }
            }
        }
    } catch {}

    # Probar candidatos
    foreach ($cand in $candidates) {
        if (Test-Path $cand) {
            try {
                $pinfo = New-Object System.Diagnostics.ProcessStartInfo
                $pinfo.FileName = $cand
                $pinfo.Arguments = "-c ""import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"""
                $pinfo.RedirectStandardOutput = $true
                $pinfo.RedirectStandardError = $true
                $pinfo.UseShellExecute = $false
                $pinfo.CreateNoWindow = $true

                $proc = [System.Diagnostics.Process]::Start($pinfo)
                $stdout = $proc.StandardOutput.ReadToEnd().Trim()
                [void]$proc.WaitForExit(3000)

                if ($proc.ExitCode -eq 0 -and $stdout -match "^3\.") {
                    $pythonDir = Split-Path -Parent $cand
                    $pythonw = Join-Path $pythonDir "pythonw.exe"
                    if (-not (Test-Path $pythonw)) {
                        $pythonw = "pythonw.exe"
                    }

                    Write-Success "Python detectado con exito: $cand (v$stdout)"
                    return @{
                        Found = $true
                        PythonExe = $cand
                        PythonwExe = $pythonw
                        Version = $stdout
                        IsVenv = ($cand -like "*\.venv\*")
                    }
                }
            } catch {}
        }
    }

    Write-Err "No se detecto ninguna instalacion valida de Python 3.10+ en el sistema."
    return @{ Found = $false }
}

# ==============================================================================
# VERIFICACION DE DEPENDENCIAS
# ==============================================================================
function Verify-Dependencies {
    param(
        [Parameter(Mandatory=$true)]
        [hashtable]$PyEnv,
        [switch]$InstallMissing
    )

    Write-Step "2/3" "Comprobando librerias y dependencias requeridas..."

    $pyExe = $PyEnv.PythonExe
    $pyCode = "import json; mods = [('torch','torch'), ('torchvision','torchvision'), ('opencv-python','cv2'), ('easyocr','easyocr'), ('pywebview','webview'), ('openpyxl','openpyxl'), ('pandas','pandas'), ('requests','requests')]; res = {}; [res.setdefault(pkg, (True if __import__(imp) else True)) for pkg, imp in mods]; print('JSON_RES:' + json.dumps(res))"

    $pinfo = New-Object System.Diagnostics.ProcessStartInfo
    $pinfo.FileName = $pyExe
    $pinfo.Arguments = "-c ""$pyCode"""
    $pinfo.RedirectStandardOutput = $true
    $pinfo.RedirectStandardError = $true
    $pinfo.UseShellExecute = $false
    $pinfo.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($pinfo)
    $stdout = $proc.StandardOutput.ReadToEnd()
    [void]$proc.WaitForExit(30000)

    $missing = [System.Collections.Generic.List[string]]::new()

    if ($stdout -match "JSON_RES:(.*)") {
        $jsonStr = $matches[1].Trim()
        $statusDict = ConvertFrom-Json $jsonStr
        foreach ($prop in $statusDict.PSObject.Properties) {
            $pkg = $prop.Name
            $isOk = $prop.Value
            if ($isOk) {
                Write-Success "Libreria OK: $pkg"
            } else {
                Write-Warn "Falta o error al importar: $pkg"
                [void]$missing.Add($pkg)
            }
        }
    } else {
        Write-Warn "No se pudo comprobar en lote, verificando individualmente..."
        $requiredModules = @(
            @{ PipName = "torch"; ImportName = "torch" },
            @{ PipName = "torchvision"; ImportName = "torchvision" },
            @{ PipName = "opencv-python"; ImportName = "cv2" },
            @{ PipName = "easyocr"; ImportName = "easyocr" },
            @{ PipName = "pywebview"; ImportName = "webview" },
            @{ PipName = "openpyxl"; ImportName = "openpyxl" },
            @{ PipName = "pandas"; ImportName = "pandas" },
            @{ PipName = "requests"; ImportName = "requests" }
        )
        foreach ($mod in $requiredModules) {
            $imp = $mod.ImportName
            $p = Start-Process -FilePath $pyExe -ArgumentList "-c ""import $imp""" -NoNewWindow -Wait -PassThru
            if ($p.ExitCode -eq 0) {
                Write-Success "Libreria OK: $($mod.PipName)"
            } else {
                Write-Warn "Falta o error: $($mod.PipName)"
                [void]$missing.Add($mod.PipName)
            }
        }
    }

    if ($missing.Count -eq 0) {
        Write-Success "Todas las dependencias criticas estan instaladas y operativas."
        return $true
    }

    if ($InstallMissing) {
        Write-Host ""
        Write-Host " [!] Instalando dependencias faltantes via PIP ($($missing -join ', '))..." -ForegroundColor Yellow
        foreach ($pkg in $missing) {
            Write-Host "     > Instalando $pkg..." -ForegroundColor Cyan
            $p = Start-Process -FilePath $pyExe -ArgumentList "-m pip install --upgrade $pkg" -NoNewWindow -Wait -PassThru
            if ($p.ExitCode -ne 0) {
                Write-Err "Fallo al instalar $pkg. Verifique conexion a internet o permisos."
                return $false
            }
        }
        Write-Success "Dependencias instaladas exitosamente."
        return $true
    } else {
        Write-Warn "Existen $($missing.Count) librerias faltantes."
        return $false
    }
}

# ==============================================================================
# CREACION DE ACCESOS DIRECTOS (DESKTOP Y MENU INICIO)
# ==============================================================================
function Install-Shortcuts {
    Write-Step "3/3" "Configurando accesos directos en Windows..."

    $vbsPath = Join-Path $ScriptDir "Iniciar_LabVision.vbs"
    if (-not (Test-Path $vbsPath)) {
        Write-Err "No se encontro el lanzador silencioso: $vbsPath"
        return $false
    }

    $iconPath = Join-Path $ScriptDir "labvision.ico"
    if (-not (Test-Path $iconPath)) {
        $iconLocation = "$env:SystemRoot\System32\shell32.dll,21"
    } else {
        $iconLocation = "$iconPath,0"
    }

    $wscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"

    try {
        $wshShell = New-Object -ComObject WScript.Shell

        # 1. Acceso directo en el Escritorio (Desktop)
        $desktopPath = [Environment]::GetFolderPath('Desktop')
        $desktopShortcutPath = Join-Path $desktopPath "LabVision.lnk"

        $scDesktop = $wshShell.CreateShortcut($desktopShortcutPath)
        $scDesktop.TargetPath = $wscriptExe
        $scDesktop.Arguments = "`"$vbsPath`""
        $scDesktop.WorkingDirectory = $ScriptDir
        $scDesktop.IconLocation = $iconLocation
        $scDesktop.Description = "LabVision - Sistema Inteligente de Extraccion de Laboratorio"
        $scDesktop.Save()

        Write-Success "Acceso directo en Escritorio: $desktopShortcutPath"

        # 2. Carpeta y Acceso directo en MenÃº Inicio (Start Menu -> Programs)
        $programsPath = [Environment]::GetFolderPath('Programs')
        $menuFolder = Join-Path $programsPath "LabVision"
        if (-not (Test-Path $menuFolder)) {
            New-Item -ItemType Directory -Path $menuFolder -Force | Out-Null
        }

        # Lanzador Principal
        $menuShortcutPath = Join-Path $menuFolder "LabVision.lnk"
        $scMenu = $wshShell.CreateShortcut($menuShortcutPath)
        $scMenu.TargetPath = $wscriptExe
        $scMenu.Arguments = "`"$vbsPath`""
        $scMenu.WorkingDirectory = $ScriptDir
        $scMenu.IconLocation = $iconLocation
        $scMenu.Description = "LabVision - Sistema Inteligente de Extraccion de Laboratorio"
        $scMenu.Save()

        # Acceso de Diagnostico / Desinstalacion en MenÃº Inicio
        $diagBat = Join-Path $ScriptDir "Verificar_Instalacion.bat"
        if (Test-Path $diagBat) {
            $menuDiagPath = Join-Path $menuFolder "Verificar o Reparar Instalacion.lnk"
            $scDiag = $wshShell.CreateShortcut($menuDiagPath)
            $scDiag.TargetPath = $diagBat
            $scDiag.WorkingDirectory = $ScriptDir
            $scDiag.IconLocation = "$env:SystemRoot\System32\imageres.dll,89"
            $scDiag.Description = "Herramienta de Diagnostico y Reparacion de LabVision"
            $scDiag.Save()
        }

        Write-Success "Acceso directo en Menu Inicio: $menuFolder"

        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wshShell) | Out-Null
        return $true
    } catch {
        Write-Err "Error al crear los accesos directos: $_"
        return $false
    }
}

# ==============================================================================
# DESINSTALACION DE ACCESOS DIRECTOS
# ==============================================================================
function Uninstall-Shortcuts {
    Write-Header "DESINSTALACION DE ACCESOS DIRECTOS DE LabVision"

    $desktopPath = [Environment]::GetFolderPath('Desktop')
    $desktopShortcut = Join-Path $desktopPath "LabVision.lnk"

    if (Test-Path $desktopShortcut) {
        Remove-Item $desktopShortcut -Force
        Write-Success "Eliminado acceso directo del Escritorio."
    } else {
        Write-Warn "No existia acceso directo en el Escritorio."
    }

    $programsPath = [Environment]::GetFolderPath('Programs')
    $menuFolder = Join-Path $programsPath "LabVision"
    if (Test-Path $menuFolder) {
        Remove-Item $menuFolder -Recurse -Force
        Write-Success "Eliminada la carpeta de accesos directos del Menu Inicio."
    }

    $rootMenuLnk = Join-Path $programsPath "LabVision.lnk"
    if (Test-Path $rootMenuLnk) {
        Remove-Item $rootMenuLnk -Force
    }

    Write-Host ""
    Write-Host "  [OK] Desinstalacion de accesos completada." -ForegroundColor Green
}

# ==============================================================================
# MODO DIAGNOSTICO / CHECK ONLY
# ==============================================================================
function Run-Diagnostics {
    Write-Header "DIAGNOSTICO INTEGRAL DE LabVision"

    # 1. Archivos base del proyecto
    Write-Step "1/4" "Verificando integridad del codigo base..."
    $keyFiles = @(
        "app.py",
        "ocr_engine.py",
        "Iniciar_LabVision.vbs",
        "Iniciar_LabVision.bat",
        "labvision.ico",
        "static\index.html",
        "static\app.js",
        "config\manager.py",
        "notifications\discord.py"
    )

    $allFilesOk = $true
    foreach ($kf in $keyFiles) {
        $p = Join-Path $ScriptDir $kf
        if (Test-Path $p) {
            Write-Success "Archivo presente: $kf"
        } else {
            Write-Err "Falta archivo critico: $kf"
            $allFilesOk = $false
        }
    }

    # 2. Entorno Python
    Write-Step "2/4" "Verificando interprete Python..."
    $pyEnv = Find-PythonEnvironment
    if (-not $pyEnv.Found) {
        Write-Err "Interprete Python NO encontrado."
    } else {
        Write-Success "Python OK: $($pyEnv.PythonExe)"
        Write-Success "PythonW OK: $($pyEnv.PythonwExe)"
    }

    # 3. Dependencias
    Write-Step "3/4" "Verificando modulos Python..."
    $depsOk = $false
    if ($pyEnv.Found) {
        $depsOk = Verify-Dependencies -PyEnv $pyEnv
    }

    # 4. Accesos Directos
    Write-Step "4/4" "Verificando accesos directos..."
    $desktopPath = [Environment]::GetFolderPath('Desktop')
    $desktopShortcut = Join-Path $desktopPath "LabVision.lnk"
    $hasDesktop = Test-Path $desktopShortcut

    $programsPath = [Environment]::GetFolderPath('Programs')
    $menuLnk = Join-Path $programsPath "LabVision\LabVision.lnk"
    $hasMenu = Test-Path $menuLnk

    if ($hasDesktop) {
        Write-Success "Acceso en Escritorio detectado."
    } else {
        Write-Warn "Acceso en Escritorio NO encontrado."
    }

    if ($hasMenu) {
        Write-Success "Acceso en Menu Inicio detectado."
    } else {
        Write-Warn "Acceso en Menu Inicio NO encontrado."
    }

    Write-Header "RESUMEN DEL DIAGNOSTICO"
    if ($allFilesOk -and $pyEnv.Found -and $depsOk -and $hasDesktop) {
        Write-Host "  >> ESTADO GENERAL: PERFECTO (LISTO PARA PRODUCCION) <<" -ForegroundColor Green
    } else {
        Write-Host "  >> ATENCION: Hay elementos que requieren atencion <<" -ForegroundColor Yellow
        Write-Host "  Ejecute 'Instalador_LabVision.bat' para corregir cualquier problema de forma automatica." -ForegroundColor Cyan
    }
}

# ==============================================================================
# LOGICA PRINCIPAL DE INSTALACION
# ==============================================================================
Clear-Host
Show-AsciiBanner

if ($Uninstall) {
    Uninstall-Shortcuts
    exit 0
}

if ($CheckOnly) {
    Run-Diagnostics
    exit 0
}

Write-Header "INICIANDO INSTALACION Y CONFIGURACION DE LabVision"

# 1. Python
$pyEnv = Find-PythonEnvironment
if (-not $pyEnv.Found) {
    Write-Err "No se puede continuar sin una instalacion de Python 3.10+."
    Write-Host "Por favor instale Python desde python.org o verifique su configuracion." -ForegroundColor Yellow
    exit 1
}

# 2. Dependencias
if (-not $SkipDeps) {
    $depsResult = Verify-Dependencies -PyEnv $pyEnv -InstallMissing
    if (-not $depsResult) {
        Write-Warn "Algunas dependencias tuvieron advertencias. Continuando..."
    }
} else {
    Write-Warn "Verificacion de dependencias omitida por parametro."
}

# 3. Accesos directos
$scResult = Install-Shortcuts
if (-not $scResult) {
    Write-Err "Hubo un problema al crear los accesos directos."
    exit 1
}

Write-Header "INSTALACION COMPLETADA CON EXITO"
Write-Host "  LabVision ha sido instalado y configurado correctamente." -ForegroundColor Green
Write-Host "  - Acceso directo en el Escritorio: 'LabVision'" -ForegroundColor White
Write-Host "  - Acceso en Menu Inicio: 'Programas -> LabVision'" -ForegroundColor White
Write-Host "  - Ejecucion 100% silenciosa (sin ventana negra de CMD)" -ForegroundColor White
Write-Host ""

