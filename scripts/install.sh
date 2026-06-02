#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${AI_AGENT_SKILLS_DIR:-$HOME/.ai-agent/skills}"
AGENT_HOME="${AI_AGENT_HOME:-$HOME/.ai-agent}"
ROUTER_PATH="$HOME/.ai-prompt/router.md"

python_command() {
  if command -v python3 >/dev/null 2>&1; then
    printf 'python3\n'
  elif command -v python >/dev/null 2>&1; then
    printf 'python\n'
  else
    return 1
  fi
}

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
        printf '未知 MCP 选项已跳过：%s\n' "$item"
        ;;
    esac
  done

  if [[ "$wrote" == true ]]; then
    printf '已生成 MCP 片段：%s\n' "$output"
    printf '请检查路径后，再合并到对应 AI 的 MCP 配置。\n'
  else
    rm -f "$output"
    printf '未选择 MCP。\n'
  fi
}

configure_mcp_selection() {
  local picker_output py selections

  if [[ -n "${AI_AGENT_MCP_SELECTIONS:-}" ]]; then
    write_mcp_selection "$AI_AGENT_MCP_SELECTIONS"
    return
  fi

  if [[ ! -t 0 ]]; then
    printf '非交互模式：已跳过 MCP 选择。可设置 AI_AGENT_MCP_SELECTIONS 指定。\n'
    return
  fi

  if py="$(python_command)" && picker_output="$("$py" "$ROOT/scripts/terminal_picker.py" mcp)"; then
    selections="$(printf '%s\n' "$picker_output" | awk -F '\t' '$1=="mcp"{print $2}' | paste -sd ',' -)"
    write_mcp_selection "${selections:-none}"
    return
  fi

  printf '\n选择要准备的 MCP：\n'
  printf '  1) serena\n'
  printf '  2) chrome-devtools\n'
  printf '  3) ado-work-items\n'
  printf '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过：'
  read -r selections
  write_mcp_selection "${selections:-none}"
}

write_entrypoint_file() {
  local target="$1"
  local name="${2:-}"
  local pointer="Read $ROUTER_PATH first, then follow it."

  [[ -z "$target" ]] && return
  target="${target/#\~/$HOME}"
  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]]; then
    cp "$target" "$target.bak.$(date +%Y%m%d-%H%M%S)"
  fi
  printf '%s\n' "$pointer" > "$target"
  if [[ -n "$name" ]]; then
    printf '已写入 %s 入口：%s\n' "$name" "$target"
  else
    printf '已写入入口：%s\n' "$target"
  fi
}

runtime_default_entrypoint() {
  local runtime="$1"
  case "$runtime" in
    "claude") printf '%s/.claude/CLAUDE.md\n' "$HOME" ;;
    "codex") printf '%s/.codex/AGENTS.md\n' "$HOME" ;;
    "agy") printf '%s/.gemini/GEMINI.md\n' "$HOME" ;;
    *) return 1 ;;
  esac
}

normalize_runtime_selection() {
  local item="$1"
  item="$(printf '%s' "$item" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$item" in
    "1") item="claude" ;;
    "2") item="codex" ;;
    "3") item="agy" ;;
    "4") item="custom" ;;
  esac
  printf '%s\n' "$item"
}

configure_runtime_adapters_noninteractive() {
  local selections="$1"
  local runtime default_path

  if [[ "$selections" == "all" ]]; then
    selections="claude,codex,agy"
  fi

  IFS=',' read -r -a runtimes <<< "$selections"
  for runtime in "${runtimes[@]}"; do
    runtime="$(normalize_runtime_selection "$runtime")"
    case "$runtime" in
      ""|"none") ;;
      "all")
        configure_runtime_adapters_noninteractive "claude,codex,agy"
        ;;
      "claude"|"codex"|"agy")
        default_path="$(runtime_default_entrypoint "$runtime")"
        write_entrypoint_file "$default_path" "$runtime"
        ;;
      "custom")
        printf '已选择自定义运行时；请用 AI_AGENT_ENTRYPOINTS 指定路径，或在交互模式里选择自定义添加。\n'
        ;;
      *)
        printf '未知 AI 选项已跳过：%s\n' "$runtime"
        ;;
    esac
  done
}

configure_entrypoints() {
  local pointer_dir="$AGENT_HOME/entrypoints"
  local configured=false
  local picker_output py line kind id name target runtime_selections default_path target
  mkdir -p "$pointer_dir"
  printf 'Read %s first, then follow it.\n' "$ROUTER_PATH" > "$pointer_dir/router-pointer.md"
  printf '共享入口指针：%s/router-pointer.md\n' "$pointer_dir"

  if [[ -n "${AI_AGENT_RUNTIMES:-}" ]]; then
    configure_runtime_adapters_noninteractive "$AI_AGENT_RUNTIMES"
    configured=true
  fi

  if [[ -n "${AI_AGENT_ENTRYPOINTS:-}" ]]; then
    IFS=';' read -r -a targets <<< "$AI_AGENT_ENTRYPOINTS"
    for target in "${targets[@]}"; do
      write_entrypoint_file "$target" "custom"
    done
    configured=true
  fi

  if [[ "$configured" == true ]]; then
    return
  fi

  if [[ ! -t 0 ]]; then
    printf '非交互模式：已跳过 AI 接入。可设置 AI_AGENT_RUNTIMES 或 AI_AGENT_ENTRYPOINTS 指定。\n'
    return
  fi

  if py="$(python_command)" && picker_output="$("$py" "$ROOT/scripts/terminal_picker.py" runtime)"; then
    while IFS=$'\t' read -r kind id name target; do
      [[ "$kind" != "runtime" ]] && continue
      write_entrypoint_file "$target" "$name"
    done <<< "$picker_output"
    return
  fi

  printf '\n选择要接入的 AI：\n'
  printf '  1) Claude  -> ~/.claude/CLAUDE.md\n'
  printf '  2) Codex   -> ~/.codex/AGENTS.md\n'
  printf '  3) Antigravity CLI (agy) -> ~/.gemini/GEMINI.md\n'
  printf '  4) 自定义路径\n'
  printf '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过：'
  read -r runtime_selections
  [[ -z "$runtime_selections" ]] && return
  runtime_selections="$(printf '%s' "$runtime_selections" | tr -d '[:space:]')"
  if [[ "$runtime_selections" == "all" ]]; then
    runtime_selections="claude,codex,agy"
  fi

  IFS=',' read -r -a runtimes <<< "$runtime_selections"
  for runtime in "${runtimes[@]}"; do
    runtime="$(normalize_runtime_selection "$runtime")"
    case "$runtime" in
      "claude"|"codex"|"agy")
        default_path="$(runtime_default_entrypoint "$runtime")"
        write_entrypoint_file "$default_path" "$runtime"
        ;;
      "custom")
        printf '自定义 AI 名称：'
        read -r name
        printf '自定义入口文件路径：'
        read -r target
        write_entrypoint_file "$target" "${name:-custom}"
        ;;
      ""|"none") ;;
      *)
        printf '未知 AI 选项已跳过：%s\n' "$runtime"
        ;;
    esac
  done
}

bash "$ROOT/scripts/apply-to-global.sh"

printf '\n已安装统一提示词和运行时 skills。\n'
printf '提示词目录：%s/.ai-prompt\n' "$HOME"
printf 'Skills 目录：%s\n' "$SKILLS_DIR"
printf 'Router: %s\n' "$ROUTER_PATH"

configure_mcp_selection
configure_entrypoints

printf '\n不会自动覆盖任何 AI 的 MCP 配置。\n'
printf '可用 MCP 片段：%s/ai-config/mcp/\n' "$ROOT"
