# Native Entrypoints

AI tools only load instructions from files or settings they already know how to read. This directory documents the boundary pattern:

1. Install the shared prompt hub to `~/.ai-prompt`.
2. For each AI runtime, find the native instruction file or global setting that runtime already reads.
3. Keep that native file thin:

   ```text
   Read ~/.ai-prompt/router.md first, then follow it.
   ```

Do not paste the full workflow into every project or every runtime directory. The native file is only a pointer; `~/.ai-prompt/router.md` remains the source of truth.

When a runtime uses a different home path on Windows or inside a sandbox, replace `~` with the absolute home directory for that environment.

The installer can write these native pointer files for you. During interactive install, choose runtimes from the terminal checklist:

- `claude` suggests `~/.claude/CLAUDE.md`
- `codex` suggests `~/.codex/AGENTS.md`
- `agy` suggests `~/.gemini/GEMINI.md`, Antigravity CLI's official global context file
- `自定义添加` asks for an AI name and explicit entrypoint path only when the runtime is not covered above

Known runtimes are wired automatically. Use `custom` only for non-standard or unknown runtime paths.

Antigravity CLI specifics are intentionally based on the official docs: `agy` reads global context from `~/.gemini/GEMINI.md` and workspace rules from `GEMINI.md` / `AGENTS.md`. Do not use a guessed `~/.agy` directory.

In non-interactive mode, pass runtime names and/or semicolon-separated explicit paths:

```bash
AI_AGENT_RUNTIMES=claude,codex \
AI_AGENT_ENTRYPOINTS="$HOME/.some-ai/INSTRUCTIONS.md;$HOME/.another-ai/AGENTS.md" \
bash scripts/install.sh
```
