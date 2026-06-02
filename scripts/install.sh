#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"

backup_if_exists() {
  local path="$1"
  if [[ -e "$path" && ! -L "$path" ]]; then
    mv "$path" "$path.bak.$STAMP"
    printf 'Backed up %s -> %s\n' "$path" "$path.bak.$STAMP"
  fi
}

replace_home_placeholders() {
  local target="$1"
  find "$target" -type f -print0 | xargs -0 perl -0pi -e "s#__HOME__#${HOME}#g"
}

mkdir -p "$HOME/.codex/skills"

backup_if_exists "$HOME/.ai-prompt"
mkdir -p "$HOME/.ai-prompt"
rsync -a --delete "$ROOT/ai-prompt/" "$HOME/.ai-prompt/"
replace_home_placeholders "$HOME/.ai-prompt"

rsync -a "$ROOT/codex-skills/" "$HOME/.codex/skills/"
replace_home_placeholders "$HOME/.codex/skills"

printf '\nInstalled prompt hub and Codex skills.\n'
printf 'Prompt hub: %s/.ai-prompt\n' "$HOME"
printf 'Codex skills: %s/.codex/skills\n' "$HOME"
printf '\nMCP config was not overwritten. Merge snippets from:\n'
printf '  %s/codex-config/mcp.example.toml\n' "$ROOT"

