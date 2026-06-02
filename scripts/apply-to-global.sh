#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$HOME/.ai-agent-workflow-backups/$STAMP"

replace_home_placeholders() {
  local target="$1"
  find "$target" -type f -print0 | xargs -0 perl -0pi -e "s#__HOME__#${HOME}#g"
}

mkdir -p "$BACKUP_DIR" "$HOME/.codex/skills"

if [[ -d "$HOME/.ai-prompt" ]]; then
  rsync -a "$HOME/.ai-prompt/" "$BACKUP_DIR/ai-prompt/"
fi

if [[ -d "$HOME/.codex/skills" ]]; then
  mkdir -p "$BACKUP_DIR/codex-skills"
  for skill_dir in "$ROOT"/codex-skills/*; do
    skill_name="$(basename "$skill_dir")"
    if [[ -d "$HOME/.codex/skills/$skill_name" ]]; then
      rsync -a "$HOME/.codex/skills/$skill_name/" "$BACKUP_DIR/codex-skills/$skill_name/"
    fi
  done
fi

rsync -a --delete \
  --exclude '.env' \
  --exclude 'runtime.conf' \
  "$ROOT/ai-prompt/" "$HOME/.ai-prompt/"
replace_home_placeholders "$HOME/.ai-prompt"

rsync -a "$ROOT/codex-skills/" "$HOME/.codex/skills/"
replace_home_placeholders "$HOME/.codex/skills"

printf 'Applied project workflow to global config.\n'
printf 'Backup: %s\n' "$BACKUP_DIR"
printf 'Prompt hub: %s/.ai-prompt\n' "$HOME"
printf 'Codex skills: %s/.codex/skills\n' "$HOME"

