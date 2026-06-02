# AI Agent Workflow

个人 AI Agent 工作流配置包，用来在不同电脑之间迁移：

- 统一提示词入口：`ai-prompt/`
- Skill/MCP 索引：`ai-prompt/capabilities/`
- 本地 Codex skills：`codex-skills/`
- Codex MCP 配置模板：`codex-config/`
- 安装脚本：`scripts/install.sh`

## What Is Included

- 轻量公共提示词：中文输出、最小改动、真实验证、必要澄清。
- 高级模型路由：精确描述直接读文件；模糊/跨文件问题先判断是否需要语义/符号召回或侦查。
- MCP 索引：ADO、Chrome DevTools、Node REPL、Serena、Codex 插件能力说明。
- Engineering skills：
  - `backend-business-safety`
  - `diagnose`
  - `grill-me`
  - `improve-codebase-architecture`
  - `receiving-code-review`
  - `security-best-practices`
  - `tdd`
  - `verification-before-completion`
- Prompt skills：
  - `anysearch`
  - `bilibili-auto-transcript`

## What Is Not Included

- API keys and `.env` files.
- Machine-specific full `~/.codex/config.toml`.
- Codex plugin cache directories.
- Trust lists for local projects.
- Runtime-generated files such as `.DS_Store`, `runtime.conf`, and `__pycache__`.

## Install On A New Mac

```bash
git clone git@github.com:egoist74110/ai-agent-workflow.git
cd ai-agent-workflow
bash scripts/install.sh
```

The installer copies:

- `ai-prompt/` to `~/.ai-prompt`
- `codex-skills/` to `~/.codex/skills`

It also replaces `__HOME__` placeholders with the current machine's `$HOME`.

## MCP Setup Notes

The installer does not overwrite `~/.codex/config.toml`.

Use `codex-config/mcp.example.toml` as a merge reference. Important entries:

- `serena`: semantic/symbol code navigation.
- `chrome-devtools`: browser debugging through Chrome DevTools MCP.
- `adoWorkItems`: local personal ADO tool; path must be adjusted if the script is not present on the new machine.

For Serena:

```bash
uv tool install -p 3.13 serena-agent
codex mcp add serena -- serena start-mcp-server --context=codex --project-from-cwd
```

Then adjust the generated command to use absolute paths if Codex App cannot find `serena`, `uv`, or `uvx`.

## AGENTS.md Router

Use `AGENTS.example.md` as a project-level router template. Put it in any workspace where you want agents to follow this prompt hub.

## Sync Back From This Machine

When updating this repository from the current machine, copy only safe files:

- include prompt files and skill documents/scripts
- exclude `.env`, `runtime.conf`, plugin caches, and full machine configs
- replace absolute home paths with `__HOME__` before committing

