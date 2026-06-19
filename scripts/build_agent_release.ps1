param(
  [string]$Version = "0.2.0-beta.1",
  [string]$GitHubRepo = "JS190-prog/mcpworld",
  [switch]$SkipInstallerTools
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $Root "dist\agent-release"
$BuildDir = Join-Path $Root "dist\agent-build"
$AgentZip = Join-Path $DistDir "mcpworld-agent.zip"
$AgentPy = Join-Path $Root "agent\mcpworld_agent.py"
$InstallPs1 = Join-Path $Root "agent\install.ps1"
$InnoScript = Join-Path $Root "installer\inno\MCPWorldAgent.iss"
$WixScript = Join-Path $Root "installer\wix\MCPWorldAgent.wxs"

Remove-Item -Recurse -Force -LiteralPath $DistDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath $BuildDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Compress-Archive -Force -Path $AgentPy,$InstallPs1 -DestinationPath $AgentZip

$VenvDir = Join-Path $BuildDir "venv"
python -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install pyinstaller
& $VenvPython -m PyInstaller --onefile --name mcpworld-agent --distpath $DistDir --workpath (Join-Path $BuildDir "pyinstaller-work") --specpath $BuildDir $AgentPy

$AgentExe = Join-Path $DistDir "mcpworld-agent.exe"
if (!(Test-Path -LiteralPath $AgentExe)) {
  throw "Missing built agent exe: $AgentExe"
}

$SetupExe = Join-Path $DistDir "MCPWorld-Agent-Setup.exe"
$SetupMsi = Join-Path $DistDir "MCPWorld-Agent-Setup.msi"

if (!$SkipInstallerTools) {
  $InnoCompiler = Get-Command iscc.exe -ErrorAction SilentlyContinue
  if ($InnoCompiler) {
    & $InnoCompiler.Source "/DMyAppVersion=$Version" "/O$DistDir" $InnoScript
  } else {
    Write-Warning "Inno Setup compiler was not found. Skipping EXE installer."
  }

  $Candle = Get-Command candle.exe -ErrorAction SilentlyContinue
  $Light = Get-Command light.exe -ErrorAction SilentlyContinue
  if ($Candle -and $Light) {
    $WixObj = Join-Path $BuildDir "MCPWorldAgent.wixobj"
    & $Candle.Source -dProductVersion=$Version -dDistDir=$DistDir -out $WixObj $WixScript
    & $Light.Source -ext WixUIExtension -out $SetupMsi $WixObj
  } else {
    Write-Warning "WiX Toolset was not found. Skipping MSI installer."
  }
}

$ShaPath = Join-Path $DistDir "SHA256SUMS.txt"
Get-ChildItem -LiteralPath $DistDir -File | Where-Object { $_.Name -match '\.(zip|exe|msi)$' } | ForEach-Object {
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
  "$Hash  $($_.Name)"
} | Set-Content -LiteralPath $ShaPath -Encoding UTF8

$ZipSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $AgentZip).Hash.ToLowerInvariant()
$ExeSha = if (Test-Path -LiteralPath $SetupExe) { (Get-FileHash -Algorithm SHA256 -LiteralPath $SetupExe).Hash.ToLowerInvariant() } else { "TBD_BUILD_ARTIFACT" }
$MsiSha = if (Test-Path -LiteralPath $SetupMsi) { (Get-FileHash -Algorithm SHA256 -LiteralPath $SetupMsi).Hash.ToLowerInvariant() } else { "TBD_BUILD_ARTIFACT" }
$Manifest = [ordered]@{
  channel = "beta"
  version = $Version
  minimumAgentVersion = $Version
  releasePage = "https://github.com/$GitHubRepo/releases/tag/v$Version"
  notes = "MCPWorld Agent release manifest. Large binaries are hosted on GitHub Releases."
  assets = [ordered]@{
    exe = [ordered]@{
      fileName = "MCPWorld-Agent-Setup.exe"
      url = "https://github.com/$GitHubRepo/releases/download/v$Version/MCPWorld-Agent-Setup.exe"
      sha256 = $ExeSha
      recommendedFor = "general Windows users"
    }
    msi = [ordered]@{
      fileName = "MCPWorld-Agent-Setup.msi"
      url = "https://github.com/$GitHubRepo/releases/download/v$Version/MCPWorld-Agent-Setup.msi"
      sha256 = $MsiSha
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
$Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $DistDir "latest.json") -Encoding UTF8
Write-Host "Built release files in $DistDir"
Get-ChildItem -LiteralPath $DistDir -File | Select-Object Name,Length | Format-Table -AutoSize
