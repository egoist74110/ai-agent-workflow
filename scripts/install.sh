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
  HOME_REPLACEMENT="$HOME" perl -pe 's#__HOME__#$ENV{HOME_REPLACEMENT}#g' "$1"
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

write_entrypoint_file() {
  local target="$1"
  local name="${2:-}"
  local pointer="Read $ROUTER_PATH first, then follow it."

  [[ -z "$target" ]] && return
  target="${target/#\~/$HOME}"
  if [[ -d "$target" ]]; then
    printf '⚠️  入口必须是文件，但 %s 是目录，已跳过。请填具体的指令文件，例如 %s/AGENTS.md\n' "$target" "${target%/}"
    return 1
  fi
  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]]; then
    cp "$target" "$target.bak.$(date +%Y%m%d-%H%M%S)"
  fi
  if ! printf '%s\n' "$pointer" > "$target" 2>/dev/null; then
    printf '⚠️  无法写入 %s，已跳过。\n' "$target"
    return 1
  fi
  if [[ -n "$name" ]]; then
    printf '已写入 %s 入口：%s\n' "$name" "$target"
  else
    printf '已写入入口：%s\n' "$target"
  fi
}

runtime_default_entrypoint() {
  case "$1" in
    "claude") printf '%s/.claude/CLAUDE.md\n' "$HOME" ;;
    "codex") printf '%s/.codex/AGENTS.md\n' "$HOME" ;;
    "agy") printf '%s/.gemini/GEMINI.md\n' "$HOME" ;;
    "opencode") printf '%s/.config/opencode/AGENTS.md\n' "$HOME" ;;
    *) return 1 ;;
  esac
}

normalize_runtime_selection() {
  local item
  item="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$item" in
    "1") item="claude" ;;
    "2") item="codex" ;;
    "3") item="agy" ;;
    "4") item="opencode" ;;
    "5") item="custom" ;;
  esac
  printf '%s\n' "$item"
}

configure_runtime_adapters_noninteractive() {
  local selections="$1"
  local runtime default_path

  if [[ "$selections" == "all" ]]; then
    selections="claude,codex,agy,opencode"
  fi

  IFS=',' read -r -a runtimes <<< "$selections"
  for runtime in "${runtimes[@]}"; do
    runtime="$(normalize_runtime_selection "$runtime")"
    case "$runtime" in
      ""|"none") ;;
      "all")
        configure_runtime_adapters_noninteractive "claude,codex,agy,opencode"
        ;;
      "claude"|"codex"|"agy"|"opencode")
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

# 统一的 curses 选择器：一次调用同时处理 MCP 与 AI。返回 1 表示无法启动 TUI。
run_picker() {
  local sections="$1" py output kind a b c
  py="$(python_command)" || return 1
  output="$("$py" "$ROOT/scripts/terminal_picker.py" "$sections")" || return 1

  local -a mcp_ids=()
  while IFS=$'\t' read -r kind a b c; do
    [[ -z "$kind" ]] && continue
    case "$kind" in
      mcp) [[ -n "$a" ]] && mcp_ids+=("$a") ;;
      runtime) write_entrypoint_file "$c" "$b" ;;
    esac
  done <<< "$output"

  if [[ ",$sections," == *",mcp,"* ]]; then
    if [[ ${#mcp_ids[@]} -gt 0 ]]; then
      local joined
      printf -v joined '%s,' "${mcp_ids[@]}"
      write_mcp_selection "${joined%,}"
    else
      write_mcp_selection "none"
    fi
  fi
  return 0
}

fallback_mcp_menu() {
  local selections
  printf '\n选择要准备的 MCP：\n'
  printf '  1) serena\n'
  printf '  2) chrome-devtools\n'
  printf '  3) ado-work-items\n'
  printf '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过：'
  read -r selections
  write_mcp_selection "${selections:-none}"
}

fallback_runtime_menu() {
  local selections runtime default_path name target
  printf '\n选择要接入的 AI：\n'
  printf '  1) Claude  -> ~/.claude/CLAUDE.md\n'
  printf '  2) Codex   -> ~/.codex/AGENTS.md\n'
  printf '  3) Antigravity CLI (agy) -> ~/.gemini/GEMINI.md\n'
  printf '  4) opencode -> ~/.config/opencode/AGENTS.md\n'
  printf '  5) 自定义路径\n'
  printf '请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过：'
  read -r selections
  [[ -z "$selections" ]] && return
  selections="$(printf '%s' "$selections" | tr -d '[:space:]')"
  [[ "$selections" == "all" ]] && selections="claude,codex,agy,opencode"

  local -a runtimes
  IFS=',' read -r -a runtimes <<< "$selections"
  for runtime in "${runtimes[@]}"; do
    runtime="$(normalize_runtime_selection "$runtime")"
    case "$runtime" in
      "claude"|"codex"|"agy"|"opencode")
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

configure() {
  local pointer_dir="$AGENT_HOME/entrypoints"
  local need_mcp=true need_rt=true
  local target sections
  local -a targets

  mkdir -p "$pointer_dir"
  printf 'Read %s first, then follow it.\n' "$ROUTER_PATH" > "$pointer_dir/router-pointer.md"
  printf '共享入口指针：%s/router-pointer.md\n' "$pointer_dir"

  # 环境变量（非交互）优先，按分区分别接管。
  if [[ -n "${AI_AGENT_MCP_SELECTIONS:-}" ]]; then
    write_mcp_selection "$AI_AGENT_MCP_SELECTIONS"
    need_mcp=false
  fi
  if [[ -n "${AI_AGENT_RUNTIMES:-}" ]]; then
    configure_runtime_adapters_noninteractive "$AI_AGENT_RUNTIMES"
    need_rt=false
  fi
  if [[ -n "${AI_AGENT_ENTRYPOINTS:-}" ]]; then
    IFS=';' read -r -a targets <<< "$AI_AGENT_ENTRYPOINTS"
    for target in "${targets[@]}"; do
      write_entrypoint_file "$target" "custom"
    done
    need_rt=false
  fi

  if ! $need_mcp && ! $need_rt; then
    return
  fi

  if [[ ! -t 0 ]]; then
    $need_mcp && printf '非交互模式：已跳过 MCP 选择。可设置 AI_AGENT_MCP_SELECTIONS 指定。\n'
    $need_rt && printf '非交互模式：已跳过 AI 接入。可设置 AI_AGENT_RUNTIMES 或 AI_AGENT_ENTRYPOINTS 指定。\n'
    return
  fi

  sections=""
  $need_mcp && sections="mcp"
  $need_rt && sections="${sections:+$sections,}runtime"

  if run_picker "$sections"; then
    return
  fi

  # 无 python / curses / 终端时回退到文本菜单。
  $need_mcp && fallback_mcp_menu
  $need_rt && fallback_runtime_menu
}

bash "$ROOT/scripts/apply-to-global.sh"

printf '\n已安装统一提示词和运行时 skills。\n'
printf '提示词目录：%s/.ai-prompt\n' "$HOME"
printf 'Skills 目录：%s\n' "$SKILLS_DIR"
printf 'Router: %s\n' "$ROUTER_PATH"

configure

printf '\n不会自动覆盖任何 AI 的 MCP 配置。\n'
printf '可用 MCP 片段：%s/ai-config/mcp/\n' "$ROOT"
