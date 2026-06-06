# repatch_blendermcp.ps1
# repatch_blendermcp.py 를 실행하고 결과를 로그에 남긴다.
# 작업 스케줄러(로그온 시)에 등록해 BlenderMCP 업데이트 후 자동 복구하는 용도.

$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "repatch_blendermcp.py"
$log    = Join-Path $here "repatch_blendermcp.log"

if (-not (Test-Path $script)) {
    "$(Get-Date -Format s)  ERROR: $script not found" | Add-Content -Path $log -Encoding utf8
    exit 1
}

# python 실행기 탐색: py 런처 우선, 없으면 python
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pyCmd) {
    $exe = "py"; $pyArgs = @("-3", $script)
} else {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) {
        "$(Get-Date -Format s)  ERROR: python/py not found on PATH" | Add-Content -Path $log -Encoding utf8
        exit 1
    }
    $exe = "python"; $pyArgs = @($script)
}

$out  = & $exe @pyArgs 2>&1 | Out-String
$code = $LASTEXITCODE

"$(Get-Date -Format s)  exit=$code`n$out" | Add-Content -Path $log -Encoding utf8
# 콘솔에도 출력(수동 실행 시 확인용)
Write-Output $out
exit $code
