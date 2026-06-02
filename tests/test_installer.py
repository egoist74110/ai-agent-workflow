#!/usr/bin/env python3
"""installer / picker 的冒烟测试（仅用标准库）。

直接跑：   python3 tests/test_installer.py
或 pytest： pytest tests/
覆盖最容易回归、且之前真出过 bug 的点：目录守卫、__HOME__ 替换、
镜像时保护 runtime.conf、MCP 片段拼接、注册表与 toml 一致、picker 从注册表建模型。
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import installer  # noqa: E402
import picker      # noqa: E402


def test_registry_matches_mcp_toml_files():
    """registry.json 里每个 mcp id 都要有对应的 toml，且已知运行时都在。"""
    reg = installer.load_registry(ROOT)
    rt_ids = {r["id"] for r in reg["runtimes"]}
    assert {"claude", "codex", "agy", "opencode"} <= rt_ids
    for m in reg["mcp"]:
        toml = os.path.join(ROOT, "ai-config", "mcp", f"{m['id']}.toml")
        assert os.path.isfile(toml), f"缺少 {toml}"


def test_write_entrypoint_rejects_directory():
    with tempfile.TemporaryDirectory() as home:
        target = os.path.join(home, ".opencode")  # 故意建成目录
        os.makedirs(target)
        ok = installer.write_entrypoint_file(target, "opencode", home)
        assert ok is False
        assert os.path.isdir(target)  # 仍是目录，没被当文件覆盖


def test_write_entrypoint_writes_file_and_backs_up():
    with tempfile.TemporaryDirectory() as home:
        target = os.path.join(home, ".config", "opencode", "AGENTS.md")
        assert installer.write_entrypoint_file(target, "opencode", home) is True
        with open(target, encoding="utf-8") as f:
            body = f.read()
        assert body.strip().endswith("router.md first, then follow it.")
        assert home in body  # router 路径已是绝对路径
        # 再写一次应产生 .bak
        assert installer.write_entrypoint_file(target, "opencode", home) is True
        baks = [p for p in os.listdir(os.path.dirname(target)) if ".bak." in p]
        assert len(baks) == 1


def test_mcp_selection_concats_and_replaces_home():
    with tempfile.TemporaryDirectory() as home:
        out = installer.write_mcp_selection(["serena"], ROOT, home)
        assert out and os.path.isfile(out)
        with open(out, encoding="utf-8") as f:
            text = f.read()
        assert "# serena" in text
        assert "__HOME__" not in text          # 占位符已替换
        # 写进 TOML 的 home 反斜杠已转义（POSIX 下 replace 为空操作）
        assert home.replace("\\", "\\\\") in text


def test_mcp_selection_none_removes_output():
    with tempfile.TemporaryDirectory() as home:
        installer.write_mcp_selection(["serena"], ROOT, home)
        out = os.path.join(installer.agent_home(home), "mcp.selected.toml")
        assert os.path.isfile(out)
        installer.write_mcp_selection(["none"], ROOT, home)
        assert not os.path.exists(out)          # 空选择清掉文件


def test_load_lark_mcp_spec_replaces_home():
    with tempfile.TemporaryDirectory() as home:
        spec = installer.load_mcp_server_spec("lark", ROOT, home, runtime_id="codex")
        assert spec["name"] == "lark"
        # toml 模板用正斜杠，home 在 Windows 下是反斜杠，按归一化路径比较
        assert os.path.normpath(spec["command"]) == \
            os.path.normpath(os.path.join(home, "my-own-script", ".venv", "bin", "python"))
        assert [os.path.normpath(a) for a in spec["args"]] == \
            [os.path.normpath(os.path.join(home, "my-own-script", "app_lark", "mcp_lark_server.py"))]


def test_simple_toml_fallback_parses_env_table():
    old = installer.tomllib
    installer.tomllib = None
    try:
        parsed = installer._loads_simple_toml(
            '[mcp_servers.demo]\n'
            'command = "cmd"\n'
            'args = ["a"]\n\n'
            '[mcp_servers.demo.env]\n'
            'PATH = "/bin"\n'
        )
    finally:
        installer.tomllib = old
    assert parsed["mcp_servers"]["demo"]["command"] == "cmd"
    assert parsed["mcp_servers"]["demo"]["env"]["PATH"] == "/bin"


def test_sync_mcp_to_codex_merges_and_is_idempotent():
    with tempfile.TemporaryDirectory() as home:
        cfg = os.path.join(home, ".codex", "config.toml")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w", encoding="utf-8") as f:
            f.write('model = "gpt-5"\n\n[mcp_servers.existing]\ncommand = "keep"\nargs = []\n')

        assert installer.sync_mcp_to_codex(["lark", "serena"], ROOT, home) is True
        with open(cfg, encoding="utf-8") as f:
            text = f.read()
        assert '[mcp_servers.existing]' in text
        assert '[mcp_servers.lark]' in text
        assert '[mcp_servers.serena]' in text
        assert '[mcp_servers.serena.env]' in text
        # 合并后的 TOML 必须可解析，且 lark 路径已正确写入（按归一化路径比较）
        parsed = installer._loads_simple_toml(text)
        assert os.path.normpath(parsed["mcp_servers"]["lark"]["args"][0]) == \
            os.path.normpath(os.path.join(home, "my-own-script", "app_lark", "mcp_lark_server.py"))

        assert installer.sync_mcp_to_codex(["lark", "serena"], ROOT, home) is False


def test_sync_mcp_to_codex_replaces_existing_env_subtable():
    with tempfile.TemporaryDirectory() as home:
        cfg = os.path.join(home, ".codex", "config.toml")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(
                'model = "gpt-5"\n\n'
                '[mcp_servers.serena]\n'
                'command = "old-serena"\n'
                'args = ["old"]\n\n'
                '[mcp_servers.serena.env]\n'
                'PATH = "/old"\n\n'
                '[mcp_servers.after]\n'
                'command = "keep"\n'
                'args = []\n'
            )

        assert installer.sync_mcp_to_codex(["serena"], ROOT, home) is True
        with open(cfg, encoding="utf-8") as f:
            text = f.read()

        assert text.count("[mcp_servers.serena]") == 1
        assert text.count("[mcp_servers.serena.env]") == 1
        assert '[mcp_servers.after]' in text
        assert 'old-serena' not in text
        assert 'PATH = "/old"' not in text
        installer._loads_simple_toml(text)


def test_sync_mcp_to_gemini_json_preserves_existing():
    with tempfile.TemporaryDirectory() as home:
        cfg = os.path.join(home, ".gemini", "config", "mcp_config.json")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"existing": {"command": "keep", "args": []}}}, f)

        assert installer.sync_mcp_to_gemini_config(["lark"], ROOT, home, cfg, "agy") is True
        with open(cfg, encoding="utf-8") as f:
            data = json.load(f)
        assert "existing" in data["mcpServers"]
        assert data["mcpServers"]["lark"]["command"].endswith("/.venv/bin/python")
        assert data["mcpServers"]["lark"]["args"][0].endswith("mcp_lark_server.py")


def test_sync_mcp_to_opencode_json_preserves_existing():
    with tempfile.TemporaryDirectory() as home:
        cfg = os.path.join(home, ".config", "opencode", "config.json")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"model": "x", "mcp": {"existing": {"type": "local"}}}, f)

        assert installer.sync_mcp_to_opencode(["lark"], ROOT, home) is True
        with open(cfg, encoding="utf-8") as f:
            data = json.load(f)
        assert data["model"] == "x"
        assert "existing" in data["mcp"]
        assert data["mcp"]["lark"]["type"] == "local"
        assert data["mcp"]["lark"]["enabled"] is True
        assert data["mcp"]["lark"]["command"][1].endswith("mcp_lark_server.py")


def test_sync_mcp_to_claude_treats_existing_as_ok():
    calls = []
    old_which = installer.shutil.which
    old_run = installer.subprocess.run

    def fake_which(name):
        return "/fake/claude" if name == "claude" else None

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        raise subprocess.CalledProcessError(
            1,
            cmd,
            stderr="MCP server lark already exists in user config",
        )

    installer.shutil.which = fake_which
    installer.subprocess.run = fake_run
    try:
        with tempfile.TemporaryDirectory() as home:
            assert installer.sync_mcp_to_claude(["lark"], ROOT, home) is False
    finally:
        installer.shutil.which = old_which
        installer.subprocess.run = old_run

    assert calls


def test_normalize_mcp_ids():
    reg = installer.load_registry(ROOT)
    assert installer.normalize_mcp_ids("all", reg) == [m["id"] for m in reg["mcp"]]
    assert installer.normalize_mcp_ids("1", reg) == [reg["mcp"][0]["id"]]
    assert installer.normalize_mcp_ids("serena, ,none", reg) == ["serena"]


def test_apply_replaces_home_and_protects_runtime_conf():
    with tempfile.TemporaryDirectory() as home:
        # 预置一个用户本机 runtime.conf，镜像后必须存活
        secret_dir = os.path.join(home, ".ai-prompt", "skills", "anysearch")
        os.makedirs(secret_dir)
        secret = os.path.join(secret_dir, "runtime.conf")
        with open(secret, "w", encoding="utf-8") as f:
            f.write("API_KEY=keep-me\n")

        installer.apply_to_global(ROOT, home)

        # router.md 里的 __HOME__ 必须被替换干净
        router = os.path.join(home, ".ai-prompt", "router.md")
        assert os.path.isfile(router)
        with open(router, encoding="utf-8") as f:
            assert "__HOME__" not in f.read()

        # runtime.conf 被保护，未被 --delete 掉
        assert os.path.isfile(secret)
        with open(secret, encoding="utf-8") as f:
            assert "keep-me" in f.read()

        # 工程 skill 和工具 skill 现在同在一棵树 ~/.ai-prompt/skills/
        skills = os.path.join(home, ".ai-prompt", "skills")
        assert os.path.isfile(os.path.join(skills, "tdd", "SKILL.md"))
        assert os.path.isfile(os.path.join(skills, "anysearch", "SKILL.md"))

        # 备份目录已生成
        assert os.path.isdir(os.path.join(home, ".ai-agent-workflow-backups"))


def test_picker_build_sections_from_registry():
    reg = installer.load_registry(ROOT)
    secs = picker.build_sections(reg, {"mcp", "runtime"}, "/fake/home")
    kinds = {s["kind"] for s in secs}
    assert kinds == {"mcp", "runtime"}
    rt = next(s for s in secs if s["kind"] == "runtime")
    assert rt["allow_custom"] is True
    claude = next(i for i in rt["items"] if i["id"] == "claude")
    assert os.path.normpath(claude["path"]) == os.path.normpath("/fake/home/.claude/CLAUDE.md")


def run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
