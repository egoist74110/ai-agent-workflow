#!/usr/bin/env python3
"""统一安装器（唯一逻辑实现）。

替代原来 bash + PowerShell 各写一遍的 install / apply-to-global。
scripts/install.sh、install.ps1、apply-to-global.sh、apply-to-global.ps1
现在都只是找到 python 后调用本文件的薄壳。

用法：
    installer.py apply      # 仅把 ai-prompt / ai-skills 同步到全局目录
    installer.py install    # apply + 选择 MCP / 接入 AI（默认）

可移植化、备份、运行时注册表都集中在这一份实现里；新增运行时改 ai-config/registry.json。
"""

import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picker  # noqa: E402

# .env / runtime.conf 始终不从源覆盖，也不在镜像时被删除（保护用户本机密钥/配置）。
PROTECT = {".env", "runtime.conf"}


# ── 路径与注册表 ─────────────────────────────────────────────────────────────

def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_registry(root):
    with open(os.path.join(root, "ai-config", "registry.json"), encoding="utf-8") as f:
        return json.load(f)


def env(name, default=None):
    value = os.environ.get(name)
    return value if value else default


def skills_dir(home):
    return env("AI_AGENT_SKILLS_DIR") or os.path.join(home, ".ai-agent", "skills")


def agent_home(home):
    return env("AI_AGENT_HOME") or os.path.join(home, ".ai-agent")


def router_path(home):
    return os.path.join(home, ".ai-prompt", "router.md")


# ── 文件树操作 ───────────────────────────────────────────────────────────────

def _iter_files(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def _copy_into(src, dst):
    for dirpath, _dirnames, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for fn in filenames:
            if fn in PROTECT:
                continue
            shutil.copy2(os.path.join(dirpath, fn), os.path.join(target_dir, fn))


def mirror_tree(src, dst):
    """把 src 镜像到 dst：复制全部源文件，并删除 dst 中源里没有的多余文件。
    PROTECT 里的文件名（.env / runtime.conf）既不覆盖也不删除。"""
    _copy_into(src, dst)

    keep = set()
    for f in _iter_files(src):
        rel = os.path.relpath(f, src)
        if os.path.basename(rel) not in PROTECT:
            keep.add(rel)
    for f in list(_iter_files(dst)):
        rel = os.path.relpath(f, dst)
        if os.path.basename(rel) in PROTECT:
            continue
        if rel not in keep:
            os.remove(f)
    # 自底向上清理空目录
    for dirpath, _dirnames, _filenames in os.walk(dst, topdown=False):
        if os.path.abspath(dirpath) == os.path.abspath(dst):
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        except OSError:
            pass


def merge_tree(src, dst):
    """只合并：复制源文件覆盖同名，但从不删除 dst 里已有的其它内容。"""
    _copy_into(src, dst)


def backup_tree(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)


def replace_home_placeholders(target, home):
    for f in _iter_files(target):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue  # 跳过二进制 / 不可读文件
        if "__HOME__" in text:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(text.replace("__HOME__", home))


def _stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


# ── apply：把项目同步到全局 ──────────────────────────────────────────────────

def apply_to_global(root, home):
    """同步语义（与历史行为一致，刻意不对称）：
      - ai-prompt  -> ~/.ai-prompt        镜像（删除多余文件，保护 .env/runtime.conf）
      - ai-skills  -> <skills_dir>         只合并（不删除，便于与运行时 .system skills 共存）
    覆盖前先备份到 ~/.ai-agent-workflow-backups/<时间戳>/。
    """
    sdir = skills_dir(home)
    backup_dir = os.path.join(home, ".ai-agent-workflow-backups", _stamp())
    prompt_target = os.path.join(home, ".ai-prompt")
    src_prompt = os.path.join(root, "ai-prompt")
    src_skills = os.path.join(root, "ai-skills")

    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(sdir, exist_ok=True)

    if os.path.isdir(prompt_target):
        backup_tree(prompt_target, os.path.join(backup_dir, "ai-prompt"))
    if os.path.isdir(src_skills):
        for name in sorted(os.listdir(src_skills)):
            existing = os.path.join(sdir, name)
            if os.path.isdir(existing):
                backup_tree(existing, os.path.join(backup_dir, "ai-skills", name))

    mirror_tree(src_prompt, prompt_target)
    replace_home_placeholders(prompt_target, home)
    merge_tree(src_skills, sdir)
    replace_home_placeholders(sdir, home)

    print("已应用项目工作流到本机全局目录。")
    print(f"备份目录：{backup_dir}")
    print(f"提示词目录：{prompt_target}")
    print(f"Skills 目录：{sdir}")
    return backup_dir, prompt_target, sdir


# ── MCP 片段 ─────────────────────────────────────────────────────────────────

def normalize_mcp_ids(raw, registry):
    """把 'all' / 编号 / id 列表归一化成 id 列表（编号按 registry 顺序）。"""
    mcp = registry.get("mcp", [])
    by_num = {str(i + 1): m["id"] for i, m in enumerate(mcp)}
    ids = []
    for tok in raw.split(","):
        t = tok.strip().lower()
        if t in ("", "none"):
            continue
        if t == "all":
            return [m["id"] for m in mcp]
        ids.append(by_num.get(t, t))
    return ids


def write_mcp_selection(ids, root, home):
    output = os.path.join(agent_home(home), "mcp.selected.toml")
    os.makedirs(agent_home(home), exist_ok=True)

    parts = []
    for mid in ids:
        mid = (mid or "").strip()
        if mid in ("", "none"):
            continue
        snippet = os.path.join(root, "ai-config", "mcp", f"{mid}.toml")
        if not os.path.isfile(snippet):
            print(f"未知 MCP 选项已跳过：{mid}")
            continue
        with open(snippet, encoding="utf-8") as f:
            text = f.read().replace("__HOME__", home)
        parts.append(f"\n# {mid}\n{text}\n")

    if parts:
        with open(output, "w", encoding="utf-8") as f:
            f.write("".join(parts))
        print(f"已生成 MCP 片段：{output}")
        print("请检查路径后，再合并到对应 AI 的 MCP 配置。")
        return output

    if os.path.exists(output):
        os.remove(output)
    print("未选择 MCP。")
    return None


# ── 运行时入口文件 ───────────────────────────────────────────────────────────

def write_entrypoint_file(target, name, home):
    if not target:
        return False
    if target.startswith("~"):
        target = os.path.join(home, target[1:].lstrip("/\\"))

    if os.path.isdir(target):
        print(f"⚠️  入口必须是文件，但 {target} 是目录，已跳过。"
              f"请填具体的指令文件，例如 {target.rstrip('/')}/AGENTS.md")
        return False

    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.isfile(target):
        shutil.copy2(target, f"{target}.bak.{_stamp()}")

    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write(f"Read {router_path(home)} first, then follow it.\n")
    except OSError:
        print(f"⚠️  无法写入 {target}，已跳过。")
        return False

    print(f"已写入 {name} 入口：{target}" if name else f"已写入入口：{target}")
    return True


def configure_runtimes_noninteractive(raw, registry, home):
    if raw.strip().lower() == "all":
        raw = ",".join(r["id"] for r in registry["runtimes"])
    by_id = {r["id"]: r for r in registry["runtimes"]}
    by_num = {str(i + 1): r["id"] for i, r in enumerate(registry["runtimes"])}
    custom_num = str(len(registry["runtimes"]) + 1)

    for tok in raw.split(","):
        t = tok.strip().lower()
        if t in ("", "none"):
            continue
        rid = by_num.get(t, t)
        if t == custom_num or rid == "custom":
            print("已选择自定义运行时；请用 AI_AGENT_ENTRYPOINTS 指定路径，或在交互模式里选择自定义添加。")
            continue
        r = by_id.get(rid)
        if not r:
            print(f"未知 AI 选项已跳过：{rid}")
            continue
        write_entrypoint_file(os.path.join(home, r["entrypoint"]), r["name"], home)


# ── 交互 / 非交互配置主流程 ──────────────────────────────────────────────────

def configure(root, home, registry):
    pointer_dir = os.path.join(agent_home(home), "entrypoints")
    os.makedirs(pointer_dir, exist_ok=True)
    with open(os.path.join(pointer_dir, "router-pointer.md"), "w", encoding="utf-8") as f:
        f.write(f"Read {router_path(home)} first, then follow it.\n")
    print(f"共享入口指针：{pointer_dir}/router-pointer.md")

    need_mcp = True
    need_rt = True

    mcp_env = env("AI_AGENT_MCP_SELECTIONS")
    if mcp_env:
        write_mcp_selection(normalize_mcp_ids(mcp_env, registry), root, home)
        need_mcp = False
    rt_env = env("AI_AGENT_RUNTIMES")
    if rt_env:
        configure_runtimes_noninteractive(rt_env, registry, home)
        need_rt = False
    ep_env = env("AI_AGENT_ENTRYPOINTS")
    if ep_env:
        for target in ep_env.split(";"):
            target = target.strip()
            if target:
                write_entrypoint_file(target, "custom", home)
        need_rt = False

    if not need_mcp and not need_rt:
        return

    noninteractive = env("AI_AGENT_NONINTERACTIVE") == "1" or not sys.stdin.isatty()
    if noninteractive:
        if need_mcp:
            print("非交互模式：已跳过 MCP 选择。可设置 AI_AGENT_MCP_SELECTIONS 指定。")
        if need_rt:
            print("非交互模式：已跳过 AI 接入。可设置 AI_AGENT_RUNTIMES 或 AI_AGENT_ENTRYPOINTS 指定。")
        return

    which = set()
    if need_mcp:
        which.add("mcp")
    if need_rt:
        which.add("runtime")

    sections = picker.build_sections(registry, which, home)
    result = picker.pick(sections) if picker.can_tui() else picker.text_pick(sections)
    if result is None:  # 用户取消
        result = sections

    if need_mcp:
        ids = [it["id"] for sec in result if sec["kind"] == "mcp"
               for it in sec["items"] if it["selected"]]
        write_mcp_selection(ids or ["none"], root, home)
    for sec in result:
        if sec["kind"] != "runtime":
            continue
        for it in sec["items"]:
            if it["selected"]:
                write_entrypoint_file(it["path"], it["name"], home)


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main(argv):
    cmd = argv[1] if len(argv) > 1 else "install"
    root = repo_root()
    home = os.path.expanduser("~")
    registry = load_registry(root)

    if cmd == "apply":
        apply_to_global(root, home)
        return 0

    if cmd not in ("install", ""):
        print(f"未知子命令：{cmd}（可用：apply / install）", file=sys.stderr)
        return 2

    apply_to_global(root, home)
    print()
    print("已安装统一提示词和运行时 skills。")
    print(f"Router: {router_path(home)}")

    configure(root, home, registry)

    print()
    print("不会自动覆盖任何 AI 的 MCP 配置。")
    print(f"可用 MCP 片段：{os.path.join(root, 'ai-config', 'mcp')}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
