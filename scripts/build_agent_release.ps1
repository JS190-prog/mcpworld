param(
  [string]$Version = "0.2.0-beta.1",
  [string]$GitHubRepo = "JS190-prog/mcpworld",
  [switch]$SkipInstallerTools
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -ge 7) {
  $PSNativeCommandUseErrorActionPreference = $true
}

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
  )
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Native command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

function Convert-ToMsiVersion {
  param([Parameter(Mandatory=$true)][string]$SemanticVersion)
  $match = [regex]::Match($SemanticVersion, '^(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)(?:[-.](?<build>\d+|[A-Za-z]+\.?)(?<rest>.*))?$')
  if (!$match.Success) {
    throw "Version '$SemanticVersion' cannot be converted to an MSI ProductVersion."
  }
  $build = 0
  if ($match.Groups['rest'].Value -match '(\d+)') {
    $build = [int]$Matches[1]
  } elseif ($SemanticVersion -match '(\d+)$') {
    $build = [int]$Matches[1]
  }
  return "$($match.Groups['major'].Value).$($match.Groups['minor'].Value).$($match.Groups['patch'].Value).$build"
}
$Root = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $Root "dist\agent-release"
$BuildDir = Join-Path $Root "dist\agent-build"
$AgentZip = Join-Path $DistDir "mcpworld-agent.zip"
$AgentPy = Join-Path $Root "agent\mcpworld_agent.py"
$InstallPs1 = Join-Path $Root "agent\install.ps1"
$AgentConfigExample = Join-Path $Root "agent\mcpworld-mcp-config.example.json"
$InnoScript = Join-Path $Root "installer\inno\MCPWorldAgent.iss"
$WixScript = Join-Path $Root "installer\wix\MCPWorldAgent.wxs"
$MsiProductVersion = Convert-ToMsiVersion $Version

Remove-Item -Recurse -Force -LiteralPath $DistDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath $BuildDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Compress-Archive -Force -Path $AgentPy,$InstallPs1,$AgentConfigExample -DestinationPath $AgentZip

# Stamp the exact build version into the agent so the shipped binary reports it
# (channel update checks compare AGENT_VERSION against the manifest version).
$AgentVersionFile = Join-Path $Root "agent\_agent_version.py"
Set-Content -LiteralPath $AgentVersionFile -Value "VERSION = `"$Version`"`n" -Encoding UTF8

$VenvDir = Join-Path $BuildDir "venv"
python -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install pyinstaller
try {
  & $VenvPython -m PyInstaller --onefile --name mcpworld-agent --distpath $DistDir --workpath (Join-Path $BuildDir "pyinstaller-work") --specpath $BuildDir --paths (Join-Path $Root "agent") $AgentPy
} finally {
  # Keep the source tree clean; dev runs use the in-file fallback version.
  Remove-Item -LiteralPath $AgentVersionFile -Force -ErrorAction SilentlyContinue
}

$AgentExe = Join-Path $DistDir "mcpworld-agent.exe"
if (!(Test-Path -LiteralPath $AgentExe)) {
  throw "Missing built agent exe: $AgentExe"
}

$SetupExe = Join-Path $DistDir "MCPWorld-Agent-Setup.exe"
$SetupMsi = Join-Path $DistDir "MCPWorld-Agent-Setup.msi"

if (!$SkipInstallerTools) {
  $InnoCompiler = Get-Command iscc.exe -ErrorAction SilentlyContinue
  if ($InnoCompiler) {
    Invoke-CheckedNative $InnoCompiler.Source "/DMyAppVersion=$Version" "/O$DistDir" $InnoScript
  } else {
    Write-Warning "Inno Setup compiler was not found. Skipping EXE installer."
  }

  $Candle = Get-Command candle.exe -ErrorAction SilentlyContinue
  $Light = Get-Command light.exe -ErrorAction SilentlyContinue
  if ($Candle -and $Light) {
    $WixObj = Join-Path $BuildDir "MCPWorldAgent.wixobj"
    Invoke-CheckedNative $Candle.Source "-dProductVersion=$MsiProductVersion" "-dDistDir=$DistDir" "-out" $WixObj $WixScript
    Invoke-CheckedNative $Light.Source "-ext" "WixUIExtension" "-out" $SetupMsi $WixObj
  } else {
    Write-Warning "WiX Toolset was not found. Skipping MSI installer."
  }
}

$ShaPath = Join-Path $DistDir "SHA256SUMS.txt"
@($SetupExe, $SetupMsi) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
  $Item = Get-Item -LiteralPath $_
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Item.FullName).Hash.ToLowerInvariant()
  "$Hash  $($Item.Name)"
} | Set-Content -LiteralPath $ShaPath -Encoding UTF8

$ExeSha = if (Test-Path -LiteralPath $SetupExe) { (Get-FileHash -Algorithm SHA256 -LiteralPath $SetupExe).Hash.ToLowerInvariant() } else { "TBD_BUILD_ARTIFACT" }
$MsiSha = if (Test-Path -LiteralPath $SetupMsi) { (Get-FileHash -Algorithm SHA256 -LiteralPath $SetupMsi).Hash.ToLowerInvariant() } else { "TBD_BUILD_ARTIFACT" }
$Manifest = [ordered]@{
  channel = "beta"
  version = $Version
  minimumAgentVersion = $Version
  releasePage = "https://github.com/$GitHubRepo/releases/tag/v$Version"
  notes = "MCPWorld Agent release manifest. Public assets are installer-only for beta users."
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
  }
}
$Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $DistDir "latest.json") -Encoding UTF8
Write-Host "Built release files in $DistDir"
Get-ChildItem -LiteralPath $DistDir -File | Select-Object Name,Length | Format-Table -AutoSize
