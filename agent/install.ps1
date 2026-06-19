$ErrorActionPreference = "Stop"
$InstallDir = Join-Path $env:LOCALAPPDATA "MCPWorldAgent"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Force -Path "$PSScriptRoot\mcpworld_agent.py" -Destination $InstallDir
Write-Host "MCP World Agent files installed to $InstallDir"
Write-Host "Register with:"
Write-Host "python `"$InstallDir\mcpworld_agent.py`" --email demo@mcpworld.local"
