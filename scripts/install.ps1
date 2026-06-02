param(
  [string]$HomeDir = $HOME
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "apply-to-global.ps1") -HomeDir $HomeDir

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host ""
Write-Host "Installed prompt hub and runtime skills."
Write-Host "Prompt hub: $(Join-Path $HomeDir '.ai-prompt')"
Write-Host "Runtime skills: $(Join-Path $HomeDir '.codex/skills')"
Write-Host ""
Write-Host "MCP config was not overwritten. Add MCP tools only after user confirmation."
Write-Host "Merge snippets from:"
Write-Host "  $(Join-Path $Root 'codex-config/mcp.example.toml')"
