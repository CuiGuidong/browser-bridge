# Browser Bridge

让 Agent 在**真实浏览器**和**真实登录态**中稳定执行跨站点任务的本地桥。

## 它解决什么问题

很多基于 CDP、Playwright 或 RPA 的工具，能控制网页，但一进入真实使用场景就容易暴露几个问题：

- 脱离真实登录态，很多页面在 demo 环境能跑，在日常账号环境里不稳定
- 浏览器控制和站点语义混在一起，新增一个站点就像重写一套系统
- 固定流程和开放式推理没有边界，脚本越堆越碎，后续很难维护

Browser Bridge 解决的不是“如何点页面”，而是如何让 Agent 在真实账号浏览器环境里**长期、稳定、可扩展**地完成读取、判断、执行和发布。

## 和同类工具的差异

- 不是纯浏览器控制工具，而是面向真实账号环境的 Agent 执行底座
- 不是把所有逻辑塞进 prompt，而是把确定性流程沉到 workflow，把开放式判断留给 Agent
- 不是单站点脚本集合，而是可持续扩站点的 `adapter + workflow + skill` 分层架构
- 不是只读 demo，已经覆盖读取、搜索、动作执行，以及小红书图文发帖准备这类真实写操作

## 当前支持

| 站点 | 已支持能力 |
|------|------------|
| X | 读单帖、搜索、首页流、趋势流、主页指标、书签、关注/取关、加书签/移除书签 |
| 小红书 | 读笔记、首页推荐流、搜索、图文发帖准备 |
| 微博 | 首页流、热门微博流、热搜榜、单帖读取、主页指标、搜索 |
| 知乎 / B 站 / Reddit | 内容页、热榜/热门流、主页指标、搜索、登录状态 |
| YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富 | 第一版只读支持：内容页、主页指标、搜索、登录状态 |
| 1688 / 36氪 / 贴吧 / Aibase / Bloomberg / 大众点评 / 抖音 / Google / gov.cn / Grok / 虎扑 / IMDb / 京东 / linux.do / V2EX / 什么值得买 / 淘宝 / Wikipedia / 闲鱼 | 第一版低频只读支持：内容页、主页指标、搜索、登录状态 |

更细的站点能力、输入兼容形态、当前限制见：

- [site-support.md](docs/site-support.md)

## 一个最小心智模型

```text
Skill / Agent
  -> Browser Bridge HTTP API
    -> Workflow
      -> Extension + Adapter
        -> Real Browser Page
```

分层职责很简单：

- `CDP`：浏览器控制与诊断
- `Extension + Adapter`：站点语义
- `Bridge + Workflow`：固定流程与页面生命周期
- `Skill / Agent`：开放式决策与长链推理

这意味着：

- 固定任务优先做成 workflow
- 开放式任务保留给 Agent 编排
- 新站点优先沉到 adapter，不回流成脚本补丁

正式架构规范见：

- [architecture-spec.md](docs/architecture-spec.md)

## 当前能做什么

- 让 Agent 读取真实登录态下的 X、微博、小红书内容
- 获取首页流、热门流、热搜榜、搜索结果等结构化信息
- 在 X 中执行关注、取关、加书签、移除书签
- 在小红书中自动进入图文发帖编辑态、上传图片、填写标题正文，并停在人工确认发布前
- 通过统一 HTTP API 把这些能力暴露给 skill、脚本或更高层 Agent

## 快速开始

### 1. 启动带 CDP 的浏览器

```bash
# Edge (macOS)
open -a "Microsoft Edge" --args --remote-debugging-port=9222

# Chrome (macOS)
open -a "Google Chrome" --args --remote-debugging-port=9222

# Chrome (Linux)
google-chrome --remote-debugging-port=9222
```

默认示例使用浏览器常见的 `9222` 端口。  
如果你的本地环境使用了不同 host / port，可在启动 bridge 前通过环境变量覆盖：

```bash
export CDP_PUBLIC_HOST=127.0.0.1
export CDP_CONNECT_HOST=127.0.0.1
export CDP_PORT=9222
```

### 2. 启动 Bridge

```bash
cd bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python -m app.server
```

默认监听：

- `http://127.0.0.1:17777`

API 文档：

- `http://127.0.0.1:17777/docs`

### 3. 加载扩展

```bash
cd extension
# 在 chrome://extensions 或 edge://extensions 加载此目录
```

## 文档导航

- 想快速理解项目：先读这份 README
- 想搭建本地开发环境：读 [development.md](docs/development.md)
- 想接手架构设计：读 [architecture-spec.md](docs/architecture-spec.md)
- 想排查真实环境问题：读 [implementation-guide.md](docs/implementation-guide.md)
- 想看站点支持矩阵：读 [site-support.md](docs/site-support.md)
- 想看接口与 workflow 参数：读 [api-reference.md](docs/api-reference.md)
- 想继续扩新站点：读 [new-site-adaptation-guide.md](docs/new-site-adaptation-guide.md)
- 想了解部署与运维：读 [operations.md](docs/operations.md)
- 想看完整文档索引：读 [docs/index.md](docs/index.md)

## 安全边界

以下动作必须保持谨慎，必要时要求人工明确确认：

- 登录 / 登出
- 2FA / MFA
- 验证码
- 改密码 / 改邮箱 / 改手机号
- 支付 / 转账
- 发布内容 / 删除内容
- 第三方授权

## License

MIT
