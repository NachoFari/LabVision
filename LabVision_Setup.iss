; =====================================================================
; LabVision v0.8 - Inno Setup Script
; Creado por NachoFari para distribución profesional en Windows
; =====================================================================

#define MyAppName "LabVision"
#define MyAppVersion "0.8"
#define MyAppPublisher "NachoFari"
#define MyAppURL "https://github.com/NachoFari/LabVision"
#define MyAppExeName "LabVision.exe"
#define MyScriptDir SourcePath

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
OutputDir={#MyScriptDir}\dist
OutputBaseFilename=LabVision-Setup-v0.8
SetupIconFile={#MyScriptDir}\labvision.ico
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=0.8.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=LabVision Setup - Digitalización de Pantallas de Laboratorio
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "{#MyScriptDir}\LabVision.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\ocr_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\launcher.cs"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\labvision.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\fox.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\MANUAL_DE_LABORATORIO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\setup_installer.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\Instalador_LabVision.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\Iniciar_LabVision.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\Iniciar_LabVision.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\Verificar_Instalacion.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\Crear_Acceso_Directo.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyScriptDir}\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\exporters\*"; DestDir: "{app}\exporters"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\notifications\*"; DestDir: "{app}\notifications"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\benchmark\*"; DestDir: "{app}\benchmark"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyScriptDir}\output\.gitkeep"; DestDir: "{app}\output"; Flags: ignoreversion

[Dirs]
Name: "{app}\output"; Permissions: users-full

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\labvision.ico"
Name: "{autoprograms}\{#MyAppName}\Verificar Instalación"; Filename: "{app}\Verificar_Instalacion.bat"; IconFilename: "{app}\labvision.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\labvision.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
