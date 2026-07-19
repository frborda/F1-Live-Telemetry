; Instalador de F1 Live Telemetry (Inno Setup 6).
; Se compila desde build.ps1 con:  ISCC.exe /DAppVersion=x.y.z F1LiveTelemetry.iss
; Instala en %LOCALAPPDATA%\Programs (sin permisos de administrador), así el
; actualizador automático integrado puede reemplazar los archivos sin UAC.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7C1F4B0A-9D34-4E1B-8B37-F1E2C39A6D51}
AppName=F1 Live Telemetry
AppVersion={#AppVersion}
AppPublisher=frborda
AppPublisherURL=https://github.com/frborda/F1-Live-Telemetry
DefaultDirName={autopf}\F1LiveTelemetry
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=no
OutputBaseFilename=F1LiveTelemetry-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\F1LiveTelemetry.exe
UninstallDisplayName=F1 Live Telemetry
CloseApplications=yes
RestartApplications=no
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\F1LiveTelemetry\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\F1 Live Telemetry"; Filename: "{app}\F1LiveTelemetry.exe"
Name: "{autoprograms}\F1 Telemetry Capture"; \
    Filename: "{app}\capture\F1TelemCapture.exe"
Name: "{autodesktop}\F1 Live Telemetry"; Filename: "{app}\F1LiveTelemetry.exe"; \
    Tasks: desktopicon

[Registry]
; protocolo f1telemetry:// -> capturador (la extensión de Chrome entrega el
; token F1TV con el diálogo nativo "Abrir F1 Live Telemetry" del navegador)
Root: HKCU; Subkey: "Software\Classes\f1telemetry"; ValueType: string; \
    ValueData: "URL:F1 Live Telemetry"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\f1telemetry"; ValueType: string; \
    ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\f1telemetry\shell\open\command"; \
    ValueType: string; ValueData: """{app}\capture\F1TelemCapture.exe"" ""%1"""

[Run]
Filename: "{app}\F1LiveTelemetry.exe"; \
    Description: "Launch F1 Live Telemetry"; Flags: nowait postinstall skipifsilent
