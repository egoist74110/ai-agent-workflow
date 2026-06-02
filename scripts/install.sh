#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${AI_AGENT_SKILLS_DIR:-$HOME/.ai-agent/skills}"
AGENT_HOME="${AI_AGENT_HOME:-$HOME/.ai-agent}"
ROUTER_PATH="$HOME/.ai-prompt/router.md"

replace_home_placeholders_in_file() {
  local source="$1"
  HOME_REPLACEMENT="$HOME" perl -pe 's#__HOME__#$ENV{HOME_REPLACEMENT}#g' "$source"
}

write_mcp_selection() {
  local selections="$1"
  local output="$AGENT_HOME/mcp.selected.toml"
  local wrote=false

  mkdir -p "$AGENT_HOME"
  : > "$output"

  IFS=',' read -r -a items <<< "$selections"
  for item in "${items[@]}"; do
    item="$(printf '%s' "$item" | tr -d '[:space:]')"
    case "$item" in
      "1") item="serena" ;;
      "2") item="chrome-devtools" ;;
      "3") item="ado-work-items" ;;
    esac
    case "$item" in
      ""|"none") ;;
      "all")
        write_mcp_selection "serena,chrome-devtools,ado-work-items"
        return
        ;;
      "serena"|"chrome-devtools"|"ado-work-items")
        {
          printf '\n# %s\n' "$item"
          replace_home_placeholders_in_file "$ROOT/ai-config/mcp/$item.toml"
        } >> "$output"
        wrote=true
        ;;
      *)
        printf 'Unknown MCP selection skipped: %s\n' "$item"
        ;;
    esac
  done

  if [[ "$wrote" == true ]]; then
    printf 'Selected MCP snippets: %s\n' "$output"
    printf 'Merge this file into each runtime MCP config after checking paths.\n'
  else
    rm -f "$output"
    printf 'No MCP snippets selected.\n'
  fi
}

configure_mcp_selection() {
  if [[ -n "${AI_AGENT_MCP_SELECTIONS:-}" ]]; then
    write_mcp_selection "$AI_AGENT_MCP_SELECTIONS"
    return
  fi

  if [[ ! -t 0 ]]; then
    printf 'MCP selection skipped in non-interactive mode. Set AI_AGENT_MCP_SELECTIONS to choose snippets.\n'
    return
  fi

  printf '\nOptional MCP snippets:\n'
  printf '  1) serena\n'
  printf '  2) chrome-devtools\n'
  printf '  3) ado-work-items\n'
  printf 'Enter names separated by commas, "all", or press Enter for none: '
  read -r selections
  write_mcp_selection "${selections:-none}"
}

write_entrypoint_file() {
  local target="$1"
  local pointer="Read $ROUTER_PATH first, then follow it."

  [[ -z "$target" ]] && return
  target="${target/#\~/$HOME}"
  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]]; then
    cp "$target" "$target.bak.$(date +%Y%m%d-%H%M%S)"
  fi
  printf '%s\n' "$pointer" > "$target"
  printf 'Entrypoint written: %s\n' "$target"
}

configure_entrypoints() {
  local pointer_dir="$AGENT_HOME/entrypoints"
  mkdir -p "$pointer_dir"
  printf 'Read %s first, then follow it.\n' "$ROUTER_PATH" > "$pointer_dir/router-pointer.md"
  printf 'Shared entrypoint pointer: %s/router-pointer.md\n' "$pointer_dir"

  if [[ -n "${AI_AGENT_ENTRYPOINTS:-}" ]]; then
    IFS=';' read -r -a targets <<< "$AI_AGENT_ENTRYPOINTS"
    for target in "${targets[@]}"; do
      write_entrypoint_file "$target"
    done
    return
  fi

  if [[ ! -t 0 ]]; then
    printf 'Native entrypoint setup skipped in non-interactive mode. Set AI_AGENT_ENTRYPOINTS to semicolon-separated file paths.\n'
    return
  fi

  printf '\nTo make an AI runtime load this workflow, enter the native instruction file path it already reads.\n'
  printf 'Leave empty when finished. Existing files are backed up before being replaced.\n'
  while true; do
    printf 'Entrypoint path: '
    read -r target
    [[ -z "$target" ]] && break
    write_entrypoint_file "$target"
  done
}

bash "$ROOT/scripts/apply-to-global.sh"

printf '\nInstalled prompt hub and runtime skills.\n'
printf 'Prompt hub: %s/.ai-prompt\n' "$HOME"
printf 'Runtime skills: %s\n' "$SKILLS_DIR"
printf 'Router: %s\n' "$ROUTER_PATH"

configure_mcp_selection
configure_entrypoints

printf '\nMCP config was not overwritten automatically.\n'
printf 'Available snippets: %s/ai-config/mcp/\n' "$ROOT"
