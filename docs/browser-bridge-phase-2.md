# Browser Bridge · Phase 2 执行指南（临时文档）

_Last updated: 2026-03-12_
_Status: active_

> 这是当前阶段的执行参考文档，主要给开发过程使用。
> 本阶段完成后，可删除或归档。

---

## 1. 本阶段目标

实现一个最小可用的 `browser-bridge` skeleton，满足：

- 本地 HTTP 服务常驻
- 能稳定连接宿主 Mac 上真实 Edge 的 CDP
- 内建 `host.orb.internal + Host header` 访问适配
- 提供最小 API：
  - `health`
  - `version`
  - `tabs`
  - `open`
  - `activate`
  - `page-info`（可选但建议做）
- 返回统一 JSON schema

### 明确不做
- 浏览器扩展
- Playwright attach
- 截图
- DOM 深操作
- 自动化复杂流程
- skill 封装

---

## 2. 目录结构建议

```text
browser-bridge-project/
  docs/
  bridge/
    bridge.py
    app/
      __init__.py
      config.py
      schemas.py
      server.py
      cdp_client.py
      cdp_service.py
      routes.py
```

### 模块职责

#### `bridge.py`
程序入口。

#### `app/config.py`
保存：
- bridge 监听 host/port
- CDP base URL
- CDP 强制 Host header
- timeout

#### `app/schemas.py`
统一响应 helper：
- `ok(action, data)`
- `fail(action, message)`

#### `app/server.py`
HTTP 服务初始化。

#### `app/cdp_client.py`
底层 CDP HTTP 访问层：
- 请求宿主机 `host.orb.internal:9333`
- 自动加 `Host: 127.0.0.1:9333`
- 统一处理 timeout / 错误 / JSON

#### `app/cdp_service.py`
浏览器能力封装：
- `get_version()`
- `list_tabs()`
- `open_url()`
- `activate_tab()`
- `get_page_info()`

#### `app/routes.py`
HTTP 路由定义。

---

## 3. 技术决策

### 3.1 语言
- Python

### 3.2 服务形态
- 本地 HTTP 服务，不做单次 CLI 作为主体

### 3.3 当前推荐框架
可选：
- Python 标准库（最轻）
- FastAPI + uvicorn（更利于长期扩展）

当前倾向：
- 如果能接受轻依赖，优先 **FastAPI**

### 3.4 当前固定配置

```python
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 17777

CDP_BASE_URL = "http://host.orb.internal:9333"
CDP_HOST_HEADER = "127.0.0.1:9333"
CDP_TIMEOUT_SECONDS = 10
```

当前阶段不急着环境变量化。

---

## 4. 统一响应结构

### 成功
```json
{
  "ok": true,
  "action": "tabs",
  "data": ...
}
```

### 失败
```json
{
  "ok": false,
  "action": "tabs",
  "message": "..."
}
```

要求：
- 所有 route 都统一
- 不要让底层 client 的异常直接裸奔到 HTTP 层

---

## 5. 最小 API 设计

### `GET /health`
作用：
- 检查 bridge 是否活着
- 检查是否能访问 Edge CDP

### `GET /version`
作用：
- 返回 `/json/version` 标准信息

### `GET /tabs`
作用：
- 列出现有 targets/tabs
- 先只关注 `type == page`

### `POST /open`
输入：
```json
{"url":"https://example.com"}
```
作用：
- 打开一个新页面/target

### `POST /activate`
输入：
```json
{"targetId":"..."}
```
作用：
- 激活指定 tab

### `GET /page-info`
输入：
- `targetId`（可选）
作用：
- 返回轻量 page info（title/url/type）

---

## 6. 实现顺序（严格按顺序）

### Step 1
创建目录、入口、配置、schema helper

### Step 2
实现 `cdp_client.py`
- 先只打通 `/json/version`

### Step 3
实现 `GET /health` 和 `GET /version`
- 证明 bridge 活了，且接上真实 Edge

### Step 4
实现 `list_tabs()` + `GET /tabs`

### Step 5
实现 `open_url()` + `POST /open`

### Step 6
实现 `activate_tab()` + `POST /activate`

### Step 7
实现轻量 `page-info`

### Step 8
执行 Phase 2 验收

---

## 7. 验收清单

### 必须通过
- [ ] bridge 能启动
- [ ] `GET /health` 正常
- [ ] `GET /version` 返回真实 Edge 信息
- [ ] `GET /tabs` 正常列出现有页面
- [ ] `POST /open` 能打开新页面
- [ ] `POST /activate` 能切换页面
- [ ] 返回结构统一
- [ ] Host header 适配逻辑已封装在 client 层

### 当前后置
- [ ] screenshot
- [ ] websocket 级 CDP 操作
- [ ] DOM 深抽取
- [ ] 浏览器扩展接入
- [ ] Playwright attach

---

## 8. 风险提醒

### 风险 1：`/json/new` 行为差异
不同 Chromium 版本的行为可能略有差异。
策略：先做朴素实现，不提前做大兼容层。

### 风险 2：target 类型复杂
`/json/list` 里可能包含 page / iframe / worker / extension。
策略：当前只关心 `page`。

### 风险 3：activate 不等价于绝对前台焦点
当前阶段先接受 CDP target activate 语义，不额外追求桌面级焦点控制。

---

## 9. 本阶段执行纪律

- 不要在 Phase 2 私自扩展到截图、DOM 深操作、扩展、Playwright
- 不要为了“更完整”提前把配置系统做复杂
- 不要把 Host header 适配散落到多个模块
- 不要把 demo 脚本误写成长期架构

当前目标只有一个：
**把最小 bridge skeleton 稳定接到真实 Edge 上。**
