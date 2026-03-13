# Browser Bridge 开发日志

_Last updated: 2026-03-13_
_Status: active_

> 记录开发期间的关键变更、安装、决策、阶段结果，供快速查看。

## 2026-03-12 / 2026-03-13

### 已确认环境事实
- 宿主 Mac 上真实 Edge 已可通过 `--remote-debugging-port=9333` 启动 CDP。
- OrbStack/OpenClaw 环境可通过 `host.orb.internal` 访问宿主 Mac。
- 访问宿主机 Edge CDP 需要显式使用 `Host: 127.0.0.1:9333` header。
- NAS 上的 `kasmweb edge` 路线也已具备基础可达性，但当前开发测试主线仍坚持宿主 Mac 上真实 Edge。

### 已完成开发
- 建立 `projects/browser-bridge-project/bridge/` Python skeleton。
- 已实现：
  - `bridge.py`
  - `app/config.py`
  - `app/schemas.py`
  - `app/cdp_client.py`
  - `app/cdp_ws_client.py`
  - `app/cdp_service.py`
  - `app/routes.py`
  - `app/server.py`
- 已跑通接口：
  - `GET /health`
  - `GET /version`
  - `GET /tabs`
  - `POST /open`
  - `POST /activate`
  - `GET /wait`
  - `GET /page-info`
  - `GET /page-content`
  - `POST /screenshot`
  - `GET /query`
  - `POST /click`
  - `POST /fill`

### 关键实现说明
- `open` 的初版失败原因已定位：当前 Edge `/json/new` 只接受 `PUT`，不接受 `GET/POST`。
- 已修正 `cdp_client.py`，支持自定义 HTTP method，并将 `open_url()` 改为 `PUT /json/new?...`。
- 已引入 websocket 级 CDP 客户端，用于：
  - `Runtime.evaluate`
  - `Page.captureScreenshot`
- 已进一步实现基础页面操作接口：
  - `query`：按 CSS selector 读取元素摘要
  - `click`：按 CSS selector 执行点击
  - `fill`：按 CSS selector 填充文本并派发 input/change 事件
  - `wait`：轮询 title/url 稳定性，提供最小页面稳定等待能力
- 已为 `click` 增加 `waitAfter` 参数，用于在点击后等待页面状态稳定，减少单步操作的脆弱性。

### 安装/依赖变更
- 系统 Python 受 PEP 668 保护，未直接修改系统环境。
- 已在项目目录 `projects/browser-bridge-project/bridge/.venv/` 创建 Python 虚拟环境。
- 已在该虚拟环境内安装依赖：`websockets`
- 原因：当前环境需要通过 CDP websocket 执行 `Runtime.evaluate`、`Page.captureScreenshot` 等方法；标准库不提供合适 websocket 客户端。

### 当前判断
- bridge 已具备：浏览器连接、tab 管理、页面观察、基础元素查询、基础点击与填充、基础等待能力。
- 下一步可进入更稳的页面交互能力阶段（更强的元素定位、输入后状态校验、导航与内容变化联动判断），或开始为 Playwright attach 预埋结构。
- 已新增“心跳自检”工作约定：在连续开发窗口中，按约每 5 分钟自查一次是否仍在推进 browser bridge 主线、是否卡住、是否需要写入 dev-log/open-items，而不是长时间空转。
