# MCP 工具状态检查报告
生成时间：2026-06-02

---

## 📊 总结

| 工具 | 类型 | 状态 | 说明 |
|------|------|------|------|
| **Serena** | MCP | ✅ 可用 | 代码导航和符号搜索 |
| **Chrome DevTools** | MCP | ✅ 可用 | 浏览器调试和自动化 |
| **Lark (飞书)** | MCP | ❌ 不可用 | 个人工具，需要本地路径配置 |
| **ADO Work Items** | MCP | ❌ 不可用 | 个人工具，需要本地路径配置 |
| **Bilibili 转录** | Skill | ⚠️ 部分可用 | 缺少 ffmpeg 二进制文件 |

---

## ✅ 可用的 MCP 工具

### 1. Serena (代码导航 MCP)
**位置：** `C:\Users\q1243\.local\bin\serena.exe`  
**版本：** 1.5.3  
**状态：** ✅ 完全可用

**特性：**
- 代码语义和符号导航
- 跨文件引用搜索
- 变量、函数、类定义查询
- 项目诊断信息

**配置：** `ai-config/mcp/serena.toml` 已正确配置
```toml
[mcp_servers.serena]
command = "__HOME__/.local/bin/serena"
args = ["start-mcp-server", "--context=claude-code", "--project-from-cwd", "--enable-web-dashboard=false", "--log-level=WARNING"]
```

**用法：** 当需要定位跨文件函数调用、理解代码结构时自动使用

---

### 2. Chrome DevTools (浏览器调试 MCP)
**命令：** `npx -y chrome-devtools-mcp@latest --no-usage-statistics`  
**状态：** ✅ 完全可用

**特性：**
- 页面元素检查和 DOM 操作
- Console 日志和网络请求监控
- 性能分析和截图
- 表单填充和自动化测试

**配置：** `ai-config/mcp/chrome-devtools.toml` 已正确配置

**用法：** 当需要验证 UI 变化、调试前端问题时使用

---

## ❌ 不可用的 MCP 工具

### 3. Lark (飞书文档 MCP)
**状态：** ⚠️ 需 App 在跑 + 一次 OAuth  
**原因：** 连 App 托管的常驻 HTTP 实例，需先在 App UI 完成 OAuth 登录

**当前配置：** `ai-config/mcp/lark.toml`（HTTP，连常驻实例，不 spawn 本地进程）
```toml
[mcp_servers.lark]
url = "http://localhost:3000/mcp"
```

**架构：** 上游 lark-mcp 跑 `--oauth --token-mode user_access_token`，客户端连上需带
`Authorization: Bearer <UAT>`。App 在自己这边完成 Feishu OAuth 并持有会自动续期的 UAT，
再由 `app_lark/lark_token_inject.py` 把这个 UAT 作为**静态 bearer 注入**到本机各工具的 MCP 配置 header 里
（lark-mcp 的 `verifyAccessToken` 只按 bearer 精确查 store，不绑 client）。配合 supersession 补丁，
注入的 bearer 过期后底层自动续期、长期有效。**仓库里不存 token**（密钥、会轮换、按机器不同）。

**修复方式：**
1. 确认 App 在运行（HTTP server 由 App 托管，默认端口 3000）并已在 App UI 完成 Lark 登录
2. 跑注入工具把 App 的 UAT 写进本机 `~/.claude.json` 的 lark header（会先备份 + 原子写）：
   `cd ~/my-own-script && .venv/bin/python -c "from app_lark.lark_token_inject import inject_bearer_to_all_tools as f; print(f(('claude',))['message'])"`
3. 重启 / 重连 lark MCP 读到带 header 的新配置，`mcp__lark__*` 工具即出

**注意：** 别在仓库或安装器里写死 header，也别让 `claude mcp` 覆盖已注入 header 的条目；
注入是本机运行时动作，由 App 工具负责。`~/.claude.json` 有写保护 deny 规则，注入需在自己终端跑。

---

### 4. ADO Work Items (Azure DevOps MCP)
**状态：** ❌ 不可用  
**原因：** 个人工具，需要本地路径配置

**当前配置：** `ai-config/mcp/ado-work-items.toml`
```toml
[mcp_servers.adoWorkItems]
command = "__HOME__/my-own-script/.venv/bin/python"
args = ["__HOME__/my-own-script/app_ado/mcp_ado_work_items_server.py"]
```

**修复方式：** 同 Lark 工具

**状态检查：**
```
❌ ~/my-own-script/ 不存在
❌ 脚本文件未找到
```

---

## ⚠️ 部分可用的工具

### 5. Bilibili 视频转录 (Skill)
**位置：** `ai-prompt/skills/bilibili-auto-transcript/`  
**状态：** ⚠️ 部分可用（缺少必要依赖）

**已安装的依赖：**
- ✅ yt-dlp `2026.03.17` - 视频下载工具
- ✅ openai-whisper `20250625` - 语音转文字（GPU 加速）

**缺失的依赖：**
- ❌ ffmpeg 二进制文件（必需）
- ⚠️ opencc （可选，繁转简工具）

**修复方式：**

#### 选项 A：使用 Scoop（推荐）
```powershell
# 先安装 scoop
iwr -useb get.scoop.sh | iex

# 安装 ffmpeg
scoop install ffmpeg

# 验证安装
ffmpeg -version
```

#### 选项 B：从官网下载
访问 https://ffmpeg.org/download.html，下载 Windows 版本，解压到 `C:\Program Files\ffmpeg\`，然后添加到 PATH。

#### 选项 C：使用 Chocolatey
```powershell
choco install ffmpeg
```

#### 验证所有依赖：
```powershell
yt-dlp --version        # 应该显示版本号
ffmpeg -version         # 应该显示版本号
whisper --help          # 应该显示帮助信息
```

**B站工具使用步骤：**

1. **创建 B 站收藏夹** - 新建公开收藏夹，记下 `fid=` 后的 ID
2. **修改脚本配置** - 编辑 `scripts/bilibili_scanner.py`，改 `FAV_MEDIA_ID`
3. **浏览器登录** - 用 Chrome/Edge 打开 bilibili.com 并登录（获取 Cookie）
4. **验证依赖** - 运行上面的验证命令
5. **手动转录示例：**
```bash
bash ~/.ai-prompt/skills/bilibili-auto-transcript/scripts/bilibili_transcript.sh "https://www.bilibili.com/video/BVxxxxx/"
```

---

## 📋 当前 MCP 配置文件列表

```
ai-config/mcp/
├── serena.toml              ✅ 已配置，可用
├── chrome-devtools.toml     ✅ 已配置，可用
├── lark.toml                ❌ 未配置（个人工具）
└── ado-work-items.toml      ❌ 未配置（个人工具）
```

---

## 🔧 建议行动

### 立即可做：
1. ✅ Serena 和 Chrome DevTools 已经可用，无需操作
2. 为 B 站转录工具安装 ffmpeg（见上面的修复方式）

### 可选项：
1. 如果你有 Lark/飞书文档需要读取，配置 `my-own-script` 路径
2. 如果你有 Azure DevOps，配置 ADO MCP 路径

### 禁用不用的工具：
如果不需要 Lark 和 ADO，可以将这两个 TOML 文件移到备份目录或删除，这样启动时不会尝试加载它们。

---

## 📝 文件修改记录

**修改过的配置：**
- `ai-config/mcp/serena.toml` - `--context` 从 `<runtime>` 改为 `claude-code` ✅

---

## ✨ 总结

- **2 个 MCP 完全可用** (Serena, Chrome DevTools)
- **2 个 MCP 不可用** (需要个人本地配置)
- **1 个 Skill 部分可用** (需要 ffmpeg)

**下一步建议：** 根据你的需求，安装 ffmpeg 或禁用不需要的 MCP 工具。
