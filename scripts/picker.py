#!/usr/bin/env python3
"""统一安装选择器（库模块）。

由 installer.py 在前台进程内直接调用，不再通过子进程 + 命令替换，
所以不需要任何 /dev/tty 重定向：当前进程的 stdout 就是真终端，curses 直接画。

对外接口：
    build_sections(registry, which, home_dir) -> list[section]
    can_tui() -> bool                # 能否启动 curses 界面
    pick(sections) -> list[section] | None   # curses 多选；None 表示取消
    text_pick(sections) -> list[section]     # 无 curses 时的编号菜单兜底
"""

import os
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


def build_sections(registry, which, home_dir):
    sections = []
    if "mcp" in which:
        sections.append({
            "kind": "mcp",
            "title": "MCP 工具",
            "hint": "生成 ~/.ai-agent/mcp.selected.toml；若同时选择 AI，会同步到对应配置",
            "allow_custom": False,
            "items": [
                {"id": m["id"], "name": m["name"], "meta": m.get("desc", ""), "selected": False}
                for m in registry.get("mcp", [])
            ],
        })
    if "runtime" in which:
        items = []
        for r in registry.get("runtimes", []):
            path = os.path.join(home_dir, r["entrypoint"])
            items.append({"id": r["id"], "name": r["name"], "meta": path, "path": path, "selected": False})
        sections.append({
            "kind": "runtime",
            "title": "接入的 AI",
            "hint": "把入口文件指向 ~/.ai-prompt/router.md",
            "allow_custom": True,
            "items": items,
        })
    return sections


# ── curses 多选界面 ───────────────────────────────────────────────────────────

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


def _picker(stdscr, sections):
    curses.curs_set(0)
    setup_colors()
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


def can_tui():
    import sys
    return curses is not None and sys.stdin.isatty() and sys.stdout.isatty()


def pick(sections):
    return curses.wrapper(_picker, sections)


# ── 编号菜单兜底（无 curses / 非终端）─────────────────────────────────────────

def text_pick(sections):
    for sec in sections:
        print()
        print(sec["title"] + "：")
        for i, item in enumerate(sec["items"], 1):
            meta = item.get("meta", "")
            print(f"  {i}) {item['name']}  {meta}".rstrip())
        custom_n = None
        if sec["allow_custom"]:
            custom_n = len(sec["items"]) + 1
            print(f"  {custom_n}) 自定义添加")
        raw = input("请输入编号，用英文逗号分隔；输入 all 全选；直接回车跳过：").strip()
        if not raw:
            continue
        if raw.lower() == "all":
            for item in sec["items"]:
                item["selected"] = True
            continue
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok.isdigit():
                continue
            n = int(tok)
            if 1 <= n <= len(sec["items"]):
                sec["items"][n - 1]["selected"] = True
            elif custom_n is not None and n == custom_n:
                name = input("自定义 AI 名称：").strip()
                path = input("自定义入口文件路径：").strip()
                if name and path:
                    resolved = home(path)
                    sec["items"].append(
                        {"id": "custom", "name": name, "meta": resolved, "path": resolved, "selected": True}
                    )
    return sections
