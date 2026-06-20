$ErrorActionPreference = "Stop"
$InstallDir = Join-Path $env:LOCALAPPDATA "MCPWorldAgent"
$ConfigDir = Join-Path $env:USERPROFILE ".mcpworld"
$ConfigPath = Join-Path $ConfigDir "config.json"
$ExampleConfig = Join-Path $PSScriptRoot "mcpworld-mcp-config.example.json"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$AgentExe = Join-Path $PSScriptRoot "mcpworld-agent.exe"
$AgentPy = Join-Path $PSScriptRoot "mcpworld_agent.py"
if (Test-Path -LiteralPath $AgentExe) {
  Copy-Item -Force -Path $AgentExe -Destination $InstallDir
}
if (Test-Path -LiteralPath $AgentPy) {
  Copy-Item -Force -Path $AgentPy -Destination $InstallDir
}
if ((Test-Path -LiteralPath $ExampleConfig) -and !(Test-Path -LiteralPath $ConfigPath)) {
  Copy-Item -Force -Path $ExampleConfig -Destination $ConfigPath
}

Write-Host "MCP World Agent files installed to $InstallDir"
Write-Host "Local MCP config: $ConfigPath"
Write-Host "Edit that config to match your local Office/CAD/HWP/Photoshop/Blender MCP ports."
Write-Host "Run agent polling with:"
Write-Host "`"$InstallDir\mcpworld-agent.exe`" --email demo@mcpworld.local --poll-interval 5"
