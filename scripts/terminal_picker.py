#!/usr/bin/env python3
import curses
import os
import sys


def home_path(path):
    path = path.replace("__HOME__", os.path.expanduser("~"))
    if path == "~" or path.startswith("~/"):
        return os.path.expanduser(path)
    return path


def runtime_items():
    home = os.path.expanduser("~")
    return [
        {"kind": "runtime", "id": "claude", "name": "Claude", "path": f"{home}/.claude/CLAUDE.md", "selected": False},
        {"kind": "runtime", "id": "codex", "name": "Codex", "path": f"{home}/.codex/AGENTS.md", "selected": False},
        {"kind": "runtime", "id": "agy", "name": "Antigravity CLI (agy)", "path": f"{home}/.gemini/GEMINI.md", "selected": False},
    ]


def mcp_items():
    return [
        {"kind": "mcp", "id": "serena", "name": "Serena", "path": "代码语义/符号导航", "selected": False},
        {"kind": "mcp", "id": "chrome-devtools", "name": "Chrome DevTools", "path": "浏览器调试 MCP", "selected": False},
        {"kind": "mcp", "id": "ado-work-items", "name": "ADO Work Items", "path": "本机 Azure DevOps 工具", "selected": False},
    ]


def prompt_text(stdscr, title, prompt):
    curses.echo()
    stdscr.clear()
    stdscr.addstr(1, 2, title, curses.A_BOLD)
    stdscr.addstr(3, 2, prompt)
    stdscr.addstr(5, 2, "> ")
    stdscr.refresh()
    value = stdscr.getstr(5, 4, 240).decode("utf-8").strip()
    curses.noecho()
    return value


def draw(stdscr, title, help_text, items, cursor):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    stdscr.addstr(0, 2, title, curses.A_BOLD)
    stdscr.addstr(1, 2, help_text[: max(0, width - 4)])

    rows = items + [
        {"kind": "action", "id": "custom", "name": "➕ 自定义添加", "path": "输入名称和入口文件路径", "selected": False},
        {"kind": "action", "id": "submit", "name": "✅ 提交", "path": "完成选择并继续安装", "selected": False},
    ]

    start = max(0, cursor - max(1, height - 6) + 1)
    visible = rows[start : start + max(1, height - 5)]
    for idx, item in enumerate(visible, start=start):
        y = 3 + idx - start
        marker = "[x]" if item.get("selected") else "[ ]"
        if item["kind"] == "action":
            marker = "   "
        line = f"{marker} {item['name']}  {item.get('path', '')}"
        attr = curses.A_REVERSE if idx == cursor else curses.A_NORMAL
        stdscr.addstr(y, 2, line[: max(0, width - 4)], attr)

    footer = "↑↓移动  空格勾选/取消  Enter操作  q取消"
    stdscr.addstr(height - 1, 2, footer[: max(0, width - 4)], curses.A_DIM)
    stdscr.refresh()


def picker(stdscr, mode):
    curses.curs_set(0)
    if mode == "mcp":
        title = "选择要准备的 MCP"
        help_text = "勾选后会生成 ~/.ai-agent/mcp.selected.toml，不会自动覆盖任何 AI 私有配置。"
        items = mcp_items()
        allow_custom = False
    elif mode == "runtime":
        title = "选择要接入的 AI"
        help_text = "勾选后会把该 AI 的入口文件指向 ~/.ai-prompt/router.md。可用“自定义添加”。"
        items = runtime_items()
        allow_custom = True
    else:
        raise SystemExit(f"unknown mode: {mode}")

    cursor = 0
    while True:
        action_custom_index = len(items)
        action_submit_index = len(items) + 1
        if not allow_custom and cursor == action_custom_index:
            cursor = action_submit_index
        draw(stdscr, title, help_text, items, cursor)
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return []
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
            if not allow_custom and cursor == action_custom_index:
                cursor -= 1
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(items) + 1, cursor + 1)
            if not allow_custom and cursor == action_custom_index:
                cursor += 1
        elif key == ord(" "):
            if cursor < len(items):
                items[cursor]["selected"] = not items[cursor]["selected"]
        elif key in (curses.KEY_ENTER, 10, 13):
            if cursor < len(items):
                items[cursor]["selected"] = not items[cursor]["selected"]
            elif cursor == action_custom_index and allow_custom:
                name = prompt_text(stdscr, "自定义 AI", "请输入 AI 名称")
                path = prompt_text(stdscr, "自定义 AI", "请输入该 AI 会读取的入口文件路径")
                if name and path:
                    items.append({"kind": "runtime", "id": "custom", "name": name, "path": home_path(path), "selected": True})
                    cursor = len(items) - 1
            elif cursor == action_submit_index:
                return [item for item in items if item.get("selected")]


def main():
    if len(sys.argv) != 2:
        print("usage: terminal_picker.py <mcp|runtime>", file=sys.stderr)
        return 2

    result_out = sys.stdout
    tty = None
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        result_out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", closefd=True)
        tty = open("/dev/tty", "r+", encoding="utf-8")
        sys.stdin = tty
        sys.stdout = tty

    selected = curses.wrapper(picker, sys.argv[1])
    for item in selected:
        if item["kind"] == "mcp":
            print(f"mcp\t{item['id']}", file=result_out)
        else:
            print(f"runtime\t{item['id']}\t{item['name']}\t{item['path']}", file=result_out)
    result_out.flush()
    if tty is not None:
        tty.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
