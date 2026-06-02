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

The installer can write these native pointer files for you. During interactive install, enter each native entrypoint path when prompted. In non-interactive mode, pass semicolon-separated paths:

```bash
AI_AGENT_ENTRYPOINTS="$HOME/.some-ai/INSTRUCTIONS.md;$HOME/.another-ai/AGENTS.md" bash scripts/install.sh
```
