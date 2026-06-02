#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "$ROOT/scripts/apply-to-global.sh"

printf '\nInstalled prompt hub and runtime skills.\n'
printf 'Prompt hub: %s/.ai-prompt\n' "$HOME"
printf 'Runtime skills: %s/.codex/skills\n' "$HOME"
printf '\nMCP config was not overwritten. Add MCP tools only after user confirmation.\n'
printf 'Merge snippets from:\n'
printf '  %s/codex-config/mcp.example.toml\n' "$ROOT"
