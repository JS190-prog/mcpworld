; MCPWorld Agent installer for Inno Setup.
#define MyAppName "MCPWorld Agent"
#ifndef MyAppVersion
#define MyAppVersion "0.2.0-beta.1"
#endif
#define MyAppPublisher "MCPWorld"
#define MyAppExeName "mcpworld-agent.exe"

[Setup]
AppId={{A61F54BA-2D80-4F8E-ABF7-8D201CE95560}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MCPWorld Agent
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=MCPWorld-Agent-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\..\dist\agent-release\mcpworld-agent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\agent\install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\agent\mcpworld-mcp-config.example.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MCPWorld Agent"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall MCPWorld Agent"; Filename: "{uninstallexe}"

[Registry]
; Register the mcpworld:// URL protocol so the web dashboard "Connect this PC"
; button launches the agent with the connect link (per-user, HKCU = no admin).
Root: HKCU; Subkey: "Software\Classes\mcpworld"; ValueType: string; ValueName: ""; ValueData: "URL:MCPWorld Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\mcpworld"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\mcpworld\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\mcpworld\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--version"; Flags: runhidden waituntilterminated
