# 薄壳：实际逻辑全在 installer.py（唯一实现，跨平台共用）。
$ErrorActionPreference = "Stop"

$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Py = $null
foreach ($candidate in @("python3", "python", "py")) {
  $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($cmd) { $Py = $cmd.Source; break }
}
if (-not $Py) {
  Write-Error "需要 python3 才能运行安装器，请先安装 Python 3。"
  exit 1
}

& $Py (Join-Path $Dir "installer.py") install
exit $LASTEXITCODE
