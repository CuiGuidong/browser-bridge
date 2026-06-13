# Browser Bridge

Browser Bridge 是让 Agent 在**真实浏览器**和**真实登录态**中稳定执行跨站点任务的本地桥。

它把浏览器控制、站点语义和固定流程拆开：

```text
Client / Agent
  -> Browser Bridge HTTP API
    -> Workflow
      -> Extension + Adapter
        -> Real Browser Page
```

当前底层控制通过 Native Messaging + 浏览器扩展完成，正常使用不需要 `--remote-debugging-port`，也不会触发浏览器调试横幅。

## 当前支持

| 站点 | 已支持能力 |
|------|------------|
| X | 读单帖、搜索、首页流、趋势流、主页指标、书签、关注/取关、加书签/移除书签 |
| 小红书 | 读笔记、首页推荐流、搜索、图文发帖准备 |
| 微博 | 首页流、热门微博流、热搜榜、单帖读取、主页指标、搜索 |
| 知乎 / B 站 / Reddit | 内容页、热榜/热门流、主页指标、搜索、登录状态 |
| YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富 | 第一版只读支持：内容页、主页指标、搜索、登录状态 |
| 1688 / 36氪 / 贴吧 / Aibase / Bloomberg / 大众点评 / 抖音 / Google / gov.cn / Grok / 虎扑 / IMDb / 京东 / linux.do / V2EX / 什么值得买 / 淘宝 / Wikipedia / 闲鱼 | 第一版低频只读支持：内容页、主页指标、搜索、登录状态 |

更细的能力矩阵见 [docs/capabilities.md](docs/capabilities.md)。

## 快速开始：macOS 单机

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

## Windows + WSL

Windows + WSL 路径是：WSL 运行 Bridge 和 Python venv，Windows 运行 Chrome/Edge 与 Native Host launcher。

```bash
./scripts/setup_wsl.sh
```

脚本会输出 Windows PowerShell 侧的 Native Host 安装命令。完整说明见 [docs/installation.md](docs/installation.md)。

## 文档

- 安装指南：[docs/installation.md](docs/installation.md)
- 架构规范：[docs/architecture.md](docs/architecture.md)
- API 与 workflow：[docs/interfaces.md](docs/interfaces.md)
- 站点能力矩阵：[docs/capabilities.md](docs/capabilities.md)
- 开发指南：[docs/development.md](docs/development.md)
- 运维诊断：[docs/operations.md](docs/operations.md)
- 新站点适配：[docs/new-site-adaptation-guide.md](docs/new-site-adaptation-guide.md)

## 安全边界

以下动作必须保持人工确认边界：

- 登录 / 登出
- 2FA / MFA / 验证码
- 改密码 / 改邮箱 / 改手机号
- 支付 / 转账
- 发布内容 / 删除内容
- 第三方授权

## License

MIT
