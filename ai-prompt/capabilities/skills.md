# Skills Index

规则：不要全量读取所有 skill。只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`。

## Custom
- `ui-ux-pro-max`
  - Path: `__HOME__/CG_Vue_uigen/.claude/skills/ui-ux-pro-max/SKILL.md`
  - Use for: 唯一 UI/UX skill；用于页面/组件/交互/视觉的设计、实现、评审、优化、配色、排版、无障碍、移动端适配。
  - Guardrails: 不再并行使用其它前端设计 skill；需要前端视觉时优先它，避免 UI skill 之间互相覆盖。
- `anysearch`
  - Path: `__HOME__/.ai-prompt/skills/anysearch/SKILL.md`
  - Runtime: `node __HOME__/.ai-prompt/skills/anysearch/scripts/anysearch_cli.js`
  - Use for: 实时外部搜索、批量搜索、垂直领域检索、URL 正文抽取。
  - Guardrails: 按需使用，不作为默认搜索；不用于密码、私密工单、内部代码、商业机密等敏感查询；不要让它覆盖官方文档优先规则。
- `bilibili-auto-transcript`
  - Path: `__HOME__/.ai-prompt/skills/bilibili-auto-transcript/SKILL.md`
  - Runtime: `bash __HOME__/.ai-prompt/skills/bilibili-auto-transcript/scripts/bilibili_transcript.sh "<B站视频链接>"`
  - Use for: B站/Bilibili 视频链接转录、收藏夹扫描、新视频自动处理；三级降级为 CC 字幕 → AI 字幕 → Whisper。
  - Guardrails: 脚本输出 TXT 后必须读取全文并替换“AI待处理”摘要占位符，再向用户报告完成；默认只输出转录文件，索引交给 knowledge-rag 或用户明确要求的 RAG 脚本。
  - Source: https://clawhub.ai/54lynnn/bilibili-auto-transcript / https://github.com/54Lynnn/bilibili-auto-transcript

## Codex System Skills
- `skill-creator`
  - Path: `__HOME__/.codex/skills/.system/skill-creator/SKILL.md`
  - Use for: 当用户觉得某个重复流程有必要封装成可复用 skill 时，创建或更新本地 skill；也可把稳定工作流、操作手册、提示词套路沉淀成 skill。
  - Guardrails: 只有明确要创建/更新 skill，或用户指出某流程值得复用时才读；不要为了普通任务临时造 skill。
- `skill-installer`
  - Path: `__HOME__/.codex/skills/.system/skill-installer/SKILL.md`
  - Use for: 列出可安装 skill、安装精选 skill 或从 GitHub repo 安装 skill。
  - Guardrails: 先判断是否真的需要安装；优先用已有能力和索引，避免“看到推荐就全装”。
- `plugin-creator`
  - Path: `__HOME__/.codex/skills/.system/plugin-creator/SKILL.md`
  - Use for: 创建或更新 Codex plugin，而不是普通 skill。
- `openai-docs`
  - Path: `__HOME__/.codex/skills/.system/openai-docs/SKILL.md`
  - Use for: OpenAI 产品/API 的最新官方文档、模型选择、迁移和提示升级。
- `imagegen`
  - Path: `__HOME__/.codex/skills/.system/imagegen/SKILL.md`
  - Use for: 需要 AI 生成或编辑位图视觉资产的任务。

## Engineering Skills
- `backend-business-safety`
  - Path: `__HOME__/.codex/skills/backend-business-safety/SKILL.md`
  - Use for: 后端业务生命周期安全；涉及 worker/job/发布/同步/导入导出、取消/重试/超时、registry/lock/cache、外部 API、长任务状态时先检查状态机、不变量、清理、幂等和并发。
  - Guardrails: 不用于简单纯函数、小 UI、静态配置或一次性脚本；只在状态可能跨请求/线程/任务存活时触发。
- `grill-me`
  - Path: `__HOME__/.codex/skills/grill-me/SKILL.md`
  - Use for: 需求、计划或设计仍模糊时的拷问模式；先一问一答澄清决策树，再动手实现。
  - Guardrails: 只在需求不清、大模块设计、用户明确要求“拷问/追问/grill me”时触发；小修小补不要触发。
- `tdd`
  - Path: `__HOME__/.codex/skills/tdd/SKILL.md`
  - Use for: 新功能、bugfix、重构或行为变更的测试优先开发；强调公共接口、行为测试、垂直切片。
  - Guardrails: 原型、纯配置、一次性脚本可不触发；没有测试框架时先说明并建议最小验证方案。
- `diagnose`
  - Path: `__HOME__/.codex/skills/diagnose/SKILL.md`
  - Use for: 代码跑不通、逻辑不可用、测试失败、构建失败、性能回退、线上/本地 bug。
  - Guardrails: 先建立可运行反馈回路，再复现、假设、插桩、修复、回归测试；不要凭直觉打补丁。
- `improve-codebase-architecture`
  - Path: `__HOME__/.codex/skills/improve-codebase-architecture/SKILL.md`
  - Use for: 大模块设计、架构隐患排查、重构机会分析、提升可测试性和可维护性。
  - Guardrails: 不默认触发；只在用户要求架构/重构/大模块设计，或诊断后发现缺少测试 seam、耦合严重时触发。
- `verification-before-completion`
  - Path: `__HOME__/.codex/skills/verification-before-completion/SKILL.md`
  - Use for: 声称完成、修好、通过、可提交或可交付之前。
  - Guardrails: 必须有新鲜验证证据；跑不了验证就明确说明原因和剩余风险。
- `receiving-code-review`
  - Path: `__HOME__/.codex/skills/receiving-code-review/SKILL.md`
  - Use for: 收到 review 反馈、PR 评论、或用户点名“帮我提交/合并”且需要先处理外部反馈时。
  - Guardrails: 不盲从 review；先理解、核对代码现实、评估是否技术正确，再逐项处理和验证。
- `security-best-practices`
  - Path: `__HOME__/.codex/skills/security-best-practices/SKILL.md`
  - Use for: 安全最佳实践、安全审查、安全报告、或需要 secure-by-default 的 Python / JavaScript / TypeScript / Go 代码。
  - Guardrails: 只处理安全维度；普通代码 review、调试、UI 问题不要触发。

## Codex Plugin Skills
- GitHub:
  - `__HOME__/.codex/plugins/cache/openai-curated/github/fef63ecf/skills/github/SKILL.md`
  - `__HOME__/.codex/plugins/cache/openai-curated/github/fef63ecf/skills/gh-fix-ci/SKILL.md`
  - `__HOME__/.codex/plugins/cache/openai-curated/github/fef63ecf/skills/gh-address-comments/SKILL.md`
  - `__HOME__/.codex/plugins/cache/openai-curated/github/fef63ecf/skills/yeet/SKILL.md`
- Documents:
  - `__HOME__/.codex/plugins/cache/openai-primary-runtime/documents/26.521.10419/skills/documents/SKILL.md`
- Spreadsheets:
  - `__HOME__/.codex/plugins/cache/openai-primary-runtime/spreadsheets/26.521.10419/skills/spreadsheets/SKILL.md`
- Presentations:
  - `__HOME__/.codex/plugins/cache/openai-primary-runtime/presentations/26.521.10419/skills/presentations/SKILL.md`
- Browser / Chrome / Computer Use:
  - `__HOME__/.codex/plugins/cache/openai-bundled/browser/26.527.31326/skills/control-in-app-browser/SKILL.md`
  - `__HOME__/.codex/plugins/cache/openai-bundled/chrome/26.527.31326/skills/control-chrome/SKILL.md`
  - `__HOME__/.codex/plugins/cache/openai-bundled/computer-use/1.0.799/skills/computer-use/SKILL.md`
