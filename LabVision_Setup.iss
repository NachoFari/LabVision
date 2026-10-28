; =====================================================================
; LabVision v0.3 - Inno Setup Script
; Creado por NachoFari para distribución profesional en Windows
; =====================================================================

#define MyAppName "LabVision"
#define MyAppVersion "0.3"
#define MyAppPublisher "NachoFari"
#define MyAppURL "https://github.com/NachoFari/LabVision"
#define MyAppExeName "LabVision.exe"

[Setup]
AppId={{E6F7A9C2-8B1D-4A3C-9E5F-7C2B1A0D4E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=E:\reotaxis\dist
OutputBaseFilename=LabVision-Setup-v0.3
SetupIconFile=E:\reotaxis\labvision.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=0.3.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=LabVision Setup - Digitalización de Pantallas de Laboratorio
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "E:\reotaxis\LabVision.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\ocr_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\launcher.cs"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\labvision.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\fox.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\MANUAL_DE_LABORATORIO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\setup_installer.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\Iniciar_LabVision.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\Iniciar_LabVision.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\Verificar_Instalacion.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\Crear_Acceso_Directo.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\reotaxis\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\exporters\*"; DestDir: "{app}\exporters"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\notifications\*"; DestDir: "{app}\notifications"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\benchmark\*"; DestDir: "{app}\benchmark"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\reotaxis\output\.gitkeep"; DestDir: "{app}\output"; Flags: ignoreversion

[Dirs]
Name: "{app}\output"; Permissions: users-full

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\labvision.ico"
Name: "{autoprograms}\{#MyAppName}\Verificar Instalación"; Filename: "{app}\Verificar_Instalacion.bat"; IconFilename: "{app}\labvision.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\labvision.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
