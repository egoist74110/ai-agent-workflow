# MCP Index

规则：先确认任务需要 MCP，再使用对应能力；不要假设服务已连接、已安装或当前页面正确。需要新增/安装/启用 MCP 时，必须先向用户说明原因、命令/配置和影响范围，得到确认后再执行。

## Configured MCP
- `ado-work-items` / `adoWorkItems`: Azure DevOps work items。
  - Example config:
    ```toml
    [mcp_servers.adoWorkItems]
    command = "__HOME__/my-own-script/.venv/bin/python"
    args = ["__HOME__/my-own-script/app_ado/mcp_ado_work_items_server.py"]
    ```
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
