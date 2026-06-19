# Agent installer pipeline

This repository can build beta Windows distribution assets through GitHub Actions.

## Outputs

The pipeline is designed to produce:

- MCPWorld-Agent-Setup.exe
- MCPWorld-Agent-Setup.msi
- mcpworld-agent.zip
- latest.json
- SHA256SUMS.txt

## How to run

Open GitHub Actions and run `Build MCPWorld Agent Installers` manually.

Use:

- version: `0.2.0-beta.1`
- release_tag: `v0.2.0-beta.1`

The workflow uploads generated files to the matching GitHub Release with `--clobber`.

## Local dry run

A local dry run can build the Python executable and ZIP if PyInstaller is available:

```powershell
powershell -ExecutionPolicy Bypass -File .\scriptsuild_agent_release.ps1 -Version 0.2.0-beta.1 -GitHubRepo JS190-prog/mcpworld -SkipInstallerTools
```

Full EXE/MSI installer generation requires Inno Setup and WiX Toolset on PATH.
