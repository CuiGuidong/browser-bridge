# Browser Bridge

Browser Bridge 是一个面向生产级与商用级架构的**本地真实浏览器执行基座**。它允许 AI Agent、自动化脚本或外部业务系统安全地复用本机真实浏览器的登录态（Cookies/Sessions），完成页面读取、数据提取与低风险自动化流程。

与常规的 headless 爬虫或 CDP 直连方案不同，Browser Bridge 采用 **浏览器扩展 + Native Messaging（本地消息传递）** 架构。正常使用时**不需要**开启浏览器的 `--remote-debugging-port`，从而完美规避调试检测和白屏、警告横幅，最大程度降低风控风险。

```text
Client / Agent / 外部系统
  ──[ HTTP API ]──> Browser Bridge Daemon (WSL / Local)
                      ──[ Native Messaging ]──> Chrome / Edge (Windows / macOS)
                                                  ──[ Site Adapters ]──> 真实页面 DOM
```

---

## 核心设计理念

1. **零 Cookie 泄露安全架构**：项目不存储任何账号、密码、Token 或 Cookie。所有登录状态完全复用用户本机的安全浏览器上下文，数据安全符合商用审计要求。
2. **免调试器规避风控**：通过 Native Messaging 驱动，对浏览器无侵入，不触发 WebDriver 或 CDP 调试特征，与真实用户操作具有相同行为特征。
3. **站点语义与控制分离**：通过扩展内置 of Site Adapter 将页面 DOM 转换为干净的结构化数据，daemon 层不接触网页选择器，保证高内聚和易维护性。
4. **人工确认安全红线**：高风险动作（如支付、删除、最终发布等）默认停留在人工确认前，基座只填表、预校验和读取，不替用户做最终风险决策。

---

## 核心功能特性

* **多站点语义读取与适配**：内置主流社交与知识平台（X/Twitter、微博、小红书、知乎、豆瓣等）的适配器，一键获取结构化帖子、趋势、书签或搜索结果。
* **低频自动保活调度器 (Cookie Keepalive)**：
  * **目的**：针对部分平台登录态失效快的问题，在后台维护低频保活。
  * **逻辑**：在每天指定的时段窗口内，随机计划一个未来时刻，强制以独立新 Tab 调起配置的站点首页，随机停留（Dwell）数十秒后自动关闭，有效刷新 Session Cookies。
  * **优雅退出**：保活进程支持 stop-aware 中断，在服务停机或重启时能瞬间识别并彻底关闭已打开的临时浏览器 Tab，杜绝资源泄漏。
  * **可观测快照**：采用原子化覆盖写入技术保存每日运行日志快照，支持配置独立错误快照文件，并通过 `/keepalive/status` 提供内存与磁盘双重一致的监控数据。
* **统一的 FastAPI Web API**：暴露标准的 Web 服务与交互端点，提供易于集成的 OpenAPI 接口规范。

---

## 当前支持站点与能力矩阵

| 站点 | 已支持的核心能力 |
|------|-----------------|
| **X (Twitter)** | 单帖结构化读取、关键词搜索、首页推荐流、趋势流、用户主页指标、书签读取、关注/取关、书签添加/移除 |
| **微博 (Weibo)** | 首页时间线、热门微博流、实时热搜榜、单帖结构化读取、主页指标、内容搜索、自动保活 |
| **小红书 (RED)** | 笔记正文与图文解析、首页推荐、笔记搜索、图文发布前置表单准备、自动保活 |
| **知乎 (Zhihu)** | 回答/文章内容页、实时热榜、主页指标、关键词搜索、登录状态检查 |
| **豆瓣 (Douban)** | 电影/剧集条目、短评读取、综合搜索、想看/在看/看过标记、登录状态检查、自动保活 |
| **B站 / Reddit** | 内容页读取、热门推荐流、用户主页指标、搜索、登录状态 |
| **通用只读支持** (50+ 平台) | 包含 1688、36氪、大众点评、淘宝、抖音、Grok、linux.do、SMZDM 等，支持页面内容提取、搜索及登录态诊断。 |

---

## 快速开始

选择与您的本机系统环境匹配的安装模式。

### macOS 单机模式

**前置依赖**：
* macOS (Darwin)
* Google Chrome 或 Microsoft Edge 浏览器
* Python 3.10+ (脚本会自动在系统中检索 3.13 / 3.12 / 3.11 / 3.10 等版本)

**安装与配置**：
```bash
# 1. 克隆仓库
git clone <repo-url>
cd browser-bridge

# 2. 运行配置脚本（如需指定 Python，可传入 PYTHON 环境变量）
PYTHON=/opt/homebrew/bin/python3.12 ./scripts/setup_macos.sh
```
> [!NOTE]
> 刚克隆后 `extension/manifest.json` 不存在。请勿在运行 setup 脚本前加载扩展，否则浏览器会报错。setup 脚本会自动生成它。

**运行与验证**：
```bash
# 启动 Bridge 守护进程
./scripts/start_bridge.sh

# 检查本地链路及通信状态
./scripts/doctor.sh

# 确认服务正常可用
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

---

### Windows + WSL 混合模式

此模式适用于：在 WSL2 Linux 子系统中运行 Bridge daemon 与 Python 虚拟环境，在宿主 Windows 系统中运行真实浏览器（Chrome/Edge）与 Native Host launcher。

**配置步骤**：
```bash
# 在 WSL 终端运行配置
./scripts/setup_wsl.sh
```
脚本执行完毕后会输出：
1. Windows 侧浏览器需要加载的 `extension/` 局域网/共享路径。
2. Windows PowerShell 侧用于安装注册 Native Host 的指令。

**在 Windows PowerShell 中注册 Native Host**：
```powershell
powershell -ExecutionPolicy Bypass -File "<WSL-path>\install-native-host.ps1" `
  -ExtensionId "<your-extension-id>" `
  -Browser edge `
  -BridgeUrl "http://127.0.0.1:17777"
```
*(如果是 Chrome 浏览器，请将 `-Browser edge` 修改为 `-Browser chrome`)*

---

## 运维配置与保活服务 (operations)

Browser Bridge 支持通过环境变量进行定制。完整的配置表参见 [operations.md](file:///home/cuiguidong/workspace/personal/projects/Python/browser-bridge/docs/operations.md)。

### Cookie 保活配置示例

如果需要为某些平台维持长期的登录状态，可以在本地 `.env.local` 文件中配置保活服务：

```env
# 启用保活调度
BB_KEEPALIVE_ENABLED=true
# 指定需要保活的站点（英文标识，逗号分隔）
BB_KEEPALIVE_SITES=douban,weibo,xiaohongshu
# 保活执行的时间窗口（每日在这个范围内随机选一个时刻）
BB_KEEPALIVE_WINDOW_START=09:30
BB_KEEPALIVE_WINDOW_END=22:30
# 浏览器 Tab 调起后停留时长（秒）的随机范围
BB_KEEPALIVE_DWELL_SECONDS_MIN=30
BB_KEEPALIVE_DWELL_SECONDS_MAX=90
# 状态快照文件路径（原子覆盖写入）
BB_KEEPALIVE_STATUS_FILE=/tmp/browser-bridge-keepalive-status.json
```

---

## 使用与集成入口

* **OpenAPI 接口文档**：启动服务后直接访问 [http://127.0.0.1:17777/docs](http://127.0.0.1:17777/docs) 即可查看完整 Swagger UI。
* **健康检查 API**：`GET /health`
* **活跃 Tab API**：`GET /tabs`
* **扩展状态 API**：`GET /extension/state`
* **保活监控 API**：`GET /keepalive/status` (返回当前保活所处的 phase 及每个配置站点的历史尝试结果)。

---

## 安全边界与审计规则

为了保障商用项目的安全合规，Browser Bridge 严格实施以下安全红线约束：
* **无代理旁路**：不会对外部任何支付、账号注销、高保密操作提供静默确认接口。
* **纯本地流转**：API 和 Native Messaging 均在 localhost 或受保护的 WSL 网卡中通信，数据从不上传至任何第三方服务器。
* **凭据隔离**：不读取或拦截浏览器的密码管理器、不提供任何绕过 2FA/MFA 与验证码的功能。

---

## License

MIT License.
