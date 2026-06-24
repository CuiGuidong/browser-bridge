# Browser Bridge API 与 Workflow 参考

_最后更新：2026-06-24_
_状态：接口参考_

本文档聚焦：

- Bridge 暴露了哪些接口
- 当前 workflow 有哪些主要参数

补充：

- 浏览器控制通过 Native Messaging 通道（扩展 ↔ Bridge），无需 `--remote-debugging-port`
- `BROWSER_RUNTIME` 为历史兼容配置，当前无实际行为差异，页面控制全部由 NativeBrowserRuntime 跑通并走 Native Messaging 通道

如果你更关心“这个项目为什么这样分层”，先读：

- [architecture.md](architecture.md)

如果你更关心“真实环境里怎么调试和避坑”，再读：

- [development.md](development.md)

如果你关心 B 站、抖音等视频站点后续如何做视频理解管线，读：

- [video-asset-pipeline-design.md](video-asset-pipeline-design.md)

## 基础 Bridge API

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /version` | 浏览器版本信息（Facade 对齐版） |
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
| `GET /extension/state` | 查看最近扩展状态（含 native report 缓存） |
| `POST /native/session/register` | Native host shim 注册 session |
| `GET /native/session/pull` | Native host shim 长轮询命令 |
| `POST /native/session/result` | Native host shim 回传结果/报告 |
| `POST /native/session/unregister` | Native host shim 注销 session |

## `read_post.v1` 语义输出

`read_post` workflow 成功响应同时保留三层数据：

- `semantic`：稳定语义合同，供 skill 默认输出和外部系统读取。
- `diagnostics`：精简诊断摘要，供 `--debug` 和排障使用。
- 旧 raw payload：原 workflow 字段，如 `content`、`page`、`signals`、`debug`、`rawPayload`，只供 `--raw` 和开发调试使用。

skill 默认只打印 `semantic`。默认输出不包含 `targetId`、`items`、`checkpoint`、`page`、`signals`、`debug`、`rawPayload`、`primaryText` 等排障字段。

### 默认结构

```json
{
  "ok": true,
  "site": "x",
  "schemaVersion": "read_post.v1",
  "contentItem": {
    "id": "2068988425072697742",
    "url": "https://x.com/laobaishare/status/2068988425072697742",
    "type": "post",
    "platformType": "tweet",
    "title": null,
    "author": {
      "id": null,
      "displayName": "老白（每日干货分享）",
      "handle": "@laobaishare",
      "profileUrl": null,
      "verified": null
    },
    "published": {
      "at": "2026-06-22T09:24:15.000Z",
      "label": "下午5:24 · 2026年6月22日",
      "location": null,
      "source": null
    },
    "text": "正文；如果正文中图片位置有语义，会保留 [Image Local: ... | Remote: ...] 占位符。",
    "summary": null,
    "tags": [],
    "media": [
      {
        "type": "image",
        "url": "https://pbs.twimg.com/media/example.jpg",
        "localPath": "/tmp/browser-bridge-cache/example.jpg",
        "order": 1,
        "placement": "after_text",
        "alt": null,
        "title": null,
        "source": null
      }
    ],
    "metrics": {
      "comments": null,
      "favorites": null,
      "likes": null,
      "quotes": null,
      "reposts": null,
      "shares": null,
      "views": null
    },
    "platformMetrics": {}
  },
  "thread": {
    "items": [],
    "relation": "none",
    "complete": null
  },
  "comments": {
    "items": [],
    "limit": 20,
    "count": 0,
    "total": null,
    "hasMore": null,
    "nextCursor": null,
    "sort": "platform_default",
    "filtered": []
  },
  "platform": {
    "labels": {},
    "metricDefinitions": {},
    "specific": {}
  }
}
```

### 字段含义

- `contentItem`：当前 URL 对应的目标内容。`type` 是通用内容类型，`platformType` 是站点原生类型。
- `thread.items`：同一内容链路中的上下文内容，例如 X thread、引用链路或转发链路。普通评论不进入这里。
- `comments.items`：默认最多 20 条可见一级评论。每条评论只保留 `authorName`、`time`、`text`、`media`、`metrics`、`platformMetrics`，不展开评论下的二级讨论。
- `comments.filtered`：被 adapter 识别出的广告、推荐卡片、非评论内容等过滤摘要。垃圾机器人识别属于更高层策略，不在当前字段中自动判定。
- `media`：结构化媒体列表。`order` 表示媒体在该列表中的顺序；`placement` 表示相对正文的位置，如 `inline`、`after_text`、`cover`。当正文中的图片位置影响理解时，`text` 会保留 `[Image Local: ... | Remote: ...]` 占位符，因此 `text` 与 `media[]` 可以重复引用同一张图片。
- `metrics`：跨站点通用互动指标，只允许 `views/likes/comments/shares/reposts/quotes/favorites`。
- `platformMetrics`：平台特有指标，例如 B 站 `coins/danmaku`、Reddit `score/upvoteRatio`、知乎 `thanks`、X 公开书签数 `bookmarks`。
- `platform.labels`：保留平台原始叫法，例如 X 的 Bookmark、小红书的收藏、微博的转发。
- `platform.metricDefinitions`：当 `platformMetrics` 出现不易理解的字段时，提供字段释义。
- `platform.specific`：平台特有但不应晋升为通用字段的信息，例如知乎问题描述、Reddit community、视频是否已解析画面。

### 通用字段晋升规则

新增站点或新增指标时，默认先映射到现有通用字段。只有同时满足以下条件，才考虑新增通用字段：

1. 至少两个以上平台存在稳定同义行为。
2. 字段对读帖、排序、质量判断或后续动作有稳定价值。
3. 字段含义不会和现有 `metrics` 或 `platform.specific` 重叠。
4. 已在 `docs/interfaces.md` 记录含义，并在合同测试中固定。

不满足条件的字段进入 `platformMetrics` 或 `platform.specific`，并在必要时补 `platform.metricDefinitions`。

### raw 与 debug 边界

- 默认：返回 `semantic`，适合 AI Agent 和人类阅读。
- `--debug`：返回 `semantic` 加 `diagnostics`。`diagnostics` 只包含页面标题/URL、目标匹配、候选数量、过滤数量、缺失字段和 adapter 版本等摘要，不复制完整 `signals/rawPayload/debug`。
- `--raw`：返回完整 workflow raw payload，用于 adapter 调试、页面定位、字段排查和回归分析。

`targetId: null` 在 workflow 新开临时页并关闭后属于正常运行状态；默认语义输出不暴露该字段。

### 降级与失败

| 场景 | 返回方式 |
|------|----------|
| 页面打开失败、Bridge 无法访问、workflow 异常 | `ok=false`，保留结构化错误 envelope |
| adapter 未匹配站点或页面类型 | `ok=false`，错误码按现有 workflow 规则返回 |
| 登录拦截、验证码、地区限制导致核心正文不可读 | `ok=false`，不伪造空语义成功 |
| 核心正文可读但评论区不可见、未加载或登录态限制 | `semantic.ok=true`，`partial=true`，`missing=["comments"]` |
| 单个互动指标页面不可见 | 对应指标为 `null`，不默认标记 `partial` |
| adapter 明确报告指标区加载失败 | `partial=true`，`missing` 中加入对应指标分组 |

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
  - skill 常用可选：`--comment-limit N`，默认 20，范围 `0..100`；当前第一阶段只裁剪已采集的页面可见一级评论，站点 adapter 通常最多采集前 20 条，不承诺自动加载更多评论
  - 返回：
    - `semantic`：默认语义结果，结构见 `read_post.v1`
    - `diagnostics`：精简诊断摘要，供 `--debug` 使用
    - raw `content`：开发调试字段，包含 `post`、`threadItems`、`commentItems`、`filteredItems`、`rawPayload`
  - raw `content.primaryText/contextItems` 仅为兼容旧调试输出保留，默认 skill 不输出，也不作为 thread/comment 关系合同
  - 开发调试验证需显式使用本机 Bridge：`BRIDGE_URL="http://127.0.0.1:17777"`
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
  - 默认语义输出：`read_post.v1`；可用 `--raw` 查看 workflow raw payload，可用 `--debug` 查看语义结果和诊断摘要
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
  - 默认语义输出：`read_post.v1`；可用 `--raw` 查看 workflow raw payload，可用 `--debug` 查看语义结果和诊断摘要
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
  - 默认语义输出：`read_post.v1`
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

## 开发辅助与安全控制 API

| 端点 | 功能 |
|------|------|
| `POST /dev/reload-extension` | 开发期自动同步并热重载浏览器扩展 |
| `GET /dev/file/get` | 本地文件极速直拉端点，用于上传等大文件分片内存直注 |

### 本地大文件流式直拉接口 `/dev/file/get`

为了彻底停用 Edge/Chrome 调试横幅警告且不受 Native Messaging 1MB 通道大小限制，本系统设计了基于内容脚本直连 Local Daemon 的文件直拉机制：
- **CORS 预检**：支持 OPTIONS 预检，并接受 `X-Browser-Bridge-Tab-Id` 与 `X-Browser-Bridge-Session-Id` 自定义请求头。
- **安全检查**：
  1. 物理来源限制：仅支持 `127.0.0.1` / `localhost` 本地回环接口访问。
  2. 令牌强校验：每次上传下发，后端临时生成 30秒 TTL 的 fileId (Token)。
  3. 四维绑定：严格校验 Tab ID、Session ID、和预期页面 Origin。
  4. 极速消费：采用“先校验、后消费”的原子销毁机制，即将返回数据流时立即物理销毁 Token。

---

## 什么时候不该直接看这份文档

- 想判断“是代码问题还是宿主环境问题”：读 [development.md](development.md)
- 想知道当前每个站点到底支持什么：读 [capabilities.md](capabilities.md)
- 想扩一个新站点：读 [new-site-adaptation-guide.md](new-site-adaptation-guide.md)
