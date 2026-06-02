#!/usr/bin/env python3
"""统一安装选择器：一屏内同时选择 MCP 与要接入的 AI。

输出（写到原始 stdout，curses 界面只画在 /dev/tty）：
    mcp\t<id>
    runtime\t<id>\t<name>\t<path>

退出码：
    0  正常（可能没有任何选择）
    2  参数错误
    3  无法启动 TUI（缺 curses / stdout 被重定向且非 POSIX），调用方应回退到文本菜单
"""

import locale
import os
import sys
import unicodedata

try:
    import curses
except ImportError:  # Windows 默认没有 curses
    curses = None


SELECTABLE = {"item", "custom", "submit"}


def home(path):
    path = path.replace("__HOME__", os.path.expanduser("~"))
    if path == "~" or path.startswith("~/"):
        return os.path.expanduser(path)
    return path


def display_len(text):
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def build_sections(which):
    h = os.path.expanduser("~")
    sections = []
    if "mcp" in which:
        sections.append({
            "kind": "mcp",
            "title": "MCP 工具",
            "hint": "生成 ~/.ai-agent/mcp.selected.toml，不覆盖任何私有配置",
            "allow_custom": False,
            "items": [
                {"id": "serena", "name": "Serena", "meta": "代码语义 / 符号导航", "selected": False},
                {"id": "chrome-devtools", "name": "Chrome DevTools", "meta": "浏览器调试 MCP", "selected": False},
                {"id": "ado-work-items", "name": "ADO Work Items", "meta": "本机 Azure DevOps 工具", "selected": False},
            ],
        })
    if "runtime" in which:
        sections.append({
            "kind": "runtime",
            "title": "接入的 AI",
            "hint": "把入口文件指向 ~/.ai-prompt/router.md",
            "allow_custom": True,
            "items": [
                {"id": "claude", "name": "Claude", "meta": f"{h}/.claude/CLAUDE.md", "path": f"{h}/.claude/CLAUDE.md", "selected": False},
                {"id": "codex", "name": "Codex", "meta": f"{h}/.codex/AGENTS.md", "path": f"{h}/.codex/AGENTS.md", "selected": False},
                {"id": "agy", "name": "Antigravity CLI (agy)", "meta": f"{h}/.gemini/GEMINI.md", "path": f"{h}/.gemini/GEMINI.md", "selected": False},
                {"id": "opencode", "name": "opencode", "meta": f"{h}/.config/opencode/AGENTS.md", "path": f"{h}/.config/opencode/AGENTS.md", "selected": False},
            ],
        })
    return sections


def build_rows(sections):
    rows = []
    for si, sec in enumerate(sections):
        if si > 0:
            rows.append({"type": "spacer"})
        rows.append({"type": "header", "section": si})
        for ii in range(len(sec["items"])):
            rows.append({"type": "item", "section": si, "item": ii})
        if sec["allow_custom"]:
            rows.append({"type": "custom", "section": si})
    rows.append({"type": "spacer"})
    rows.append({"type": "submit"})
    return rows


def first_selectable(rows):
    for i, row in enumerate(rows):
        if row["type"] in SELECTABLE:
            return i
    return 0


def move(rows, cur, step):
    n = len(rows)
    i = cur
    for _ in range(n):
        i = (i + step) % n
        if rows[i]["type"] in SELECTABLE:
            return i
    return cur


def last_item_of_section(rows, si):
    found = None
    for i, row in enumerate(rows):
        if row["type"] == "item" and row["section"] == si:
            found = i
    return found if found is not None else first_selectable(rows)


def cattr(pair):
    return curses.color_pair(pair) if curses.has_colors() else 0


def safe_addstr(stdscr, y, x, text, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w - 1:
        return
    try:
        stdscr.addnstr(y, x, text, max(0, w - x - 1), attr)
    except curses.error:
        pass


def setup_colors():
    if not curses.has_colors():
        return
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # 标题 / section
        curses.init_pair(2, curses.COLOR_GREEN, -1)   # 勾选标记
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # 操作项
    except curses.error:
        pass


def render_row(stdscr, y, w, sections, row, focused):
    t = row["type"]
    if t == "spacer":
        return
    if t == "header":
        sec = sections[row["section"]]
        safe_addstr(stdscr, y, 1, sec["title"], curses.A_BOLD | cattr(1))
        x = 1 + display_len(sec["title"]) + 2
        hint = sec.get("hint", "")
        if hint and x < w - 2:
            safe_addstr(stdscr, y, x, "· " + hint, curses.A_DIM)
        return

    if t == "item":
        sec = sections[row["section"]]
        item = sec["items"][row["item"]]
        checked = item["selected"]
        box = "[✓]" if checked else "[ ]"
        name = item["name"]
        meta = item.get("meta", "")
        action = False
    elif t == "custom":
        checked, box, name = False, "[+]", "自定义添加…"
        meta, action = "输入名称和入口文件路径", True
    else:  # submit
        checked, box, name = False, "[↵]", "完成安装"
        meta, action = "", True

    if focused:
        safe_addstr(stdscr, y, 0, " " * (w - 1), curses.A_REVERSE)
        bar = curses.A_REVERSE | curses.A_BOLD
        safe_addstr(stdscr, y, 2, box, bar)
        x = 2 + display_len(box) + 1
        safe_addstr(stdscr, y, x, name, bar)
        x += display_len(name) + 2
        if meta and x < w - 2:
            safe_addstr(stdscr, y, x, "— " + meta, curses.A_REVERSE)
        return

    box_attr = (cattr(2) | curses.A_BOLD) if checked else curses.A_DIM
    safe_addstr(stdscr, y, 2, box, box_attr)
    x = 2 + display_len(box) + 1
    name_attr = (cattr(3) | curses.A_BOLD) if action else curses.A_NORMAL
    safe_addstr(stdscr, y, x, name, name_attr)
    x += display_len(name) + 2
    if meta and x < w - 2:
        safe_addstr(stdscr, y, x, "— " + meta, curses.A_DIM)


def draw(stdscr, sections, rows, cursor):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    safe_addstr(stdscr, 0, 1, "AI Agent 安装向导", curses.A_BOLD | cattr(1))
    safe_addstr(stdscr, 1, 1, "↑/↓ 移动 · 空格 勾选 · Enter 确认/添加 · q 取消", curses.A_DIM)

    top = 3
    avail = max(1, h - top - 1)
    start = 0
    if len(rows) > avail and cursor >= avail:
        start = min(cursor - avail + 1, len(rows) - avail)
    start = max(0, start)

    for idx in range(start, min(len(rows), start + avail)):
        render_row(stdscr, top + (idx - start), w, sections, rows[idx], idx == cursor)
    stdscr.refresh()


def prompt(stdscr, title, label):
    curses.curs_set(1)
    curses.echo()
    stdscr.erase()
    safe_addstr(stdscr, 0, 1, title, curses.A_BOLD | cattr(1))
    safe_addstr(stdscr, 2, 1, label)
    safe_addstr(stdscr, 4, 1, "> ")
    stdscr.refresh()
    try:
        value = stdscr.getstr(4, 3, 400).decode("utf-8").strip()
    except (curses.error, UnicodeDecodeError):
        value = ""
    curses.noecho()
    curses.curs_set(0)
    return value


def add_custom(stdscr, sections, si):
    name = prompt(stdscr, "自定义 AI", "名称（例如 MyAgent）")
    if not name:
        return
    path = prompt(stdscr, "自定义 AI", "入口文件路径（该 AI 会读取的文件）")
    if not path:
        return
    resolved = home(path)
    sections[si]["items"].append(
        {"id": "custom", "name": name, "meta": resolved, "path": resolved, "selected": True}
    )


def toggle(sections, rows, cursor):
    row = rows[cursor]
    if row["type"] == "item":
        item = sections[row["section"]]["items"][row["item"]]
        item["selected"] = not item["selected"]


def picker(stdscr, which):
    curses.curs_set(0)
    setup_colors()
    sections = build_sections(which)
    rows = build_rows(sections)
    cursor = first_selectable(rows)

    while True:
        draw(stdscr, sections, rows, cursor)
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_RESIZE:
            continue
        if key in (curses.KEY_UP, ord("k")):
            cursor = move(rows, cursor, -1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = move(rows, cursor, 1)
        elif key == ord(" "):
            toggle(sections, rows, cursor)
        elif key in (curses.KEY_ENTER, 10, 13):
            row = rows[cursor]
            if row["type"] == "item":
                toggle(sections, rows, cursor)
            elif row["type"] == "custom":
                add_custom(stdscr, sections, row["section"])
                rows = build_rows(sections)
                cursor = last_item_of_section(rows, row["section"])
            elif row["type"] == "submit":
                return sections


def emit(sections, out):
    for sec in sections:
        for item in sec["items"]:
            if not item["selected"]:
                continue
            if sec["kind"] == "mcp":
                print(f"mcp\t{item['id']}", file=out)
            else:
                print(f"runtime\t{item['id']}\t{item['name']}\t{item.get('path', '')}", file=out)
    out.flush()


def main():
    if curses is None:
        sys.stderr.write("当前 Python 缺少 curses，回退到文本菜单。"
                         "Windows 可执行: pip install windows-curses\n")
        return 3

    which = "mcp,runtime"
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        which = sys.argv[1].strip()
    which_set = {w.strip() for w in which.split(",") if w.strip()} or {"mcp", "runtime"}

    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    # curses 直接读写真正的终端（C 层的 fd 0/1）。当 stdout 被重定向到管道
    # （例如安装脚本的命令替换 $(...)）时，把 fd 0/1 指向 /dev/tty 让 curses 画在终端上，
    # 并保留原始 stdout（result_fd）用来输出选择结果。
    result_fd = os.dup(1)
    if not sys.stdout.isatty():
        if os.name != "posix":
            os.close(result_fd)
            sys.stderr.write("stdout 被重定向且非 POSIX，无法启动 TUI，回退到文本菜单。\n")
            return 3
        try:
            tty_fd = os.open("/dev/tty", os.O_RDWR)
        except OSError:
            os.close(result_fd)
            return 3
        os.dup2(tty_fd, 0)
        os.dup2(tty_fd, 1)
        os.close(tty_fd)

    try:
        sections = curses.wrapper(picker, which_set)
    except curses.error:
        os.close(result_fd)
        return 3

    with os.fdopen(result_fd, "w", encoding="utf-8", closefd=True) as out:
        if sections is not None:
            emit(sections, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
