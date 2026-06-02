#!/usr/bin/env python3
"""统一安装器（唯一逻辑实现）。

替代原来 bash + PowerShell 各写一遍的 install / apply-to-global。
scripts/install.sh、install.ps1、apply-to-global.sh、apply-to-global.ps1
现在都只是找到 python 后调用本文件的薄壳。

用法：
    installer.py apply      # 仅把 ai-prompt（含 skills）同步到全局目录
    installer.py install    # apply + 选择 MCP / 接入 AI（默认）

可移植化、备份、运行时注册表都集中在这一份实现里；新增运行时改 ai-config/registry.json。
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover - Python <3.11 fallback is below.
    tomllib = None

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


def _backup_file(path, suffix="mcp"):
    if os.path.isfile(path):
        shutil.copy2(path, f"{path}.bak.{suffix}-{_stamp()}")


def _read_json(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _loads_simple_toml(text):
    if tomllib is not None:
        return tomllib.loads(text)

    data = {"mcp_servers": {}}
    current = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"\[mcp_servers\.([^\].]+)(?:\.env)?\]", line)
        if m:
            server = data["mcp_servers"].setdefault(m.group(1), {})
            current = server.setdefault("env", {}) if line.endswith(".env]") else server
            continue
        if current is None or "=" not in line:
            continue
        key, value = [p.strip() for p in line.split("=", 1)]
        if value.startswith("["):
            current[key] = json.loads(value)
        else:
            current[key] = json.loads(value)
    return data


def load_mcp_server_spec(mid, root, home, runtime_id=None):
    """Load one ai-config/mcp/<id>.toml snippet as a neutral server spec."""
    snippet = os.path.join(root, "ai-config", "mcp", f"{mid}.toml")
    if not os.path.isfile(snippet):
        return None
    with open(snippet, encoding="utf-8") as f:
        text = f.read().replace("__HOME__", home)
    parsed = _loads_simple_toml(text)
    servers = parsed.get("mcp_servers", {})
    if not servers:
        return None
    name, body = next(iter(servers.items()))
    command = body.get("command", "")
    args = list(body.get("args", []))
    env_vars = dict(body.get("env", {}))
    if runtime_id:
        args = [a.replace("<runtime>", runtime_id) if isinstance(a, str) else a for a in args]
        env_vars = {
            k: v.replace("<runtime>", runtime_id) if isinstance(v, str) else v
            for k, v in env_vars.items()
        }
    return {"id": mid, "name": name, "command": command, "args": args, "env": env_vars}


# ── apply：把项目同步到全局 ──────────────────────────────────────────────────

def apply_to_global(root, home):
    """把 ai-prompt 镜像到 ~/.ai-prompt（所有 skill 现在都在 ai-prompt/skills 这一棵树里）。
    镜像 = 删除源里已不存在的文件，但保护本机 .env / runtime.conf。
    覆盖前先备份到 ~/.ai-agent-workflow-backups/<时间戳>/。
    """
    backup_dir = os.path.join(home, ".ai-agent-workflow-backups", _stamp())
    prompt_target = os.path.join(home, ".ai-prompt")
    src_prompt = os.path.join(root, "ai-prompt")

    os.makedirs(backup_dir, exist_ok=True)
    if os.path.isdir(prompt_target):
        backup_tree(prompt_target, os.path.join(backup_dir, "ai-prompt"))

    mirror_tree(src_prompt, prompt_target)
    replace_home_placeholders(prompt_target, home)

    print("已应用项目工作流到本机全局目录。")
    print(f"备份目录：{backup_dir}")
    print(f"提示词目录：{prompt_target}")
    print(f"Skills 目录：{os.path.join(prompt_target, 'skills')}")
    return backup_dir, prompt_target


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
        print("若本次也选择了已知 AI，安装器会同步这些 MCP 到对应运行时配置。")
        return output

    if os.path.exists(output):
        os.remove(output)
    print("未选择 MCP。")
    return None


def _toml_string(value):
    return json.dumps(value, ensure_ascii=False)


def _render_toml_mcp_block(spec):
    lines = [
        f"[mcp_servers.{spec['name']}]",
        f"command = {_toml_string(spec['command'])}",
        f"args = {_toml_string(spec['args'])}",
    ]
    if spec.get("env"):
        lines.append("")
        lines.append(f"[mcp_servers.{spec['name']}.env]")
        for key, value in spec["env"].items():
            lines.append(f"{key} = {_toml_string(value)}")
    return "\n".join(lines) + "\n"


def _replace_toml_mcp_block(text, name, block):
    header = re.escape(f"[mcp_servers.{name}]")
    escaped_name = re.escape(name)
    pattern = re.compile(rf"(?ms)^{header}\n.*?(?=^\[(?!mcp_servers\.{escaped_name}(?:\.|\Z))|\Z)")
    if pattern.search(text):
        return pattern.sub(block.rstrip() + "\n\n", text).rstrip() + "\n"
    sep = "" if not text or text.endswith("\n") else "\n"
    return f"{text}{sep}\n{block}".rstrip() + "\n"


def sync_mcp_to_codex(ids, root, home):
    path = os.path.join(home, ".codex", "config.toml")
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    changed = False
    for mid in ids:
        spec = load_mcp_server_spec(mid, root, home, runtime_id="codex")
        if not spec:
            continue
        new_text = _replace_toml_mcp_block(text, spec["name"], _render_toml_mcp_block(spec))
        changed = changed or new_text != text
        text = new_text
    if changed:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _backup_file(path, "mcp")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已同步 MCP 到 Codex 配置：{path}")
    return changed


def _json_mcp_server(spec):
    data = {"command": spec["command"], "args": spec["args"]}
    if spec.get("env"):
        data["env"] = spec["env"]
    return data


def sync_mcp_to_gemini_config(ids, root, home, path, runtime_id):
    data = _read_json(path, {"mcpServers": {}})
    data.setdefault("mcpServers", {})
    changed = False
    for mid in ids:
        spec = load_mcp_server_spec(mid, root, home, runtime_id=runtime_id)
        if not spec:
            continue
        server = _json_mcp_server(spec)
        if data["mcpServers"].get(spec["name"]) != server:
            data["mcpServers"][spec["name"]] = server
            changed = True
    if changed:
        _backup_file(path, "mcp")
        _write_json(path, data)
        print(f"已同步 MCP 到 JSON 配置：{path}")
    return changed


def sync_mcp_to_agy(ids, root, home):
    paths = [
        os.path.join(home, ".gemini", "config", "mcp_config.json"),
        os.path.join(home, ".gemini", "antigravity-ide", "mcp_config.json"),
    ]
    changed = False
    for p in paths:
        changed = sync_mcp_to_gemini_config(ids, root, home, p, "agy") or changed
    return changed


def sync_mcp_to_opencode(ids, root, home):
    path = os.path.join(home, ".config", "opencode", "config.json")
    data = _read_json(path, {"$schema": "https://opencode.ai/config.json"})
    data.setdefault("mcp", {})
    changed = False
    for mid in ids:
        spec = load_mcp_server_spec(mid, root, home, runtime_id="opencode")
        if not spec:
            continue
        server = {
            "type": "local",
            "command": [spec["command"], *spec["args"]],
            "enabled": True,
        }
        if spec.get("env"):
            server["environment"] = spec["env"]
        if data["mcp"].get(spec["name"]) != server:
            data["mcp"][spec["name"]] = server
            changed = True
    if changed:
        _backup_file(path, "mcp")
        _write_json(path, data)
        print(f"已同步 MCP 到 opencode 配置：{path}")
    return changed


def sync_mcp_to_claude(ids, root, home):
    claude = shutil.which("claude")
    if not claude:
        print("未找到 claude 命令，已跳过 Claude MCP 同步。")
        return False
    changed = False
    for mid in ids:
        spec = load_mcp_server_spec(mid, root, home, runtime_id="claude")
        if not spec:
            continue
        payload = _json_mcp_server(spec)
        try:
            subprocess.run(
                [claude, "mcp", "add-json", "-s", "user", spec["name"], json.dumps(payload)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            changed = True
            print(f"已同步 MCP 到 Claude：{spec['name']}")
        except subprocess.CalledProcessError as e:
            msg = (e.stderr or e.stdout or "").strip()
            if "already exists" in msg:
                print(f"Claude MCP 已存在，跳过：{spec['name']}")
                continue
            print(f"⚠️  Claude MCP 同步失败：{spec['name']} {msg}")
    return changed


def sync_mcp_to_runtimes(ids, runtime_ids, root, home):
    ids = [i for i in ids if i and i != "none"]
    runtime_ids = [r for r in runtime_ids if r and r != "custom"]
    if not ids or not runtime_ids:
        return []

    synced = []
    for rid in dict.fromkeys(runtime_ids):
        if rid == "codex":
            if sync_mcp_to_codex(ids, root, home):
                synced.append(rid)
        elif rid == "claude":
            if sync_mcp_to_claude(ids, root, home):
                synced.append(rid)
        elif rid == "agy":
            if sync_mcp_to_agy(ids, root, home):
                synced.append(rid)
        elif rid == "opencode":
            if sync_mcp_to_opencode(ids, root, home):
                synced.append(rid)
        else:
            print(f"未知运行时 {rid}，已跳过 MCP 自动同步。")
    if synced:
        print("提示：已运行中的 AI 会话通常需要重启或新开线程才会加载新的 MCP。")
    return synced


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

    selected = []
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
        if write_entrypoint_file(os.path.join(home, r["entrypoint"]), r["name"], home):
            selected.append(rid)
    return selected


# ── 交互 / 非交互配置主流程 ──────────────────────────────────────────────────

def configure(root, home, registry):
    pointer_dir = os.path.join(agent_home(home), "entrypoints")
    os.makedirs(pointer_dir, exist_ok=True)
    with open(os.path.join(pointer_dir, "router-pointer.md"), "w", encoding="utf-8") as f:
        f.write(f"Read {router_path(home)} first, then follow it.\n")
    print(f"共享入口指针：{pointer_dir}/router-pointer.md")

    need_mcp = True
    need_rt = True
    selected_mcp_ids = []
    selected_runtime_ids = []

    mcp_env = env("AI_AGENT_MCP_SELECTIONS")
    if mcp_env:
        selected_mcp_ids = normalize_mcp_ids(mcp_env, registry)
        write_mcp_selection(selected_mcp_ids, root, home)
        need_mcp = False
    rt_env = env("AI_AGENT_RUNTIMES")
    if rt_env:
        selected_runtime_ids = configure_runtimes_noninteractive(rt_env, registry, home)
        need_rt = False
    ep_env = env("AI_AGENT_ENTRYPOINTS")
    if ep_env:
        for target in ep_env.split(";"):
            target = target.strip()
            if target:
                write_entrypoint_file(target, "custom", home)
        need_rt = False

    if not need_mcp and not need_rt:
        sync_mcp_to_runtimes(selected_mcp_ids, selected_runtime_ids, root, home)
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
        selected_mcp_ids = [it["id"] for sec in result if sec["kind"] == "mcp"
                            for it in sec["items"] if it["selected"]]
        write_mcp_selection(selected_mcp_ids or ["none"], root, home)
    for sec in result:
        if sec["kind"] != "runtime":
            continue
        for it in sec["items"]:
            if it["selected"]:
                if write_entrypoint_file(it["path"], it["name"], home):
                    selected_runtime_ids.append(it.get("id"))

    sync_mcp_to_runtimes(selected_mcp_ids, selected_runtime_ids, root, home)


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
    print("已知 AI 的 MCP 配置会在选择 MCP + AI 时自动同步；变更前会备份原配置。")
    print(f"可用 MCP 片段：{os.path.join(root, 'ai-config', 'mcp')}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
