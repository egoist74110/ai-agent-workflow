param(
  [string]$HomeDir = $HOME
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $HomeDir ".ai-agent-workflow-backups/$Stamp"
$PromptTarget = Join-Path $HomeDir ".ai-prompt"
$SkillTarget = if ($env:AI_AGENT_SKILLS_DIR) { $env:AI_AGENT_SKILLS_DIR } else { Join-Path $HomeDir ".ai-agent/skills" }

function Copy-Directory {
  param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination,
    [switch]$Mirror
  )

  New-Item -ItemType Directory -Force -Path $Destination | Out-Null

  if ($Mirror) {
    robocopy $Source $Destination /MIR /XD ".git" /XF ".env" "runtime.conf" | Out-Null
    if ($LASTEXITCODE -le 7) { $global:LASTEXITCODE = 0 } else { throw "robocopy failed with exit code $LASTEXITCODE" }
  } else {
    robocopy $Source $Destination /E /XD ".git" /XF ".env" "runtime.conf" | Out-Null
    if ($LASTEXITCODE -le 7) { $global:LASTEXITCODE = 0 } else { throw "robocopy failed with exit code $LASTEXITCODE" }
  }
}

function Replace-HomePlaceholders {
  param([Parameter(Mandatory = $true)][string]$Target)

  if (-not (Test-Path $Target)) { return }

  $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

  Get-ChildItem -Path $Target -Recurse -File | ForEach-Object {
    $text = [System.IO.File]::ReadAllText($_.FullName)
    if ($text -like "*__HOME__*") {
      [System.IO.File]::WriteAllText($_.FullName, $text.Replace("__HOME__", $HomeDir), $Utf8NoBom)
    }
  }
}

New-Item -ItemType Directory -Force -Path $BackupDir, $SkillTarget | Out-Null

if (Test-Path $PromptTarget) {
  Copy-Directory -Source $PromptTarget -Destination (Join-Path $BackupDir "ai-prompt")
}

if (Test-Path $SkillTarget) {
  $SkillBackup = Join-Path $BackupDir "ai-skills"
  New-Item -ItemType Directory -Force -Path $SkillBackup | Out-Null
  Get-ChildItem -Path (Join-Path $Root "ai-skills") -Directory | ForEach-Object {
    $ExistingSkill = Join-Path $SkillTarget $_.Name
    if (Test-Path $ExistingSkill) {
      Copy-Directory -Source $ExistingSkill -Destination (Join-Path $SkillBackup $_.Name)
    }
  }
}

Copy-Directory -Source (Join-Path $Root "ai-prompt") -Destination $PromptTarget -Mirror
Replace-HomePlaceholders -Target $PromptTarget

Copy-Directory -Source (Join-Path $Root "ai-skills") -Destination $SkillTarget
Replace-HomePlaceholders -Target $SkillTarget

Write-Host "已应用项目工作流到本机全局目录。"
Write-Host "备份目录：$BackupDir"
Write-Host "提示词目录：$PromptTarget"
Write-Host "Skills 目录：$SkillTarget"
