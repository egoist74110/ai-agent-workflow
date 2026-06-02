#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$HOME/.ai-agent-workflow-backups/$STAMP"
SKILLS_DIR="${AI_AGENT_SKILLS_DIR:-$HOME/.ai-agent/skills}"

replace_home_placeholders() {
  local target="$1"
  HOME_REPLACEMENT="$HOME" find "$target" -type f -print0 | xargs -0 env HOME_REPLACEMENT="$HOME" perl -0pi -e 's#__HOME__#$ENV{HOME_REPLACEMENT}#g'
}

mkdir -p "$BACKUP_DIR" "$SKILLS_DIR"

if [[ -d "$HOME/.ai-prompt" ]]; then
  rsync -a "$HOME/.ai-prompt/" "$BACKUP_DIR/ai-prompt/"
fi

if [[ -d "$SKILLS_DIR" ]]; then
  mkdir -p "$BACKUP_DIR/ai-skills"
  for skill_dir in "$ROOT"/ai-skills/*; do
    skill_name="$(basename "$skill_dir")"
    if [[ -d "$SKILLS_DIR/$skill_name" ]]; then
      rsync -a "$SKILLS_DIR/$skill_name/" "$BACKUP_DIR/ai-skills/$skill_name/"
    fi
  done
fi

rsync -a --delete \
  --exclude '.env' \
  --exclude 'runtime.conf' \
  "$ROOT/ai-prompt/" "$HOME/.ai-prompt/"
replace_home_placeholders "$HOME/.ai-prompt"

rsync -a "$ROOT/ai-skills/" "$SKILLS_DIR/"
replace_home_placeholders "$SKILLS_DIR"

printf '已应用项目工作流到本机全局目录。\n'
printf '备份目录：%s\n' "$BACKUP_DIR"
printf '提示词目录：%s/.ai-prompt\n' "$HOME"
printf 'Skills 目录：%s\n' "$SKILLS_DIR"
