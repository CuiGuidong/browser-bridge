# Browser Bridge API 与 Workflow 参考

_最后更新：2026-04-28_  
_状态：接口参考_

本文档聚焦：

- Bridge 暴露了哪些接口
- 当前 workflow 有哪些主要参数

如果你更关心“这个项目为什么这样分层”，先读：

- [architecture-spec.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/architecture-spec.md)

如果你更关心“真实环境里怎么调试和避坑”，再读：

- [implementation-guide.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/implementation-guide.md)

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

使用约定：

- 固定流程优先走 `/workflow/run`
- 站点语义能力优先接到 `/site/read` / `/site/action`
- `/query` / `/evaluate` 属于浏览器级工具接口，不是站点语义接口

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
  - 常用可选：`waitForReady`、`intervalSeconds`
- `list_bookmarks`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 常用可选：`mode`(`for_you|following`)、`targetCount`、`continuous`
- `follow_user` / `unfollow_user`
  - 必填：`handle`
- `add_bookmark` / `remove_bookmark`
  - 必填：`url`

### 小红书

- `read_post`
  - 必填：`url` 或 `noteId`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 常用可选：`waitForReady`、`intervalSeconds`
- `prepare_publish_post`
  - 必填：`title`、`content`、`imagePaths`
  - 常用可选：`waitForReady`、`intervalSeconds`

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
  - 常用可选：`targetCount`、`waitForReady`、`intervalSeconds`

## workflow 运行上的共同约定

- 默认允许新开临时标签页
- 浏览器页签总数达到上限时，会优先复用同站点标签页
- workflow 结束后会关闭“本次新开”的临时标签页
- 如果 workflow 返回的 `targetId` 为 `null`，通常表示临时页已在 workflow 内关闭
- 如果传入 `targetId`，表示“指定执行容器”，不表示保持当前页原样不动

## 什么时候不该直接看这份文档

- 想判断“是代码问题还是宿主环境问题”：读 [implementation-guide.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/implementation-guide.md)
- 想知道当前每个站点到底支持什么：读 [site-support.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/site-support.md)
- 想扩一个新站点：读 [new-site-adaptation-guide.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/new-site-adaptation-guide.md)
