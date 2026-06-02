# AI Prompt Hub

本目录是 Claude / Codex / Gemini / agy 的统一提示词入口。

## Read Order
- 所有模型先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- Claude 也按调用方式分支：直接解决问题时是高模；作为 agy/Gemini 额度不足的侦查兜底时是 scout。
- 需要工具能力时，只读索引：`capabilities/skills.md`、`capabilities/mcp.md`。

## Rule
- 不要每次全量读取 `skills/`、`mcp/` 或外部 `SKILL.md`。
- 先读索引，确认相关后再按需读取对应能力文件。
