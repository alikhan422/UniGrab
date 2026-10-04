; Inno Setup Script for UniGrab Studio v2.0.1
#define MyAppName "UniGrab Studio"
#define MyAppVersion "2.0.1"
#define MyAppPublisher "UniGrab"
#define MyAppExeName "UniGrab.exe"
#define MySourceDir "F:\UniGrab\dist\UniGrab"

[Setup]
AppId={{C78DF412-89B2-4A82-9341-3F7A23CB9E01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=F:\UniGrab\license.txt
OutputDir=F:\UniGrab\Installer_Output
OutputBaseFilename=UniGrab_Setup_v2.0.1
SetupIconFile=F:\UniGrab\assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
ShowLanguageDialog=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "F:\UniGrab\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
