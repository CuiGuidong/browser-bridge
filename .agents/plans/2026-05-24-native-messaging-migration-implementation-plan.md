# Native Messaging Host 迁移实施计划

> **给执行 Agent：** 按任务逐项执行，保持改动聚焦，运行列出的验证。只有当完成的项目变更达到可独立解释、可独立回滚的边界时，才调用 `finalize-change`。除非用户明确要求，计划产物保持未暂存。所有任务在独立分支 `feature/native-messaging` 上执行。

**实现偏差记录（阶段 1 完成后）：**
- shim 从 WebSocket 方案改为 HTTP long-poll（宿主机无 websockets 库且无 pip），新增 `/native/session/register`、`/native/session/pull`、`/native/session/result` 三个 HTTP 端点
- shim 使用 `select.select()` 轮询 stdin 而非阻塞 `read()`，解决浏览器启动 shim 后 stdin EOF 导致立即退出的问题
- NativeSessionManager 从 WebSocket handler 改为 HTTP long-poll + 命令队列模式
- session 清理：注册新 session 时自动清理 60 秒未 pull 的僵尸 session

**目标：** 去掉 `--remote-debugging-port=9333` 启动要求，将浏览器控制从 CDP 直连迁移到扩展侧 `chrome.debugger` + Native Messaging 通道

**计划密度：** Detailed low-context

**实现思路：** Bridge daemon 保持为长期 HTTP 服务（:17777），新增 Native Host shim 作为浏览器启动的子进程通过 stdin/stdout 与扩展通信、通过 WebSocket 与 daemon 通信。扩展侧用 `chrome.tabs` 管理标签页、`chrome.debugger` 发送 CDP 命令。分 5 阶段渐进迁移，阶段 1-3 保留 CDP 直连和 HTTP 轮询作为对照。

**技术栈：** Python 3.10+、FastAPI、websockets、Chrome Extension Manifest V3、chrome.debugger API、Native Messaging API

**输入：** `.agents/specs/2026-05-24-native-messaging-migration-design-spec.md`

## 验收到验证矩阵

| 验收项 | 验证类型 | 证据目标 |
| --- | --- | --- |
| Native Messaging ping 往返 | 集成测试 | shim → daemon → 扩展 → daemon → shim 完整链路，延迟 < 3s |
| tabs.list 返回真实标签页 | 集成测试 | 结果包含浏览器中实际打开的 tab，tab 结构含 id/nativeTabId/title/url |
| 15 个 CDP 操作全部通过 native 通道 | 手动对比 | BROWSER_RUNTIME=native_only 下逐个操作验证，结果与 CDP 直连一致 |
| 微博 read_post 基线 | 端到端 | `python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'` 返回 ok:true |
| X read_post + search | 端到端 | X skill 脚本正常返回结构化数据 |
| 小红书 prepare_publish_post 文件上传 | 端到端 | 图片上传成功，停在发布按钮前 |
| 知乎 read_post + read_hot | 端到端 | 知乎 skill 脚本正常返回结构化数据 |
| 语义命令走 Native Messaging | 集成测试 | native_only 模式下 read/act/verify 正常工作 |
| page-state report 走 native | 集成测试 | /extension/state 的 lastReport 不为 null |
| CDP 直连代码已删除 | 代码审查 | cdp_client.py、cdp_ws_client.py、cdp_service.py 不存在 |
| HTTP 轮询端点已删除 | 代码审查 | /extension/pull、/extension/result 返回 404 |
| 文档已更新 | 文档检查 | README.md、docs/development.md、docs/operations.md 无 --remote-debugging-port 要求 |

---

## 阶段 1：基础设施 + ping 验证

### Task 1.1：建立分支和 Native Messaging 协议层

**Purpose：** 实现 length-prefixed JSON 编解码，这是 Native Messaging 的基础协议

**Files：**
- Create: `bridge/app/native_messaging.py`

**Steps：**
- [x] 创建分支：`git checkout -b feature/native-messaging`
- [x] 创建 `bridge/app/native_messaging.py`，实现两个函数：
  - `read_message(stream)` — 从二进制流读 4 字节 little-endian uint32 长度，再读对应长度的 UTF-8 JSON，返回 dict；流结束返回 None
  - `write_message(stream, msg)` — 将 dict 序列化为 JSON，写 4 字节长度前缀 + UTF-8 payload，flush
- [x] 编译检查：`env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/native_messaging.py`

**Acceptance：** 两个函数可独立导入，read_message/write_message 往返一致
**Verification：** 交互式 Python 验证：`import io; from bridge.app.native_messaging import read_message, write_message; buf = io.BytesIO(); write_message(buf, {"test": 1}); buf.seek(0); assert read_message(buf) == {"test": 1}`

### Task 1.2：实现 Native Session Manager

**Purpose：** Bridge daemon 侧的 WebSocket server，管理扩展 session，路由命令和结果

**Files：**
- Create: `bridge/app/native_session_manager.py`
- Modify: `bridge/app/server.py`

**Steps：**
- [x] 创建 `bridge/app/native_session_manager.py`，实现 `NativeSessionManager` 类：
  - `__init__()` — 初始化 `_sessions` dict（sessionId → WebSocket）、`_pending_results` dict（commandId → asyncio.Future）、`_report_cache` dict（sessionId → lastReport）
  - `async handle_connection(ws)` — WebSocket 连接处理器：分配 sessionId，注册 session，循环接收消息（结果/报告），清理 session on disconnect
  - `async send_command(session_id, method, params, timeout_seconds=30)` — 向指定 session 发命令，等待结果或超时，返回 result dict 或 error dict
  - `get_active_session()` — 返回第一个活跃 session 的 sessionId，无则返回 None
  - `get_report(session_id)` — 获取 session 的最新报告
- [x] 在 `server.py` 中注入 NativeSessionManager：
  - 新增 `native_session_manager = NativeSessionManager()` 全局实例
  - 新增 WebSocket endpoint `@app.websocket("/native/ws")` 调用 `native_session_manager.handle_connection(ws)`
  - 需要 `from fastapi import WebSocket` 和 `import json`
- [x] 编译检查：`env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/native_session_manager.py bridge/app/server.py`

**Acceptance：** WebSocket endpoint `/native/ws` 可接受连接，session 注册和命令收发正常
**Verification：** 重启 bridge，用 Python websockets 客户端连接 `ws://127.0.0.1:17777/native/ws`，发送 `{"id":"t1","result":{"test":1}}` 不报错

### Task 1.3：实现 Native Host Shim

**Purpose：** 浏览器启动的子进程，桥接扩展 stdin/stdout 与 bridge daemon WebSocket

**Files：**
- Create: `bridge/app/native_host_shim.py`

**Steps：**
- [x] 创建 `bridge/app/native_host_shim.py`，使用单 event loop + asyncio.to_thread 模型（避免跨线程/loop 使用 WebSocket 对象）：
  ```python
  #!/usr/bin/env python3
  """Native Messaging host shim for Browser Bridge."""
  import struct, sys, json, asyncio, queue
  import websockets

  BRIDGE_WS_URL = "ws://127.0.0.1:17777/native/ws"

  def read_native_message():
      raw_length = sys.stdin.buffer.read(4)
      if not raw_length or len(raw_length) < 4:
          return None
      length = struct.unpack('<I', raw_length)[0]
      data = sys.stdin.buffer.read(length)
      return json.loads(data) if data else None

  def write_native_message(msg):
      encoded = json.dumps(msg, ensure_ascii=False).encode('utf-8')
      sys.stdout.buffer.write(struct.pack('<I', len(encoded)))
      sys.stdout.buffer.write(encoded)
      sys.stdout.buffer.flush()

  async def run():
      stdin_queue = queue.Queue()
      async with websockets.connect(BRIDGE_WS_URL) as ws:
          # stdin → queue → ws（在独立线程中读 stdin）
          def stdin_reader():
              while True:
                  msg = read_native_message()
                  if msg is None:
                      stdin_queue.put(None)
                      break
                  stdin_queue.put(msg)

          import threading
          threading.Thread(target=stdin_reader, daemon=True).start()

          async def forward_stdin_to_ws():
              while True:
                  msg = await asyncio.to_thread(stdin_queue.get)
                  if msg is None:
                      await ws.close()
                      break
                  await ws.send(json.dumps(msg, ensure_ascii=False))

          async def forward_ws_to_stdout():
              async for data in ws:
                  msg = json.loads(data)
                  write_native_message(msg)

          await asyncio.gather(forward_stdin_to_ws(), forward_ws_to_stdout())

  if __name__ == '__main__':
      asyncio.run(run())
  ```
- [x] 确保文件可执行：`chmod +x bridge/app/native_host_shim.py`
- [x] 编译检查：`env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/native_host_shim.py`

**Acceptance：** shim 可独立启动，连接到 bridge daemon 的 WebSocket，stdin→ws 和 ws→stdout 双向转发正常
**Verification：** 启动 bridge daemon，运行 `echo '{"id":"t1","method":"ping","params":{}}' | python3 bridge/app/native_host_shim.py`（需要先 mock stdin 为 length-prefixed 格式，或用集成测试验证）

### Task 1.4：安装 Native Host Manifest

**Purpose：** 在系统中注册 native host，使浏览器扩展的 connectNative 能找到 shim

**Files：**
- Create: `native-messaging/com.cuiguidong.browserbridge.json`
- Create: `scripts/install-native-host.sh`

**Steps：**
- [x] 创建 `native-messaging/` 目录
- [x] 创建 `native-messaging/com.cuiguidong.browserbridge.json`：
  ```json
  {
    "name": "com.cuiguidong.browserbridge",
    "description": "Browser Bridge native messaging host",
    "type": "stdio",
    "path": "<ABSOLUTE_PATH_TO_SHIM>",
    "allowed_origins": [
      "chrome-extension://<EXTENSION_ID>/"
    ]
  }
  ```
  `<ABSOLUTE_PATH_TO_SHIM>` 和 `<EXTENSION_ID>` 由安装脚本动态填入。
- [x] 创建 `scripts/install-native-host.sh`：
  - 检测操作系统（Linux / macOS）
  - 检测浏览器（Chrome / Edge）
  - 从 `extension/manifest.json` 提取扩展 ID（或要求用户传入）
  - 计算 shim 绝对路径（`<project_root>/bridge/app/native_host_shim.py`）
  - 模板替换 JSON 中的占位符
  - 复制到对应浏览器的 `NativeMessagingHosts/` 目录
  - macOS 路径：`~/Library/Application Support/Google/Chrome/NativeMessagingHosts/` 和 `~/Library/Application Support/Microsoft Edge/NativeMessagingHosts/`
  - Linux 路径：`~/.config/google-chrome/NativeMessagingHosts/` 和 `~/.config/microsoft-edge/NativeMessagingHosts/`
- [x] 在本地 Edge 上执行安装脚本

**Acceptance：** manifest 文件存在于对应浏览器的 NativeMessagingHosts 目录，path 指向正确的 shim 脚本，allowed_origins 包含正确的扩展 ID
**Verification：** `cat ~/.config/microsoft-edge/NativeMessagingHosts/com.cuiguidong.browserbridge.json` 确认内容正确

### Task 1.5：扩展侧 Native Messaging 连接

**Purpose：** 扩展 background.js 新增 Native Messaging 连接和 ping 命令分发

**Files：**
- Modify: `extension/manifest.json`
- Modify: `extension/background.js`

**Steps：**
- [x] 在 `manifest.json` 的 `permissions` 数组中添加 `"debugger"` 和 `"nativeMessaging"`
- [x] 在 `background.js` 顶部新增 Native Messaging 连接代码（**保留现有 HTTP 轮询逻辑不动**）：
  ```javascript
  // Native Messaging 连接（与 HTTP 轮询并行）
  let nativePort = null;

  function connectNative() {
    try {
      nativePort = chrome.runtime.connectNative('com.cuiguidong.browserbridge');
      nativePort.onMessage.addListener(handleNativeCommand);
      nativePort.onDisconnect.addListener(() => {
        console.warn('[Browser Bridge] Native disconnected:', chrome.runtime.lastError?.message);
        nativePort = null;
      });
    } catch (e) {
      console.warn('[Browser Bridge] connectNative failed:', e.message);
    }
  }

  connectNative();

  // keepalive 防 Service Worker 挂起
  chrome.alarms.create('bb-keepalive', { periodInMinutes: 0.4 });
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'bb-keepalive' && !nativePort) {
      connectNative();
    }
  });

  function normalizeTab(tab) {
    return { id: String(tab.id), nativeTabId: tab.id, title: tab.title || '', url: tab.url || '', type: 'page' };
  }

  async function handleNativeCommand(msg) {
    const { id, method, params } = msg;
    try {
      let result;
      if (method === 'ping') {
        result = { alive: true, timestamp: Date.now() };
      } else if (method === 'tabs.list') {
        const tabs = await chrome.tabs.query({});
        result = { tabs: tabs.map(normalizeTab) };
      } else {
        result = { error: 'unknown method' };
      }
      nativePort.postMessage({ id, result });
    } catch (error) {
      nativePort.postMessage({ id, error: { code: 'unknown', message: error.message } });
    }
  }
  ```
- [x] 同步扩展到宿主机：`cp extension/manifest.json extension/background.js /Users/cuiguidong/workspace/personal/projects/browser-bridge-project/extension/`
- [x] 在 `edge://extensions` 中重载扩展

**Acceptance：** 扩展启动后自动连接 native host，background.js console 无报错
**Verification：** 在 edge://extensions 的 Service Worker 控制台中无 `[Browser Bridge] connectNative failed` 错误

### Task 1.6：ping 端到端验证

**Purpose：** 验证完整的 Native Messaging 链路：bridge daemon → WebSocket → shim → stdin/stdout → 扩展 → 回来

**Files：**
- Modify: `bridge/app/server.py`（新增调试 endpoint）

**Steps：**
- [x] 确保 bridge daemon 已重启（包含 /native/ws endpoint）
- [x] 确保 native host manifest 已安装
- [x] 确保扩展已重载且 connectNative 成功（edge://extensions 的 Service Worker 控制台无 `connectNative failed` 错误）
- [x] 在 `server.py` 新增两个调试 endpoint（仅用于开发调试，阶段 5 清理时移除）：
  - `POST /native/debug/ping` — 调用 `native_session_manager.send_command(active_session, "ping", {})`
  - `POST /native/debug/tabs` — 调用 `native_session_manager.send_command(active_session, "tabs.list", {})`
- [x] 通过 curl 触发 daemon 向真实扩展发 ping：
  ```bash
  curl --noproxy '*' -sS -X POST http://127.0.0.1:17777/native/debug/ping
  ```
  预期返回：`{"ok": true, "data": {"alive": true, "timestamp": ...}}`
- [x] 通过 curl 触发 tabs.list：
  ```bash
  curl --noproxy '*' -sS -X POST http://127.0.0.1:17777/native/debug/tabs
  ```
  预期返回：包含浏览器实际打开 tab 的列表

**Acceptance：** daemon 通过 native session 向真实扩展发 ping 收到 `{alive: true}`，tabs.list 返回真实标签页
**Verification：** curl 返回 ok:true，tabs.list 结果包含至少 1 个 tab 对象且含 id/nativeTabId/title/url 字段

---

## 阶段 2：浏览器级操作迁移

### Task 2.1：实现 NativeBrowserRuntime

**Purpose：** 实现与 CdpRuntime 相同接口的 15 个方法，通过 Native Session Manager 调用扩展

**Files：**
- Create: `bridge/app/native_browser_runtime.py`

**Steps：**
- [x] 创建 `NativeBrowserRuntime` 类，构造函数接收 `NativeSessionManager` 实例
- [x] 实现 15 个方法，每个方法通过 `session_manager.send_command()` 调用扩展：
  - `get_version()` → 返回固定的 `{browser: "native", protocolVersion: "1.3"}`
  - `list_tabs()` → `tabs.list`
  - `open_or_reuse_url(url, ...)` → 先 `tabs.list` 查找可复用 tab，有则 `tabs.activate` + `debugger.send` Page.navigate，无则 `tabs.create`
  - `activate_tab(target_id)` → `tabs.activate`
  - `navigate_tab(target_id, url)` → `debugger.send` Page.navigate
  - `reload_tab(target_id)` → `debugger.send` Page.reload
  - `close_tab(target_id)` → `tabs.close`
  - `wait_for_page(target_id, ...)` → 轮询 `tabs.list` 检查 URL/标题变化
  - `get_page_info(target_id)` → `tabs.list` 后过滤目标 tab
  - `get_page_content(target_id, max_chars)` → `debugger.send` Runtime.evaluate（使用现有 JS 表达式）
  - `probe_page_readiness(target_id, ...)` → `debugger.send` Runtime.evaluate（使用现有探针 JS）
  - `capture_screenshot(target_id, fmt)` → `debugger.send` Page.enable + Page.captureScreenshot
  - `query_elements(selector, target_id, limit)` → `debugger.send` Runtime.evaluate（使用现有查询 JS）
  - `execute_js(expression, target_id)` → `debugger.send` Runtime.evaluate
  - `set_file_input_files_by_selector(target_id, selector, files)` → `debugger.send` 多步 CDP 命令链（Page.enable → DOM.enable → DOM.getDocument → DOM.querySelector → DOM.setFileInputFiles → DOM.resolveNode → Runtime.callFunctionOn）
- [x] 实现统一 helper `_resolve_native_tab_id(target_id=None)`：
  - `target_id` 为 None → 调用 `tabs.list`，返回第一个 `type === "page"` 的 tab 的 nativeTabId
  - `target_id` 为数字字符串 → 返回 `int(target_id)`
  - `target_id` 为非数字字符串 → 返回 `None`（调用方应报 `tab_not_found`）
  - 所有 15 个方法通过此 helper 解析 target_id，不直接 `int()` 转换
- [x] 编译检查：`env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/native_browser_runtime.py`

**Acceptance：** 15 个方法全部实现，方法签名与 CdpRuntime 一致
**Verification：** `python3 -c "from bridge.app.native_browser_runtime import NativeBrowserRuntime; print('OK')"` 不报错

### Task 2.2：扩展侧 tabs 和 debugger 命令分发

**Purpose：** 扩展 background.js 支持全部 tabs.* 和 debugger.* 方法

**Files：**
- Modify: `extension/background.js`

**Steps：**
- [x] 在 `handleNativeCommand` 中添加完整命令分发（替换 Task 1.5 的 placeholder）：
  - `tabs.list` → `chrome.tabs.query({})`
  - `tabs.create` → `chrome.tabs.create({url, active})`
  - `tabs.activate` → `chrome.tabs.update(tabId, {active: true})`
  - `tabs.close` → `chrome.tabs.remove(tabId)`
  - `debugger.attach` → `ensureDebuggerAttached(tabId)`
  - `debugger.send` → `ensureDebuggerAttached(tabId)` + `chrome.debugger.sendCommand({tabId}, command, params_)`
  - `debugger.detach` → `chrome.debugger.detach({tabId})`
  - `semantic.invoke` → 暂返回 `{error: "not implemented in phase 2"}`
- [x] 添加 `ensureDebuggerAttached(tabId)` 函数（含 attachedTabs cache 和错误分类）
- [x] 添加 `handleDebuggerCommand(method, params)` 函数
- [x] 添加 `chrome.tabs.onRemoved` 监听器清理 attach cache
- [x] 同步到宿主机并重载扩展

**Acceptance：** 所有 tabs 和 debugger 命令通过 Native Messaging 正常执行
**Verification：** 通过 Task 1.6 的 debug endpoint 依次测试，确保命令走 daemon → active native session → shim → extension 真实链路：`/native/debug/tabs`（list）、通过 `NativeBrowserRuntime` 的 Python 调用或新增 debug endpoint 测试 `tabs.create`（打开 about:blank）、`tabs.activate`、`debugger.attach`、`debugger.send`（Runtime.evaluate 返回 document.title）、`debugger.detach`、`tabs.close`

### Task 2.3：BROWSER_RUNTIME 配置和路由切换

**Purpose：** 使 CdpRuntime 根据配置选择 native 或 CDP 后端

**Files：**
- Modify: `bridge/app/config.py`
- Modify: `bridge/app/browser/cdp_runtime.py`
- Modify: `bridge/app/server.py`

**Steps：**
- [x] 在 `config.py` 新增：
  ```python
  BROWSER_RUNTIME = os.getenv("BROWSER_RUNTIME", "auto")  # auto | native_only | cdp_only
  ```
- [x] 在 `cdp_runtime.py` 的 `CdpRuntime` 类中：
  - 构造函数接收 `native_session_manager` 参数（可选）
  - 每个方法根据 `BROWSER_RUNTIME` 决定路由：
    - `cdp_only` → 始终用现有 CDP 实现
    - `native_only` → 始终用 NativeBrowserRuntime，无活跃 session 时抛错
    - `auto`（默认） → 优先 native（有活跃 session 时），否则 CDP
  - 提取内部方法 `_use_native()` 判断当前是否应走 native 通道
- [x] 在 `server.py` 中，将 `native_session_manager` 注入到 `CdpRuntime` 构造函数
- [x] 编译检查

**Acceptance：** `BROWSER_RUNTIME=native_only` 且未开 --remote-debugging-port 时，浏览器操作走 native 通道
**Verification：** 通过 systemd drop-in 或 `.env.local` 设置 `BROWSER_RUNTIME=native_only`，确认浏览器未开 --remote-debugging-port，重启 bridge daemon 后 `curl --noproxy '*' -sS http://127.0.0.1:17777/tabs` 通过 native 通道返回标签页列表。如果返回 CDP 错误而非 native 结果，说明配置未生效。

### Task 2.4：逐操作验证（native_only 模式）

**Purpose：** 在 native_only 且无 CDP 端口下，逐个验证 15 个操作

**Files：** 无新增文件

**Steps：**
- [x] 确认浏览器**未**开 `--remote-debugging-port`，正常启动 Edge
- [x] 通过 systemd drop-in 或 `.env.local` 设置 `BROWSER_RUNTIME=native_only`，重启 bridge daemon：
  ```bash
  sudo systemctl restart browser-bridge.service
  curl --noproxy '*' -sS http://127.0.0.1:17777/health
  ```
- [x] 逐个验证（通过 curl 或 Python 脚本）：
  - `/health` → 返回 bridge alive（CDP 状态可能为 disconnected，但 native 可用）
  - `/tabs` → 返回真实标签页列表
  - `open_url` → 创建新标签页
  - `activate_tab` → 切换标签页
  - `navigate_tab` → 导航到新 URL
  - `reload_tab` → 刷新标签页
  - `close_tab` → 关闭标签页
  - `get_page_info` → 返回页面元信息
  - `execute_js` → `document.title` 返回正确标题
  - `capture_screenshot` → 返回 base64 PNG 数据
  - `get_page_content` → 返回页面文本内容
  - `query_elements` → 返回 DOM 元素列表
  - `probe_page_readiness` → 返回 ready 状态
  - `set_file_input_files_by_selector` → 需要创建测试 HTML 页面验证（或在阶段 3 的小红书发帖中验证）
- [x] 记录每个操作的结果和耗时

**Acceptance：** 14/15 操作通过（set_file_input_files 可推迟到阶段 3）
**Verification：** 每个操作返回 ok:true 或有效数据，无 timeout 错误

---

## 阶段 3：核心 workflow 回归

### Task 3.1：微博 read_post 基线

**Purpose：** 验证 native 通道下最基础的 workflow

**Files：** 无

**Steps：**
- [x] 确保 `BROWSER_RUNTIME=native_only`，浏览器未开 --remote-debugging-port
- [x] 运行：`python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'`
- [x] 检查返回 ok:true，包含 author/text/images 字段

**Acceptance：** 返回 ok:true，author 和 text 不为空
**Verification：** 输出 JSON 包含 `"ok": true` 和非空 `"text"` 字段

### Task 3.2：X read_post + search

**Purpose：** 验证 X 站点的读取和搜索 workflow

**Files：** 无

**Steps：**
- [x] 运行：`python3 skills/x-assistant/scripts/read_post.py 'https://x.com/billtheinvestor/status/2038173185875775987'`
- [x] 运行：`python3 skills/x-assistant/scripts/search.py "AI agent"`
- [x] 检查两个结果都返回 ok:true

**Acceptance：** read_post 返回推文内容，search 返回搜索结果列表
**Verification：** 两个 JSON 输出都包含 `"ok": true`

### Task 3.3：小红书 read_post + prepare_publish_post（文件上传重点）

**Purpose：** 验证小红书读取和文件上传能力，文件上传是 chrome.debugger 的关键差异点

**Files：** 无

**Steps：**
- [x] 运行：`python3 skills/xiaohongshu-assistant/scripts/read_post.py 'https://www.xiaohongshu.com/explore/69c6469e000000001d01d9d1'`
- [x] 检查返回 ok:true
- [x] 测试文件上传（prepare_publish_post）：
  - 准备一张测试图片路径
  - 通过 workflow API 调用 prepare_publish_post
  - 验证图片上传成功，页面停在发布按钮前
  - **重点检查**：`DOM.setFileInputFiles` 通过 chrome.debugger 是否正常工作
- [x] 如果文件上传失败，检查 chrome.debugger 对 DOM 命令的支持情况

**Acceptance：** read_post 正常返回，文件上传成功（或明确记录 chrome.debugger 的限制）
**Verification：** read_post JSON 包含 `"ok": true`；prepare_publish_post 流程完成到发布按钮前

### Task 3.4：知乎 read_post + read_hot

**Purpose：** 验证知乎站点的读取和热榜 workflow

**Files：** 无

**Steps：**
- [x] 运行：`python3 skills/zhihu-assistant/scripts/read_post.py 'https://zhuanlan.zhihu.com/p/1899044076168394425'`
- [x] 运行：`python3 skills/zhihu-assistant/scripts/read_hot.py`
- [x] 检查两个结果都返回 ok:true

**Acceptance：** read_post 返回文章正文，read_hot 返回热榜列表
**Verification：** 两个 JSON 输出都包含 `"ok": true`，read_post 的 text 字段不为 null

---

## 阶段 4：语义通道迁移

### Task 4.1：ExtensionRuntime 语义命令迁移到 Native Messaging

**Purpose：** 将 read/act/verify/capabilities/probe_ready 从 HTTP pull/result 切到 Native Messaging

**Files：**
- Modify: `bridge/app/extension/extension_runtime.py`（注入 native_session_manager，扩展 invoke 签名）
- Modify: `bridge/app/server.py`（注入 native_session_manager 到 ExtensionRuntime）
- Modify: `bridge/app/application/read_service.py`（传递 target_id/site 给 invoke）
- Modify: `bridge/app/application/action_service.py`（传递 target_id/site 给 invoke）
- Modify: `extension/background.js`（semantic.invoke 分发）

**Steps：**
- [x] 修改 `ExtensionRuntime.__init__()` 接收 `native_session_manager=None` 和 `site_registry=None` 参数并存储
- [x] 扩展 `invoke()` 签名为 `invoke(method, params, timeout_seconds=30, target_url=None, target_id=None, site=None)`
- [x] 在 `_resolve_semantic_tab_id()` 的第 3 优先级（无 target_id 无 target_url）中，通过 `self._site_registry.get(site).hosts` 获取站点 hosts 列表，用于过滤匹配站点 tab
- [x] 在 `server.py` 中将 `native_session_manager` 和 `site_registry` 注入到 `ExtensionRuntime` 构造函数
- [x] 在 `extension_runtime.py` 中新增 `_resolve_semantic_tab_id(target_id=None, target_url=None, site=None)` 方法：
  - 调用 `native_session_manager.send_command(active_session, "tabs.list", {})` 获取全部 tab
  - 按 spec §3.5 优先级匹配：
    1. `target_id` 非空 → 在 tab 列表中找 `nativeTabId == int(target_id)` 的 tab
    2. `target_url` 非空 → 规范化后 exact URL 匹配（复用 `find_hint_with_debug` 中的 URL 规范化规则：保留 query，仅白名单忽略 tracking 参数，X 额外支持 status_id 匹配）
    3. 都无 → 找最近活跃的匹配站点 tab（按 site config 的 hosts 过滤）
  - 返回 `nativeTabId` 整数，找不到返回 None
- [x] 在 `invoke()` 中：如果有活跃 native session，调用 `_resolve_semantic_tab_id(target_id, target_url, site)` 解析 tabId，解析失败返回 `{ok: false, error: "tab_not_found"}`，不发命令给扩展；解析成功通过 `native_session_manager.send_command()` 发送 `{method, params, tabId: <整数>}`
- [x] 在 `server.py` 中将 `native_session_manager` 注入到 `ExtensionRuntime` 构造函数
- [x] 更新 `read_service.py` 和 `action_service.py` 中所有 `extension_runtime.invoke()` 调用，传入 `target_id` 和 `site` 参数（从 workflow 传入的上下文中获取）
- [x] 在 `background.js` 的 `handleNativeCommand` 中实现 `semantic.invoke`：
  - 从 params 中取 `tabId`（daemon 侧已解析好的整数）
  - 如果缺少 tabId，直接返回 `{error: {code: "missing_tab_id", message: "..."}}`
  - **不做任何 URL 匹配**——扩展侧只接收已解析的 tabId
  - 通过 `chrome.tabs.sendMessage(tabId, {action: 'bridgeRpc', payload: {method: params.method, params: params.params, commandId: msg.id}})` 转发给 content script（复用现有 `handleBridgeRpc()` 处理逻辑）
  - 等待 content script 的响应（sendMessage 回调）
- [x] 验证语义命令通过 native 通道工作

**Acceptance：** `BROWSER_RUNTIME=native_only` 下，site/read 正常返回语义数据
**Verification：** `curl --noproxy '*' -sS 'http://127.0.0.1:17777/site/read' -H 'Content-Type: application/json' -d '{"site":"zhihu","kind":"read_post","params":{"url":"https://zhuanlan.zhihu.com/p/1899044076168394425"}}'` 返回 ok:true

### Task 4.2：page-state report 迁移到 Native Messaging

**Purpose：** content script 的页面状态报告从 HTTP POST 迁到 native report 消息

**Files：**
- Modify: `extension/background.js`
- Modify: `extension/content.js`（如果 reportSnapshot 在 content.js 中）

**Steps：**
- [x] content.js 的 `reportSnapshot()` 不改动——它仍通过 `chrome.runtime.sendMessage({action: 'extensionSnapshot', payload})` 发给 background.js
- [x] background.js 的 `postReport(payload)` 函数改为：
  - 优先通过 `nativePort.postMessage({type: "report", payload})` 发送（native 通道）
  - `nativePort` 不可用时回退到 HTTP POST `/extension/report`
- [x] 在 NativeSessionManager 中处理 report 消息：
  - 收到 `{type: "report", payload: {...}}` 时存入 `_report_cache`
  - 暴露 `get_report(session_id)` 方法供 ExtensionRuntime 查询
- [x] 在 ExtensionRuntime 中：
  - `get_hint()` 和 `get_state()` 优先查询 native report 缓存
  - 无 native session 时回退到现有 HTTP report 缓存

**Acceptance：** `BROWSER_RUNTIME=native_only` 下，`/extension/state` 返回的 lastReport 不为 null
**Verification：** 打开一个知乎页面，等待 3 秒，`curl --noproxy '*' -sS http://127.0.0.1:17777/extension/state` 返回 lastReport 不为 null 且时间戳新鲜

### Task 4.3：全量 workflow 回归（native_only 语义通道）

**Purpose：** 确认语义通道迁移后所有 workflow 仍然正常

**Files：** 无

**Steps：**
- [x] 在 `BROWSER_RUNTIME=native_only` 下重跑 Task 3.1-3.4 的全部验证
- [x] 额外测试 X 的 follow_user / bookmark 动作（如方便的话）

**Acceptance：** 全部核心 workflow 通过
**Verification：** 同阶段 3

---

## 阶段 5：清理

### Task 5.1：删除 CDP 直连代码

**Purpose：** 移除不再需要的 CDP 直连层

**注意：** `server.py` 中的 Playwright 路由（`/playwright/connect`、`/playwright/click` 等，约 line 730+）也通过 CDP WebSocket 连接浏览器。这些路由不在本次迁移范围内——它们是 Path C（复杂页面操作）的独立通道。本次只删除 `cdp_client.py`、`cdp_ws_client.py`、`cdp_service.py` 和 `cdp_runtime.py` 中的 CDP 分支。Playwright 路由的迁移或移除作为后续独立任务处理。

**Files：**
- Delete: `bridge/app/cdp_client.py`
- Delete: `bridge/app/cdp_ws_client.py`
- Delete: `bridge/app/cdp_service.py`
- Modify: `bridge/app/config.py`（移除 CDP_* 配置，保留 Playwright 可能需要的配置）
- Modify: `bridge/app/browser/cdp_runtime.py`（移除 CDP 分支，只保留 native）
- Modify: `bridge/app/server.py`（移除 cdp_service 相关导入，保留 playwright 相关导入）

**Steps：**
- [x] 删除三个 CDP 文件
- [x] 从 `config.py` 移除 `CDP_PUBLIC_HOST`、`CDP_CONNECT_HOST`、`CDP_PORT`、`CDP_BASE_URL`、`CDP_CONNECT_BASE_URL`、`CDP_HOST_HEADER`、`CDP_WS_BASE_URL`、`CDP_TIMEOUT_SECONDS`
- [x] 从 `cdp_runtime.py` 移除 CDP 分支代码，`CdpRuntime` 直接委托给 `NativeBrowserRuntime`
- [x] 从 `server.py` 移除 CDP 相关导入
- [x] 从 `server.py` 移除 `/native/debug/ping` 和 `/native/debug/tabs` 调试 endpoint
- [x] 编译检查

**Acceptance：** 无 CDP 直连代码残留，bridge 正常启动
**Verification：** 编译通过，`BROWSER_RUNTIME=native_only` 下 /health 正常

### Task 5.2：删除 HTTP 轮询端点和扩展 HTTP 轮询逻辑

**Purpose：** 移除不再需要的 HTTP 轮询通道

**Files：**
- Modify: `bridge/app/server.py`（移除 /extension/pull、/extension/result 端点）
- Modify: `extension/background.js`（移除 pullBridgeCommand、postBridgeCommandResult、pollDevCommandOnce 等 HTTP 轮询逻辑）
- Modify: `extension/manifest.json`（移除 host_permissions）

**Steps：**
- [x] 从 server.py 移除 `/extension/pull`、`/extension/result`、`/extension/report` 端点（全部 HTTP 轮询端点一起移除，因为阶段 4 已确认 report 走 native）
- [x] 从 background.js 移除 HTTP 轮询相关函数（pullBridgeCommand、postBridgeCommandResult、pollDevCommandOnce）；将 `postReport(payload)` 重命名为 `sendNativeReport(payload)`，只保留 `nativePort.postMessage({type: "report", payload})` 路径，移除 HTTP fallback；保留 `extensionSnapshot` 的 message handler（content.js → background.js 入口不变）
- [x] 从 manifest.json 移除 `"host_permissions": ["http://127.0.0.1:17777/*"]`（此时扩展已不依赖 HTTP 访问 bridge）
- [x] 同步扩展并重载
- [x] 全量回归验证

**Acceptance：** 无 HTTP 轮询代码，扩展不依赖 host_permissions 访问 bridge
**Verification：** background.js 中无 `fetch.*BRIDGE_URL`、`/extension/*` HTTP 通道残留；manifest.json 中无 `host_permissions`；全量 workflow 通过

### Task 5.3：更新文档

**Purpose：** 移除文档中对 --remote-debugging-port 的要求

**Files：**
- Modify: `README.md`
- Modify: `docs/development.md`
- Modify: `docs/operations.md`
- Modify: `AGENTS.md`（如果引用了 CDP 端口）
- Modify: `LOCAL_DEV.md`（如果引用了 CDP 端口）

**Steps：**
- [x] README.md：快速开始部分移除 --remote-debugging-port 启动步骤，改为"安装 native host manifest + 启动 bridge"
- [x] docs/development.md：安装与启动部分更新，移除 CDP 端口配置，新增 native host 安装步骤
- [x] docs/operations.md：环境变量表移除 CDP_* 变量，新增 BROWSER_RUNTIME 变量说明
- [x] 更新 AGENTS.md 中对 CDP 的引用（如有）
- [x] 更新 LOCAL_DEV.md 中对 CDP 端口的引用（如有）
- [x] 更新 docs/capabilities.md 中的相关说明（如有）

**Acceptance：** 文档中无 --remote-debugging-port 要求，native host 安装步骤清晰
**Verification：** `grep -r "remote-debugging-port\|9333\|CDP_PORT\|CDP_PUBLIC_HOST" docs/ README.md AGENTS.md` 无结果

### Task 5.4：合并前检查清单（等待用户批准）

**Purpose：** 完成合并前的最终验证，产出检查清单供用户决策是否合并

**Files：** 无

**Steps：**
- [x] 最终全量回归验证（`BROWSER_RUNTIME=native_only`，无 --remote-debugging-port）：
  - 微博 read_post
  - X read_post + search
  - 小红书 read_post
  - 知乎 read_post + read_hot
  - /health、/tabs、/extension/state
- [x] `git diff --check`
- [x] 产出合并前检查清单报告给用户，包含：
  - 已完成的验证项
  - 已知残留风险（chrome.debugger 横幅、与 Codex 共存等）
  - 建议的合并命令：`git checkout main && git merge feature/native-messaging`
- [x] **等待用户明确批准后**才执行合并
- [x] 合并后更新 .agents/task-board.yaml 记录迁移完成

**Acceptance：** 用户批准合并，main 分支包含全部 native messaging 代码
**Verification：** 合并后在 main 上重跑一次微博 read_post 基线
