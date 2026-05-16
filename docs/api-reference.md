# Browser Bridge API 与 Workflow 参考

_最后更新：2026-05-16_
_状态：接口参考_

本文档聚焦：

- Bridge 暴露了哪些接口
- 当前 workflow 有哪些主要参数

补充：

- CDP 连接地址当前支持通过环境变量配置
- 默认假设浏览器 CDP 暴露在 `127.0.0.1:9222`
- 如本地环境不是默认值，可覆盖：
  - `CDP_PUBLIC_HOST`
  - `CDP_CONNECT_HOST`
  - `CDP_PORT`
  - `CDP_TIMEOUT_SECONDS`

如果你更关心“这个项目为什么这样分层”，先读：

- [architecture-spec.md](architecture-spec.md)

如果你更关心“真实环境里怎么调试和避坑”，再读：

- [implementation-guide.md](implementation-guide.md)

如果你关心 B 站、抖音等视频站点后续如何做视频理解管线，读：

- [video-asset-pipeline-design.md](video-asset-pipeline-design.md)

## 基础 Bridge API

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /version` | 浏览器 / CDP 版本信息 |
| `GET /tabs` | 列出浏览器 tab |
| `POST /open` | 打开或复用页面 |
| `POST /activate` | 激活 tab |
| `GET /wait` | 等待页面稳定 |
| `GET /page-info` | 获取页面信息 |
| `GET /page-content` | 获取基础文本内容 |
| `GET /probe-readiness` | 通用页面就绪探针 |
| `POST /screenshot` | 截图 |
| `GET /query` | 基础 DOM 查询 |
| `POST /evaluate` | 执行 JS |

## 站点语义 API

| 端点 | 功能 |
|------|------|
| `GET /site/capabilities` | 查询站点能力 |
| `POST /site/read` | 调用站点读取能力 |
| `POST /site/action` | 调用站点动作能力 |
| `POST /workflow/run` | 调用固定流程 workflow |
| `GET /login/status` | 检查单站登录状态 |
| `POST /login/check` | 批量检查登录状态，可触发通知 |

使用约定：

- 固定流程优先走 `/workflow/run`
- 站点语义能力优先接到 `/site/read` / `/site/action`
- `/query` / `/evaluate` 属于浏览器级工具接口，不是站点语义接口

### `/site/capabilities` 能力发现

不传 `targetId` 时，接口只返回 bridge 侧注册能力，不依赖当前浏览器页面或扩展运行时：

```text
GET /site/capabilities?site=xiaohongshu
```

关键返回：

```json
{
  "ok": true,
  "action": "site-capabilities",
  "data": {
    "site": "xiaohongshu",
    "registry": {
      "site": "xiaohongshu",
      "read": ["read_post", "read_post_metrics", "read_profile_metrics", "account_status"],
      "action": [],
      "workflow": ["read_post", "prepare_publish_post", "read_post_metrics", "read_profile_metrics", "account_status"]
    },
    "runtime": null
  }
}
```

不传 `site` 时返回所有已注册站点能力。只有传入 `targetId` 时，接口才会额外查询页面运行时能力。

### 语义接口错误结构

`/workflow/run`、`/site/read`、`/site/action` 失败时返回结构化错误：

```json
{
  "ok": false,
  "action": "workflow-run",
  "error": {
    "code": "capability_missing",
    "message": "workflow not supported",
    "detail": {
      "site": "xiaohongshu",
      "workflow": "unknown_workflow"
    }
  }
}
```

当前错误码：

- `capability_missing`
- `workflow_failed`
- `site_not_supported`
- `login_required`
- `human_confirmation_required`

`/site/read` 和 `/site/action` 会先按 registry 检查 `site` 与 `kind`。未知站点返回 `site_not_supported`，未知读取或动作能力返回 `capability_missing`。

### 登录状态检查

`account_status` 是站点通用 workflow：

```json
{
  "site": "bilibili",
  "workflow": "account_status",
  "params": {},
  "timeoutSeconds": 20
}
```

也可以使用运维入口：

```text
GET /login/status?site=bilibili&notify=true
POST /login/check
```

`/login/check` 请求示例：

```json
{
  "sites": ["x", "weibo", "xiaohongshu", "bilibili"],
  "notify": true,
  "timeoutSeconds": 20
}
```

返回不包含 cookie、token 或密码。通知配置：

- `BB_NOTIFY_TELEGRAM_BOT_TOKEN`
- `BB_NOTIFY_TELEGRAM_CHAT_ID`
- `BB_NOTIFY_MIN_INTERVAL_SECONDS`
- `BB_NOTIFY_WECHAT_WEBHOOK`

Telegram 已可用；微信先按企业微信/兼容 webhook 预留。

## 扩展集成 API

| 端点 | 功能 |
|------|------|
| `POST /extension/report` | 扩展被动上报页面状态 |
| `GET /extension/state` | 查看最近扩展状态 |
| `GET /extension/pull` | 扩展主动拉取桥端命令 |
| `POST /extension/result` | 扩展回传主动命令结果 |

## Playwright API

| 端点 | 功能 |
|------|------|
| `POST /playwright/connect` | 连接 Playwright |
| `POST /playwright/disconnect` | 断开 Playwright |
| `GET /playwright/pages` | 列出 Playwright 页面 |
| `POST /playwright/click` | 点击 |
| `POST /playwright/fill` | 填写 |
| `POST /playwright/evaluate` | 执行 JS |
| `GET /playwright/wait-selector` | 等待 selector |

## 当前 workflow 参数约定

### X

- `read_post`
  - 必填：`url`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 兼容别名：`query`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `list_bookmarks`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 常用可选：`mode`(`for_you|following`)、`targetCount`、`continuous`
- `read_trending`
  - 打开 X Explore/Trending 页面并返回可见趋势流条目
- `read_profile_metrics`
  - 必填：`url` 或 `handle`
  - 返回主页公开信息、可见指标和当前可见关注状态，不返回 cookie/token
- `follow_user` / `unfollow_user`
  - 必填：`handle`
- `add_bookmark` / `remove_bookmark`
  - 必填：`url`
- `account_status`
  - 可选：`url`
  - 返回登录状态、是否需要人工登录和可见账号信息，不返回 cookie/token

### 小红书

- `read_post`
  - 必填：`url` 或 `noteId`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 兼容别名：`query`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `prepare_publish_post`
  - 必填：`title`、`content`、`imagePaths`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_post_metrics`
  - 必填：`url` 或 `noteId`
  - 返回 `metrics.views/shares` 等不可见指标时使用 `null`
- `read_profile_metrics`
  - 必填：`url`
  - 返回主页指标和可见的 `recentPosts`
- `account_status`
  - 可选：`url`
  - 返回登录状态、是否需要人工登录和可见账号信息，不返回 cookie/token

### 微博

- `read_post`
  - 必填：`url`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 常用可选：`targetCount`、`scrollRounds`、`waitForReady`、`intervalSeconds`
- `read_hot_feed`
  - 常用可选：`targetCount`、`scrollRounds`、`waitForReady`、`intervalSeconds`
- `read_hot_search`
  - 常用可选：`targetCount`、`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 兼容别名：`query`
  - 常用可选：`targetCount`、`waitForReady`、`intervalSeconds`
- `read_profile_metrics`
  - 必填：`url`，或 `userId`/`uid`，或 `screenName`/`handle`
  - 返回微博主页公开指标和可见近期内容，不返回 cookie/token
- `account_status`
  - 可选：`url`
  - 返回登录状态、是否需要人工登录和可见账号信息，不返回 cookie/token

### 知乎 / B 站 / 抖音 / Reddit / YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富 / 1688 / 36氪 / 贴吧 / Aibase / Bloomberg / 大众点评 / Google / gov.cn / Grok / 虎扑 / IMDb / 京东 / linux.do / V2EX / 什么值得买 / 淘宝 / Wikipedia / 闲鱼

- `read_post`
  - 必填：`url`
  - 知乎、Reddit、微信公众号、豆瓣、HackerNews、Instagram、雪球、东方财富、1688、36氪、贴吧、Aibase、Bloomberg、大众点评、Google、gov.cn、Grok、虎扑、IMDb、京东、linux.do、V2EX、什么值得买、淘宝、Wikipedia、闲鱼返回内容页标题、作者/来源、摘要和页面可见互动指标
  - B 站、抖音和 YouTube 返回视频页元信息和公开互动指标，不解析视频内容本身
- `read_profile_metrics`
  - 必填：`url`
  - 返回主页公开指标和可见的近期内容链接
- `search`
  - 必填：`keyword`
  - 兼容别名：`query`
  - 返回搜索结果中的语义链接列表
- `read_hot`
  - 当前支持：知乎、B 站、Reddit
  - 返回热榜/热门页中可见的语义链接列表；B 站只返回视频元信息链接，不解析视频内容本身
- `account_status`
  - 可选：`url`
  - 返回登录状态、是否需要人工登录和可见账号信息，不返回 cookie/token

安全边界：

- 这些参考 OpenCLI 扩展方向选取的新站点当前只暴露读取 workflow，不暴露 `/site/action` 写能力
- Instagram、雪球、东方财富、电商、招聘、二手交易、AI 会话等高风控或高敏感站点默认只做低频真实浏览器读取
- 1688、京东、淘宝、闲鱼、大众点评等不自动登录、不加购、不下单、不支付、不发布、不聊天
- Grok 只提供页面状态和可见内容读取，不自动发送 prompt
- 微信公众号不自动创建草稿或群发，后续如做发布准备也必须停在人工确认前

## workflow 运行上的共同约定

- 默认允许新开临时标签页
- 浏览器页签总数达到上限时，会优先复用同站点标签页
- workflow 结束后会关闭“本次新开”的临时标签页
- 如果 workflow 返回的 `targetId` 为 `null`，通常表示临时页已在 workflow 内关闭
- 如果传入 `targetId`，表示“指定执行容器”，不表示保持当前页原样不动

## 什么时候不该直接看这份文档

- 想判断“是代码问题还是宿主环境问题”：读 [implementation-guide.md](implementation-guide.md)
- 想知道当前每个站点到底支持什么：读 [site-support.md](site-support.md)
- 想扩一个新站点：读 [new-site-adaptation-guide.md](new-site-adaptation-guide.md)
