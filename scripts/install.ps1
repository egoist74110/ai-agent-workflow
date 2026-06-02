param(
  [string]$HomeDir = $HOME
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "apply-to-global.ps1") -HomeDir $HomeDir

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$SkillTarget = if ($env:AI_AGENT_SKILLS_DIR) { $env:AI_AGENT_SKILLS_DIR } else { Join-Path $HomeDir ".ai-agent/skills" }
$AgentHome = if ($env:AI_AGENT_HOME) { $env:AI_AGENT_HOME } else { Join-Path $HomeDir ".ai-agent" }
$RouterPath = Join-Path $HomeDir ".ai-prompt/router.md"

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
      Write-Host "Unknown MCP selection skipped: $Item"
      continue
    }

    $Text = [System.IO.File]::ReadAllText($Snippet).Replace("__HOME__", $HomeDir)
    [System.IO.File]::AppendAllText($Output, "`n# $Item`n$Text`n", $Utf8NoBom)
    $Wrote = $true
  }

  if ($Wrote) {
    Write-Host "Selected MCP snippets: $Output"
    Write-Host "Merge this file into each runtime MCP config after checking paths."
  } else {
    if (Test-Path $Output) { Remove-Item -LiteralPath $Output -Force }
    Write-Host "No MCP snippets selected."
  }
}

function Configure-McpSelection {
  if ($env:AI_AGENT_MCP_SELECTIONS) {
    Write-McpSelection -Selections $env:AI_AGENT_MCP_SELECTIONS
    return
  }

  if ($env:AI_AGENT_NONINTERACTIVE -eq "1" -or [Console]::IsInputRedirected) {
    Write-Host "MCP selection skipped in non-interactive mode. Set AI_AGENT_MCP_SELECTIONS to choose snippets."
    return
  }

  Write-Host ""
  Write-Host "Optional MCP snippets:"
  Write-Host "  1) serena"
  Write-Host "  2) chrome-devtools"
  Write-Host "  3) ado-work-items"
  $Selections = Read-Host 'Choose numbers separated by commas, "all", or press Enter for none'
  if (-not $Selections) { $Selections = "none" }
  Write-McpSelection -Selections $Selections
}

function Write-EntrypointFile {
  param([string]$Target)

  if (-not $Target) { return }
  if ($Target.StartsWith("~")) {
    $Target = Join-Path $HomeDir $Target.Substring(1).TrimStart([char[]]"\/")
  }

  $Parent = Split-Path -Parent $Target
  if ($Parent) {
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
  }
  if (Test-Path $Target) {
    Copy-Item -LiteralPath $Target -Destination "$Target.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
  }

  [System.IO.File]::WriteAllText($Target, "Read $RouterPath first, then follow it.`n", (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "Entrypoint written: $Target"
}

function Get-RuntimeEntrypointDefault {
  param([string]$Runtime)

  switch ($Runtime) {
    "claude" { return (Join-Path $HomeDir ".claude/CLAUDE.md") }
    "codex" { return (Join-Path $HomeDir ".codex/AGENTS.md") }
    "agy" { return (Join-Path $HomeDir ".gemini/GEMINI.md") }
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
    "4" { return "custom" }
    default { return $Runtime }
  }
}

function Configure-RuntimeAdaptersNonInteractive {
  param([string]$Selections)

  if ($Selections.Trim().ToLowerInvariant() -eq "all") {
    $Selections = "claude,codex,agy"
  }

  $Selections.Split(",") | ForEach-Object {
    $Runtime = Normalize-RuntimeSelection -Runtime $_
    switch ($Runtime) {
      { $_ -eq "" -or $_ -eq "none" } { break }
      "claude" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) }
      "codex" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) }
      "agy" { Write-EntrypointFile -Target (Get-RuntimeEntrypointDefault -Runtime $Runtime) }
      "custom" { Write-Host "Custom runtime selected; set AI_AGENT_ENTRYPOINTS with semicolon-separated paths." }
      default { Write-Host "Unknown runtime selection skipped: $Runtime" }
    }
  }
}

function Configure-Entrypoints {
  $PointerDir = Join-Path $AgentHome "entrypoints"
  $Configured = $false
  New-Item -ItemType Directory -Force -Path $PointerDir | Out-Null
  [System.IO.File]::WriteAllText((Join-Path $PointerDir "router-pointer.md"), "Read $RouterPath first, then follow it.`n", (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "Shared entrypoint pointer: $(Join-Path $PointerDir 'router-pointer.md')"

  if ($env:AI_AGENT_RUNTIMES) {
    Configure-RuntimeAdaptersNonInteractive -Selections $env:AI_AGENT_RUNTIMES
    $Configured = $true
  }

  if ($env:AI_AGENT_ENTRYPOINTS) {
    $env:AI_AGENT_ENTRYPOINTS.Split(";") | ForEach-Object { Write-EntrypointFile -Target $_.Trim() }
    $Configured = $true
  }

  if ($Configured) {
    return
  }

  if ($env:AI_AGENT_NONINTERACTIVE -eq "1" -or [Console]::IsInputRedirected) {
    Write-Host "Native runtime setup skipped in non-interactive mode. Set AI_AGENT_RUNTIMES or AI_AGENT_ENTRYPOINTS."
    return
  }

  Write-Host ""
  Write-Host "Connect AI runtimes to the deployed router:"
  Write-Host "  1) claude  -> ~/.claude/CLAUDE.md"
  Write-Host "  2) codex   -> ~/.codex/AGENTS.md"
  Write-Host "  3) agy     -> ~/.gemini/GEMINI.md"
  Write-Host "  4) custom path"
  $RuntimeSelections = Read-Host 'Choose numbers separated by commas, "all", or press Enter to skip'
  if (-not $RuntimeSelections) { return }
  if ($RuntimeSelections.Trim().ToLowerInvariant() -eq "all") {
    $RuntimeSelections = "claude,codex,agy"
  }

  $RuntimeSelections.Split(",") | ForEach-Object {
    $Runtime = Normalize-RuntimeSelection -Runtime $_
    switch ($Runtime) {
      "claude" {
        $DefaultPath = Get-RuntimeEntrypointDefault -Runtime $Runtime
        Write-EntrypointFile -Target $DefaultPath
      }
      "codex" {
        $DefaultPath = Get-RuntimeEntrypointDefault -Runtime $Runtime
        Write-EntrypointFile -Target $DefaultPath
      }
      "agy" {
        $DefaultPath = Get-RuntimeEntrypointDefault -Runtime $Runtime
        Write-EntrypointFile -Target $DefaultPath
      }
      "custom" {
        $Target = Read-Host "Custom entrypoint path"
        Write-EntrypointFile -Target $Target
      }
      { $_ -eq "" -or $_ -eq "none" } {}
      default { Write-Host "Unknown runtime selection skipped: $Runtime" }
    }
  }
}

Write-Host ""
Write-Host "Installed prompt hub and runtime skills."
Write-Host "Prompt hub: $(Join-Path $HomeDir '.ai-prompt')"
Write-Host "Runtime skills: $SkillTarget"
Write-Host "Router: $RouterPath"

Configure-McpSelection
Configure-Entrypoints

Write-Host ""
Write-Host "MCP config was not overwritten automatically."
Write-Host "Available snippets: $(Join-Path $Root 'ai-config/mcp')"
