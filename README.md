# Browser Bridge

Browser Bridge 是一个开源的本地浏览器执行基座，让 Agent、脚本或本地应用可以在**真实浏览器**和**真实登录态**中读取页面、执行低风险流程，并获得结构化结果。

它把浏览器控制、站点语义和固定流程拆开：

```text
Client / Agent
  -> Browser Bridge HTTP API
    -> Workflow
      -> Extension + Adapter
        -> Real Browser Page
```

当前底层控制通过 Native Messaging + 浏览器扩展完成，正常使用不需要 `--remote-debugging-port`，也不会触发浏览器调试横幅。项目不内置账号、cookie 或私有配置；所有登录态都来自用户本机浏览器。

## 当前支持

| 站点 | 已支持能力 |
|------|------------|
| X | 读单帖、搜索、首页流、趋势流、主页指标、书签、关注/取关、加书签/移除书签 |
| 小红书 | 读笔记、首页推荐流、搜索、图文发帖准备 |
| 微博 | 首页流、热门微博流、热搜榜、单帖读取、主页指标、搜索 |
| 知乎 / B 站 / Reddit | 内容页、热榜/热门流、主页指标、搜索、登录状态 |
| YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富 | 第一版只读支持：内容页、主页指标、搜索、登录状态 |
| 1688 / 36氪 / 贴吧 / Aibase / Bloomberg / 大众点评 / 抖音 / Google / gov.cn / Grok / 虎扑 / IMDb / 京东 / linux.do / V2EX / 什么值得买 / 淘宝 / Wikipedia / 闲鱼 | 第一版低频只读支持：内容页、主页指标、搜索、登录状态 |

## 快速开始

选择与你的系统匹配的安装方式。

### macOS 单机

前置条件：

- macOS
- Chrome 或 Edge
- Python 3.10+

安装：

```bash
git clone <repo-url>
cd browser-bridge-project
./scripts/setup_macos.sh
```

脚本会创建 `bridge/.venv`、安装依赖、生成扩展 manifest，并引导你加载 `extension/` 目录和安装 Native Host manifest。

启动 Bridge：

```bash
./scripts/start_bridge.sh
```

诊断：

```bash
./scripts/doctor.sh
```

确认服务可用：

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

项目根 `.env.local` 只用于 Bridge 服务监听地址等本机配置，不参与 skill 默认连接目标解析。Agent skill 如需连接另一台 Bridge，应在运行命令中传入 `BRIDGE_URL`，或在对应 skill 脚本目录的 `.env` 中配置。

### Windows + WSL

Windows + WSL 路径是：WSL 运行 Bridge 和 Python venv，Windows 运行 Chrome/Edge 与 Native Host launcher。

```bash
./scripts/setup_wsl.sh
```

脚本会输出：

- Windows 浏览器需要加载的 `extension/` 路径
- Windows PowerShell 侧 Native Host 安装命令
- WSL 侧启动和诊断命令

安装 Native Host 时，`-Browser` 应与实际加载扩展的浏览器一致：

```powershell
powershell -ExecutionPolicy Bypass -File "<path>\install-native-host.ps1" `
  -ExtensionId "<extension-id>" `
  -Browser edge `
  -BridgeUrl "http://127.0.0.1:17777"
```

如果使用 Chrome，把 `-Browser edge` 改成 `-Browser chrome`。只有两个浏览器都加载同一个扩展 ID 时才使用 `-Browser both`。

## 使用入口

- API 文档：启动后访问 `http://127.0.0.1:17777/docs`
- 健康检查：`curl --noproxy '*' -sS http://127.0.0.1:17777/health`
- 标签页列表：`curl --noproxy '*' -sS http://127.0.0.1:17777/tabs`
- 扩展状态：`curl --noproxy '*' -sS http://127.0.0.1:17777/extension/state`

普通用户不需要手写 Native Host manifest。脚本会生成 manifest、launcher 和浏览器注册项。

生产扩展同步目标通过命令环境变量传入，例如：

```bash
BB_HOST_EXTENSION_DIR=/path/to/host/extension ./scripts/build_prod_extension.sh
```

## 安全边界

以下动作必须保持人工确认边界：

- 登录 / 登出
- 2FA / MFA / 验证码
- 改密码 / 改邮箱 / 改手机号
- 支付 / 转账
- 发布内容 / 删除内容
- 第三方授权

Browser Bridge 不绕过验证码、MFA、风控、付费墙或平台限制，不调用站点私有逆向 API 替代真实页面读取。

## License

MIT
