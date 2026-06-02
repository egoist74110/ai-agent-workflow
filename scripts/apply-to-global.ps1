# 薄壳：实际逻辑全在 installer.py。仅把 ai-prompt（含 skills）同步到全局目录。
$ErrorActionPreference = "Stop"

$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Py = $null
foreach ($candidate in @("python3", "python", "py")) {
  $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($cmd) { $Py = $cmd.Source; break }
}
if (-not $Py) {
  Write-Error "需要 python3 才能运行，请先安装 Python 3。"
  exit 1
}

& $Py (Join-Path $Dir "installer.py") apply
exit $LASTEXITCODE
