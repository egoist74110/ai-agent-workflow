param(
  [string]$HomeDir = $HOME
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "apply-to-global.ps1") -HomeDir $HomeDir

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$SkillTarget = if ($env:AI_AGENT_SKILLS_DIR) { $env:AI_AGENT_SKILLS_DIR } else { Join-Path $HomeDir ".ai-agent/skills" }
$AgentHome = if ($env:AI_AGENT_HOME) { $env:AI_AGENT_HOME } else { Join-Path $HomeDir ".ai-agent" }
$RouterPath = Join-Path $HomeDir ".ai-prompt/router.md"

function Get-PythonCommand {
  foreach ($candidate in @("python3", "python", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
  }
  return $null
}

function Write-McpSelection {
  param([string]$Selections)

  $Output = Join-Path $AgentHome "mcp.selected.toml"
  New-Item -ItemType Directory -Force -Path $AgentHome | Out-Null
  if (Test-Path $Output) { Remove-Item -LiteralPath $Output -Force }

  $Items = $Selections.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  if ($Items -contains "all") {
    $Items = @("serena", "chrome-devtools", "ado-work-items")
  }

  $Wrote = $false
  $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

  foreach ($Item in $Items) {
    if ($Item -eq "1") { $Item = "serena" }
    elseif ($Item -eq "2") { $Item = "chrome-devtools" }
    elseif ($Item -eq "3") { $Item = "ado-work-items" }

    if ($Item -eq "none") { continue }

    $Snippet = Join-Path $Root "ai-config/mcp/$Item.toml"
    if (-not (Test-Path $Snippet)) {
      Write-Host "未知 MCP 选项已跳过：$Item"
      continue
    }

    $Text = [System.IO.File]::ReadAllText($Snippet).Replace("__HOME__", $HomeDir)
    [System.IO.File]::AppendAllText($Output, "`n# $Item`n$Text`n", $Utf8NoBom)
    $Wrote = $true
  }

  if ($Wrote) {
    Write-Host "已生成 MCP 片段：$Output"
    Write-Host "请检查路径后，再合并到对应 AI 的 MCP 配置。"
  } else {
    if (Test-Path $Output) { Remove-Item -LiteralPath $Output -Force }
    Write-Host "未选择 MCP。"
  }
}

function Write-EntrypointFile {
  param(
    [string]$Target,
    [string]$DisplayName = ""
  )

  if (-not $Target) { return }
  if ($Target.StartsWith("~")) {
    $Target = Join-Path $HomeDir $Target.Substring(1).TrimStart([char[]]"\/")
  }

  if (Test-Path -LiteralPath $Target -PathType Container) {
    Write-Host "⚠️  入口必须是文件，但 $Target 是目录，已跳过。请填具体的指令文件，例如 $Target/AGENTS.md"
    return
  }

  $Parent = Split-Path -Parent $Target
  if ($Parent) {
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
  }
  if (Test-Path $Target) {
    Copy-Item -LiteralPath $Target -Destination "$Target.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
  }

  [System.IO.File]::WriteAllText($Target, "Read $RouterPath first, then follow it.`n", (New-Object System.Text.UTF8Encoding($false)))
  if ($DisplayName) {
    Write-Host "已写入 $DisplayName 入口：$Target"
  } else {
    Write-Host "已写入入口：$Target"
  }
}

function Get-RuntimeEntrypointDefault {
  param([string]$Runtime)

  switch ($Runtime) {
    "claude" { return (Join-Path $HomeDir ".claude/CLAUDE.md") }
    "codex" { return (Join-Path $HomeDir ".codex/AGENTS.md") }
    "agy" { return (Join-Path $HomeDir ".gemini/GEMINI.md") }
    "opencode" { return (Join-Path $HomeDir ".config/opencode/AGENTS.md") }
    default { return $null }
  }
}

function Normalize-RuntimeSelection {
  param([string]$Runtime)

  $Runtime = $Runtime.Trim().ToLowerInvariant()
  switch ($Runtime) {
    "1" { return "claude" }
    "2" { return "codex" }
    "3" { return "agy" }
    "4" { return "opencode" }
    "5" { return "custom" }
    default { return $Runtime }
  }
}

function Configure-RuntimeAdaptersNonInteractive {
  param([string]$Selections)

  if ($Selections.Trim().ToLowerInvariant() -eq "all") {
    $Selections = "claude,codex,agy,opencode"
  }

  $Selections.Split(",") | ForEach-Object {
    $Runtime = Normalize-RuntimeSelection -Runtime $_
    switch ($Runtime) {
      { $_ -eq "" -or $_ -eq "none" } { break }
      "claude" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Claude" }
      "codex" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Codex" }
      "agy" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Antigravity CLI" }
      "opencode" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "opencode" }
      "custom" { Write-Host "已选择自定义运行时；请用 AI_AGENT_ENTRYPOINTS 指定路径，或在交互模式里选择自定义添加。" }
      default { Write-Host "未知 AI 选项已跳过：$Runtime" }
    }
  }
}

# 统一的 curses 选择器：一次调用同时处理 MCP 与 AI。返回 $false 表示无法启动 TUI。
function Invoke-UnifiedPicker {
  param([string]$Sections)

  $Py = Get-PythonCommand
  if (-not $Py) { return $false }
  $Picker = Join-Path $Root "scripts/terminal_picker.py"
  if (-not (Test-Path $Picker)) { return $false }

  $Lines = & $Py $Picker $Sections
  if ($LASTEXITCODE -ne 0) { return $false }

  $McpIds = @()
  foreach ($Line in $Lines) {
    if (-not $Line) { continue }
    $Parts = $Line -split "`t"
    switch ($Parts[0]) {
      "mcp" { if ($Parts.Count -ge 2 -and $Parts[1]) { $McpIds += $Parts[1] } }
      "runtime" { if ($Parts.Count -ge 4) { Write-EntrypointFile -Target $Parts[3] -DisplayName $Parts[2] } }
    }
  }

  if ($Sections -match "mcp") {
    if ($McpIds.Count -gt 0) { Write-McpSelection -Selections ($McpIds -join ",") }
    else { Write-McpSelection -Selections "none" }
  }
  return $true
}

function Invoke-FallbackMcpMenu {
  Write-Host ""
  Write-Host "选择要准备的 MCP："
  Write-Host "  1) serena"
  Write-Host "  2) chrome-devtools"
  Write-Host "  3) ado-work-items"
  $Selections = Read-Host '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过'
  if (-not $Selections) { $Selections = "none" }
  Write-McpSelection -Selections $Selections
}

function Invoke-FallbackRuntimeMenu {
  Write-Host ""
  Write-Host "选择要接入的 AI："
  Write-Host "  1) Claude  -> ~/.claude/CLAUDE.md"
  Write-Host "  2) Codex   -> ~/.codex/AGENTS.md"
  Write-Host "  3) Antigravity CLI (agy) -> ~/.gemini/GEMINI.md"
  Write-Host "  4) opencode -> ~/.config/opencode/AGENTS.md"
  Write-Host "  5) 自定义路径"
  $RuntimeSelections = Read-Host '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过'
  if (-not $RuntimeSelections) { return }
  if ($RuntimeSelections.Trim().ToLowerInvariant() -eq "all") {
    $RuntimeSelections = "claude,codex,agy,opencode"
  }

  $RuntimeSelections.Split(",") | ForEach-Object {
    $Runtime = Normalize-RuntimeSelection -Runtime $_
    switch ($Runtime) {
      "claude" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Claude" }
      "codex" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Codex" }
      "agy" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "Antigravity CLI" }
      "opencode" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) -DisplayName "opencode" }
      "custom" {
        $Name = Read-Host "自定义 AI 名称"
        $Target = Read-Host "自定义入口文件路径"
        Write-EntrypointFile -Target $Target -DisplayName $Name
      }
      { $_ -eq "" -or $_ -eq "none" } {}
      default { Write-Host "未知 AI 选项已跳过：$Runtime" }
    }
  }
}

function Configure {
  $PointerDir = Join-Path $AgentHome "entrypoints"
  New-Item -ItemType Directory -Force -Path $PointerDir | Out-Null
  [System.IO.File]::WriteAllText((Join-Path $PointerDir "router-pointer.md"), "Read $RouterPath first, then follow it.`n", (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "共享入口指针：$(Join-Path $PointerDir 'router-pointer.md')"

  $NeedMcp = $true
  $NeedRt = $true

  if ($env:AI_AGENT_MCP_SELECTIONS) {
    Write-McpSelection -Selections $env:AI_AGENT_MCP_SELECTIONS
    $NeedMcp = $false
  }
  if ($env:AI_AGENT_RUNTIMES) {
    Configure-RuntimeAdaptersNonInteractive -Selections $env:AI_AGENT_RUNTIMES
    $NeedRt = $false
  }
  if ($env:AI_AGENT_ENTRYPOINTS) {
    $env:AI_AGENT_ENTRYPOINTS.Split(";") | ForEach-Object { Write-EntrypointFile -Target $_.Trim() -DisplayName "custom" }
    $NeedRt = $false
  }

  if (-not $NeedMcp -and -not $NeedRt) { return }

  if ($env:AI_AGENT_NONINTERACTIVE -eq "1" -or [Console]::IsInputRedirected) {
    if ($NeedMcp) { Write-Host "非交互模式：已跳过 MCP 选择。可设置 AI_AGENT_MCP_SELECTIONS 指定。" }
    if ($NeedRt) { Write-Host "非交互模式：已跳过 AI 接入。可设置 AI_AGENT_RUNTIMES 或 AI_AGENT_ENTRYPOINTS 指定。" }
    return
  }

  $Sections = @()
  if ($NeedMcp) { $Sections += "mcp" }
  if ($NeedRt) { $Sections += "runtime" }

  if (Invoke-UnifiedPicker -Sections ($Sections -join ",")) { return }

  # 无 python / curses 时回退到文本菜单（Windows 默认无 curses）。
  if ($NeedMcp) { Invoke-FallbackMcpMenu }
  if ($NeedRt) { Invoke-FallbackRuntimeMenu }
}

Write-Host ""
Write-Host "已安装统一提示词和运行时 skills。"
Write-Host "提示词目录：$(Join-Path $HomeDir '.ai-prompt')"
Write-Host "Skills 目录：$SkillTarget"
Write-Host "Router: $RouterPath"

Configure

Write-Host ""
Write-Host "不会自动覆盖任何 AI 的 MCP 配置。"
Write-Host "可用 MCP 片段：$(Join-Path $Root 'ai-config/mcp')"
