param(
  [string]$Version = "0.2.0-beta.1",
  [string]$GitHubRepo = "OWNER/REPO",
  [string]$Channel = "beta"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ReleaseDir = Join-Path $Root "release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$Manifest = [ordered]@{
  channel = $Channel
  version = $Version
  minimumAgentVersion = $Version
  releasePage = "https://github.com/$GitHubRepo/releases/tag/v$Version"
  notes = "MCPWorld Agent release manifest. Public assets are installer-only for beta users."
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
  }
}

$ManifestPath = Join-Path $ReleaseDir "latest.json"
$ShaPath = Join-Path $ReleaseDir "SHA256SUMS.txt"
$Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
"TBD_BUILD_ARTIFACT  MCPWorld-Agent-Setup.exe" | Set-Content -LiteralPath $ShaPath -Encoding UTF8
"TBD_BUILD_ARTIFACT  MCPWorld-Agent-Setup.msi" | Add-Content -LiteralPath $ShaPath -Encoding UTF8
Write-Host "Wrote $ManifestPath"
Write-Host "Wrote $ShaPath"
Write-Host "installer hashes are filled by the build workflow"
