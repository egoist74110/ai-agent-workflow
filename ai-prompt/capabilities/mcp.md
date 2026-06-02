# MCP Index

规则：先确认任务需要 MCP，再使用对应能力。`Configured MCP` 表示本机已知、可由运行时配置或本索引命令启动的能力；任务明确需要时应优先直接访问它，不要先读私有实现脚本绕路。若当前会话已暴露对应 MCP 工具，直接调用工具；若未暴露但索引给出本机命令，可启动该命令做轻量 `tools/list`/任务调用。只有新增、安装、授权、或写入/修改运行时 MCP 配置前，才必须先说明原因、命令/配置和影响范围并取得用户确认。

## Configured MCP
- `ado-work-items` / `adoWorkItems`: Azure DevOps work items。
  - Example config:
    ```toml
    [mcp_servers.adoWorkItems]
    command = "__HOME__/my-own-script/.venv/bin/python"
    args = ["__HOME__/my-own-script/app_ado/mcp_ado_work_items_server.py"]
    ```
- `lark` / `飞书`: 飞书/Lark 云文档与知识库读取。
  - Example config:
    ```toml
    [mcp_servers.lark]
    command = "__HOME__/my-own-script/.venv/bin/python"
    args = ["__HOME__/my-own-script/app_lark/mcp_lark_server.py"]
    ```
  - Typical tools: `wiki_v2_space_getNode`（wiki 链接 token → 实际 docx token）、`docx_v1_document_rawContent`（取文档纯文本）、`wiki_v1_node_search`、`docx_builtin_search`、`docx_builtin_import`、`drive_v1_permissionMember_create`。
  - Workflow: 读 wiki 链接（URL 里 `/wiki/<token>`）先用 `wiki_v2_space_getNode` 拿到 `obj_token`，再用 `docx_v1_document_rawContent` 以该 token 取正文。云文档直链（`/docx/<token>`）可直接用该 token 取正文。
  - 图片: server **支持读图**——需要工具集含 `docx.v1.documentBlock.list`（列图片 block 拿 image token）+ `drive.v1.media.batchGetTmpDownloadUrl`（token→临时下载 URL），脚本 `DEFAULT_TOOLS` 已含这两个。若当前会话只暴露了纯文本工具、`rawContent` 把图片显示成 `image.png` 占位名，说明该运行时挂的 lark 用了更窄的 `tools` 列表，需在 lark 设置里放开这两个工具并重连，再 block 列举 + 取临时 URL 下载原图。
  - Guardrails: MCP 是**各运行时各自配置**——本索引列出不等于当前运行时已挂载。若当前会话没暴露 lark 工具，但本机命令存在且用户任务明确要求读 Lark，可直接启动该 server 访问；优先用已配置命令，不要先翻 wrapper 私有代码。stdio 调用按 MCP JSON-RPC newline 消息；启动失败时再读取本机脚本/配置排查。写入运行时配置前仍需用户确认。本机私有脚本，换机器先改路径。
- `chrome-devtools`: 浏览器页面操作、元素检查、console/network、性能调试。配置位置因运行时而异，按当前 agent 的 MCP 配置文件为准。
  - Command: `npx -y chrome-devtools-mcp@latest --no-usage-statistics`
  - Guardrails: 不要假设当前页面正确；先 `list_pages` / `select_page` 确认目标页。若需要复用用户正在使用的 Chrome 登录态，可使用 `--autoConnect` 或 `--browser-url=http://127.0.0.1:9222`。
  - Frontend workflow: 元素优先。调试前端时先用 snapshot / selector / `evaluate_script` 读取关键 DOM、文本、class、`getBoundingClientRect()`、`getComputedStyle()`、console、network。禁止默认全量 snapshot、全页 DOM dump 或一次性读取所有元素；必须先根据路由、用户描述、选择器、可见文本、console/network 错误把范围缩到目标区域，再只取关键字段。若通过元素、样式、尺寸、console/network 已能确认事实，不截图；只有元素读取无法确认视觉事实时，才截图确认遮挡、对齐、颜色、响应式等问题。
  - Fallback: 若运行时提供 Browser/Chrome 类插件，可处理 localhost / 普通网页验证；需要用户 Chrome 登录态、扩展、现有标签页时用 Chrome 插件或 `chrome-devtools` 的 running Chrome 连接模式。
- `node_repl`: Node 持久 REPL；可辅助浏览器/脚本自动化；配置位置因运行时而异。
- `serena`: 代码语义/符号导航 MCP；用于在入口不明确、调用链较长、跨文件关系复杂时，辅助定位候选文件、类、函数、引用、声明和诊断。
  - Example config:
    ```toml
    [mcp_servers.serena]
    command = "__HOME__/.local/bin/serena"
    args = ["start-mcp-server", "--context=<runtime>", "--project-from-cwd", "--enable-web-dashboard=false", "--log-level=WARNING"]

    [mcp_servers.serena.env]
    PATH = "__HOME__/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    ```
  - Trigger: 用户描述模糊、没有给出明确文件/模块、需要理解跨文件调用关系、或要做符号级修改时，由高级模型自行判断是否值得使用。
  - Typical tools: `initial_instructions`、`activate_project`、`get_symbols_overview`、`find_symbol`、`find_referencing_symbols`、`find_declaration`、`get_diagnostics_for_file`。
  - Guardrails: 不替代源码阅读和测试；Serena 只提供候选入口和关系线索，关键事实必须回到源码、命令输出或验证结果核对。用户已给出精确文件/模块，或任务很小、直接读文件更快时，不必使用。索引/语言服务不可用时，退回文本搜索 + 读取文件 + 现有工程 skills。

## External / Not Configured
- `figma`: Figma MCP 旧记录；当前不视为已配置，需要时先征得用户确认再添加。
- `figma-remote-mcp`: Figma 设计上下文、截图、元数据；授权项可能在本机私有配置中，当前不视为已配置 MCP。

## Runtime Plugins
- GitHub、Browser、Chrome、Computer Use、Documents、Spreadsheets、Presentations。
- 相关 skill 入口见 `capabilities/skills.md`。
