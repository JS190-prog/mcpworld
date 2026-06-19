param(
  [string]$Version = "0.2.0-beta.1",
  [string]$GitHubRepo = "OWNER/REPO",
  [string]$Channel = "beta"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ReleaseDir = Join-Path $Root "release"
$AgentZip = Join-Path $Root "agent\mcpworld-agent.zip"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

if (!(Test-Path -LiteralPath $AgentZip)) {
  throw "Missing $AgentZip. Build agent/mcpworld-agent.zip first."
}

$ZipSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $AgentZip).Hash.ToLowerInvariant()
$Manifest = [ordered]@{
  channel = $Channel
  version = $Version
  minimumAgentVersion = $Version
  releasePage = "https://github.com/$GitHubRepo/releases/tag/v$Version"
  notes = "MCPWorld Agent release manifest. Large binaries are hosted on GitHub Releases."
  assets = [ordered]@{
    exe = [ordered]@{
      fileName = "MCPWorld-Agent-Setup.exe"
      url = "https://github.com/$GitHubRepo/releases/download/v$Version/MCPWorld-Agent-Setup.exe"
      sha256 = "TBD_BUILD_ARTIFACT"
      recommendedFor = "general Windows users"
    }
    msi = [ordered]@{
      fileName = "MCPWorld-Agent-Setup.msi"
      url = "https://github.com/$GitHubRepo/releases/download/v$Version/MCPWorld-Agent-Setup.msi"
      sha256 = "TBD_BUILD_ARTIFACT"
      recommendedFor = "managed enterprise deployment"
    }
    zip = [ordered]@{
      fileName = "mcpworld-agent.zip"
      url = "https://github.com/$GitHubRepo/releases/download/v$Version/mcpworld-agent.zip"
      sha256 = $ZipSha
      recommendedFor = "manual install and recovery"
    }
  }
}

$ManifestPath = Join-Path $ReleaseDir "latest.json"
$ShaPath = Join-Path $ReleaseDir "SHA256SUMS.txt"
$Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
"$ZipSha  mcpworld-agent.zip" | Set-Content -LiteralPath $ShaPath -Encoding UTF8
Write-Host "Wrote $ManifestPath"
Write-Host "Wrote $ShaPath"
Write-Host "zip sha256=$ZipSha"
