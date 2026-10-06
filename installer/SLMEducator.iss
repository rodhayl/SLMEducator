; SLMEducator installer recipe (Inno Setup 6).
;
; This maintained recipe wraps a freshly built PyInstaller "onedir" payload.
; Compile it through scripts/build_installer.py, which supplies these defines:
;   MyPayloadDir          absolute path to the pristine --prod payload
;   MyAppVersion          application version (e.g. 2.0.0)
;   MyNumericVersion      four-part numeric version for the file properties
;   MyBuildId             traceable build identifier (source commit)
;   MyOutputDir           new absolute directory for the compiled Setup executable
;   MyOutputBaseFilename  installer file base name
;
; Contract:
;   * Per-user install under LOCALAPPDATA; no administrator elevation.
;   * The seeded database and generated configuration are user data: they are
;     created only when absent and are never removed by the uninstaller.
;   * Updating an existing installation in place is not supported; Setup stops
;     with a clear message instead of improvising a migration.
;   * No dependency/model downloads, no hidden services, no generic process
;     killing and no external calls happen during installation.

#ifndef MyPayloadDir
  #error MyPayloadDir is required
#endif
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyNumericVersion
  #define MyNumericVersion "0.0.0.0"
#endif
#ifndef MyBuildId
  #define MyBuildId "unknown"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "."
#endif
#ifndef MyOutputBaseFilename
  #define MyOutputBaseFilename "SLMEducator-Setup"
#endif

#define MyAppName "SLMEducator"
#define MyAppExeName "SLMEducator.exe"
#define MyAppPublisher "SLMEducator"
#define MyAppId "{40301115-8D29-4D37-A067-F025278BCDC0}"
#define MyUninstallKey "{#MyAppId}_is1"

[Setup]
AppId={{40301115-8D29-4D37-A067-F025278BCDC0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} (build {#MyBuildId})
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyNumericVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
UsePreviousAppDir=no
DisableProgramGroupPage=yes
DisableDirPage=no
AllowUNCPath=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName} {#MyAppVersion} (build {#MyBuildId})
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
; This evaluation build is not code-signed; Windows SmartScreen may warn. Do not
; instruct users to bypass operating-system security controls.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.CreateDesktopIcon=Create a &desktop shortcut
english.AdditionalIcons=Shortcuts:
english.ExistingInstallBlocked=An existing SLMEducator installation was found for this user. This build does not update or migrate an existing installation. Uninstall the previous version first (your data and configuration are preserved), then run Setup again.
spanish.CreateDesktopIcon=Crear un acceso directo en el &escritorio
spanish.AdditionalIcons=Accesos directos:
spanish.ExistingInstallBlocked=Ya existe una instalacion de SLMEducator para este usuario. Esta compilacion no actualiza ni migra una instalacion existente. Desinstale la version anterior primero (sus datos y configuracion se conservan) y vuelva a ejecutar el instalador.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Full onedir payload. The seeded database and generated configuration are
; excluded here and installed separately so they are never overwritten and are
; never removed by the uninstaller.
Source: "{#MyPayloadDir}\*"; DestDir: "{app}"; Excludes: "slm_educator.db,env.properties,*.db-wal,*.db-shm"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyPayloadDir}\slm_educator.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#MyPayloadDir}\env.properties"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{userprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{#MyAppName} local launcher"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function PreviousInstallDetected(): Boolean;
var
  Existing: String;
begin
  Result :=
    RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyUninstallKey}', 'UninstallString', Existing) or
    RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}', 'UninstallString', Existing) or
    RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1', 'UninstallString', Existing);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if PreviousInstallDetected() then
  begin
    MsgBox(ExpandConstant('{cm:ExistingInstallBlocked}'), mbError, MB_OK);
    Result := False;
  end;
end;
