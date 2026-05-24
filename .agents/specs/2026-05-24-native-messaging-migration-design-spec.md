# Native Messaging Host 迁移设计规格（历史设计）

_日期：2026-05-24_
_状态：已实现，正文为历史设计参考，**不代表当前架构**_

> **⚠️ 重要提示：本 spec 仅为历史设计参考，不再维护。**
>
> 实际实现与本 spec 在以下关键点偏离：
>
> 1. **通道协议**：实现使用 HTTP long-poll（`/native/session/register`、`/native/session/pull`、`/native/session/result`、`/native/session/report`），**不是** spec 中描述的 WebSocket `/native/ws`。原因：宿主机无 `websockets` Python 库且无 pip 安装能力。
> 2. **shim 实现**：使用 `select.select()` 轮询 stdin（5s 超时重试），**不是** 阻塞 `read()` 或线程模型。
> 3. **CDP 直连已完全删除**：`BROWSER_RUNTIME` 仅支持 `auto`/`native_only` 两值（功能等价），不存在 `cdp_only`，无 CDP 回退路径，`cdp_client.py` / `cdp_ws_client.py` / `cdp_service.py` 全部删除。
> 4. **HTTP 轮询端点已删除**：`/extension/pull`、`/extension/result`、`/extension/report` 全部移除，扩展只通过 Native Messaging 通道。
> 5. **session 失效信号**：daemon 通过 `pull_command` 返回 `{"_error": "session_not_found"}`，shim 收到后退出并由扩展重连。
> 6. **新会话自动快照**：daemon 在 session 注册后异步发送 `snapshot.all` 命令，扩展遍历所有 tab 触发 `requestSnapshot`，恢复 `/extension/state` 报告缓存。
>
> **当前架构以代码为准**：`bridge/app/native_session_manager.py`、`bridge/app/native_host_shim.py`、`bridge/app/native_browser_runtime.py`、`extension/background.js`。
> **运维细节以 `docs/operations.md`、`docs/interfaces.md`、`docs/development.md` 为准。**
>
> 以下正文保留原设计稿，仅用于追溯设计动机和决策背景。

## 1. 目标

去掉 `--remote-debugging-port=9333` 启动要求，将浏览器控制从 CDP 直连迁移到扩展侧 `chrome.debugger` + Native Messaging 通道。

### 1.1 成功标准

- 浏览器无需 `--remote-debugging-port` 即可启动
- Bridge 通过扩展代理完成所有 15 个浏览器级操作
- 微博 `read_post` 基线验证通过
- X、小红书、知乎核心 workflow 回归通过
- 小红书 `prepare_publish_post` 文件上传通过

### 1.2 非目标

- 不改变外部 HTTP API 接口（skill、Agent 调用方式不变）
- 不改变扩展的站点语义逻辑（adapter 不变）
- 不改变 workflow 层职责

## 2. 架构

### 2.1 当前架构

```
Bridge daemon (:17777)
  ├── CDP HTTP ──→ 浏览器 (:9333/json/*)
  ├── CDP WebSocket ──→ 浏览器 (:9333/devtools)
  └── HTTP 轮询 ←→ 扩展 (/extension/pull, /extension/result)
```

问题：必须 `--remote-debugging-port=9333` 启动浏览器。

### 2.2 目标架构

```
外部调用者 / skill / media-agent-suite
  → Bridge daemon (:17777, 长期运行)
    → Native Session Manager (命令队列 + 结果路由)
      → Native Host shim (浏览器启动的子进程)
        ←stdio Native Messaging→ Browser Bridge Extension
          → chrome.tabs (标签页管理)
          → chrome.debugger (CDP 命令代理)
          → content script + site adapters (站点语义)
```

### 2.3 进程模型

```
systemd
  └── browser-bridge.service (Bridge daemon, 长期运行, :17777)
        └── NativeSessionManager (HTTP 长轮询 server at /native/ws)

Edge 浏览器
  └── Browser Bridge Extension
        └── connectNative("com.cuiguidong.browserbridge")
              └── 浏览器启动 native host 子进程
                    └── browser-bridge-native-shim.py
                          ├── stdin/stdout ←→ 扩展 (Native Messaging)
                          └── HTTP 长轮询 ←→ Bridge daemon (:17777/native/ws)
```

### 2.4 双向通道模型

Native Host shim 与 Bridge daemon 之间通过 **WebSocket** 建立持久双向通道：

**连接建立：**
1. 浏览器扩展调用 `chrome.runtime.connectNative("com.cuiguidong.browserbridge")`
2. 浏览器按系统 manifest 启动 `browser-bridge-native-shim.py` 子进程
3. shim 启动后，向 Bridge daemon 发起 WebSocket 连接 `http://127.0.0.1:17777/native/session/register`
4. daemon 的 `NativeSessionManager` 注册此 session，分配 sessionId

**命令下发（daemon → shim → 扩展）：**
1. daemon 有浏览器操作时，通过 WebSocket 推送命令给 shim
2. shim 将命令以 Native Messaging 格式（length-prefixed JSON）写入 stdout
3. 扩展从 `nativePort.onMessage` 收到命令并执行

**结果回传（扩展 → shim → daemon）：**
1. 扩展执行完毕，将结果通过 `nativePort.postMessage()` 发给 shim
2. shim 从 stdin 读取结果，通过 WebSocket 发回 daemon
3. daemon 匹配命令 id，唤醒等待的调用方

**报告推送（扩展 → shim → daemon）：**
1. 扩展的 content script 产生页面状态报告
2. 报告通过 `nativePort.postMessage({type: "report", payload: {...}})` 发给 shim
3. shim 转发给 daemon 的 `NativeSessionManager`，存入报告缓存

**连接断开与重连：**
- 浏览器关闭/shim 进程退出 → WebSocket 断开 → daemon 清理 session
- 扩展 Service Worker 挂起 → native 连接断开 → shim 检测到 stdin EOF → shim 退出 → daemon 清理 session
- Service Worker 唤醒后重新 `connectNative()` → 新 shim 进程 → 新 WebSocket → 新 session
- `chrome.alarms` keepalive 减少 Service Worker 挂起频率

## 3. Native Messaging 协议

### 3.1 消息格式

Chrome Native Messaging 是 length-prefixed 二进制协议，**不是** JSON line：

```
[4 bytes: message length, native-endian uint32][UTF-8 JSON payload]
```

- 消息长度不含这 4 字节本身
- host → Chrome 最大 1 MB
- Chrome → host 最大 64 MiB（截图 base64 通常在此范围内）
- JSON payload 必须是有效的 JSON 对象或数组

### 3.2 标准 Tab 结构

所有涉及标签页的方法使用统一的 tab 对象结构：

```json
{
  "id": "123",
  "nativeTabId": 123,
  "title": "页面标题",
  "url": "https://example.com",
  "type": "page"
}
```

- `id`：字符串形式的 tab id，与现有 `targetId` 约定兼容
- `nativeTabId`：数字形式，供 `chrome.tabs` / `chrome.debugger` API 使用
- 当现有代码传递 `targetId` 字符串时，native runtime 将其转为 `nativeTabId` 整数

### 3.3 消息类型

**命令（Bridge daemon → 扩展，经 shim 转发）：**

```json
{"id": "cmd_001", "method": "tabs.list", "params": {}}
{"id": "cmd_002", "method": "tabs.create", "params": {"url": "https://...", "active": true}}
{"id": "cmd_003", "method": "tabs.activate", "params": {"tabId": 123}}
{"id": "cmd_004", "method": "tabs.close", "params": {"tabId": 123}}
{"id": "cmd_005", "method": "debugger.attach", "params": {"tabId": 123}}
{"id": "cmd_006", "method": "debugger.send", "params": {"tabId": 123, "command": "Page.navigate", "params_": {"url": "..."}}}
{"id": "cmd_007", "method": "debugger.detach", "params": {"tabId": 123}}
{"id": "cmd_008", "method": "semantic.invoke", "params": {"method": "read", "params": {...}, "targetId": "123", "targetUrl": "..."}}
{"id": "cmd_009", "method": "ping", "params": {}}
```

**结果（扩展 → Bridge daemon，经 shim 转发）：**

```json
{"id": "cmd_001", "result": {"tabs": [{"id": "123", "nativeTabId": 123, "title": "...", "url": "...", "type": "page"}]}}
{"id": "cmd_002", "result": {"tab": {"id": "456", "nativeTabId": 456, ...}}}
{"id": "cmd_005", "result": {"attached": true}}
{"id": "cmd_006", "result": {"frameId": "...", "loaderId": "..."}}
{"id": "cmd_008", "result": {"content": {...}}}
```

**错误（扩展 → Bridge daemon）：**

```json
{"id": "cmd_005", "error": {"code": "debugger_already_attached", "message": "Tab is already being debugged by another extension"}}
```

错误码清单：
- `debugger_already_attached`：tab 已被 DevTools 或其他扩展调试
- `debugger_restricted_domain`：目标页为 chrome://、edge:// 等受限域名
- `debugger_attach_failed`：attach 失败（其他原因）
- `tab_not_found`：tabId 无效或已关闭
- `command_failed`：CDP 命令执行失败
- `timeout`：操作超时

**报告（扩展 → Bridge daemon，经 shim 转发，无 id）：**

```json
{"type": "report", "payload": {"url": "...", "pageType": "...", ...}}
```

### 3.4 方法清单

| 方法 | 等价原 CDP 操作 | 说明 |
|------|----------------|------|
| `tabs.list` | `GET /json/list` | `chrome.tabs.query({})` |
| `tabs.create` | `PUT /json/new` | `chrome.tabs.create({url})` |
| `tabs.activate` | `GET /json/activate` | `chrome.tabs.update(tabId, {active: true})` |
| `tabs.close` | `GET /json/close` | `chrome.tabs.remove(tabId)` |
| `debugger.attach` | 无（WebSocket 建连） | `chrome.debugger.attach({tabId}, '1.3')` |
| `debugger.send` | WebSocket CDP 命令 | `chrome.debugger.sendCommand({tabId}, method, params)` |
| `debugger.detach` | WebSocket 断连 | `chrome.debugger.detach({tabId})` |
| `semantic.invoke` | `extension_runtime.invoke()` | 转发给 content script |
| `ping` | 无 | 连接保活探测 |

`debugger.send` 的 `command` 字段直接使用 CDP 方法名（如 `Page.navigate`、`Runtime.evaluate`、`Page.captureScreenshot`），`params_` 字段是 CDP 命令参数。

### 3.5 semantic.invoke 目标 tab 解析

当 `semantic.invoke` 需要确定目标 tab 时，解析在 **Bridge daemon 侧**完成（不在扩展侧），按以下优先级：

1. `targetId` 存在 → 查找 `nativeTabId == int(targetId)` 的 tab
2. `targetUrl` 存在 → 复用 Bridge 现有匹配语义：
   - 先 `tabs.list` 获取全部 tab
   - 规范化后 exact URL 匹配（去除 trailing slash，**保留 query 参数**——搜索页、分享页、带参数内容页依赖 query 区分）
   - X 额外支持 `x_status_id` 匹配（从 URL 中提取 status ID 比对）
   - 站点级 canonical match：仅按白名单忽略 tracking 参数（如 `utm_*`、`ref`、`from`），不全局丢弃 query
3. 都不存在 → 查找最近活跃的匹配站点 tab（按 site config 的 hosts 过滤）

解析得到 `nativeTabId` 后，daemon 通过 Native Messaging 发送 `semantic.invoke` 命令，命令中携带解析后的 `tabId`。扩展侧 background.js 收到后直接用 `chrome.tabs.sendMessage(tabId, ...)` 转发给该 tab 的 content script。

**关键：不要在扩展侧做 URL 匹配。** 扩展侧只接收已解析好的 tabId。所有匹配逻辑复用 Bridge 现有的 `ExtensionRuntime` 中的 `find_hint_with_debug` 规范化策略。

## 4. 扩展侧改造

### 4.1 manifest.json

```json
{
  "permissions": ["activeTab", "tabs", "scripting", "storage", "alarms", "debugger", "nativeMessaging"]
}
```

`nativeMessaging` 是 MV3 的标准权限，允许扩展调用 `chrome.runtime.connectNative()`。系统 native host manifest 单独安装。

### 4.2 background.js 改造

**阶段 1-3（并行期）：** 新增 Native Messaging 连接，保留现有 HTTP 轮询。Native 通道用于浏览器级操作，HTTP 轮询继续承载语义命令。

**阶段 4（切换期）：** 语义命令从 HTTP 轮询切到 Native Messaging。

**阶段 5（清理期）：** 移除 HTTP 轮询逻辑。

核心结构：

```javascript
// Native Messaging 连接
let nativePort = null;

function connectNative() {
  nativePort = chrome.runtime.connectNative('com.cuiguidong.browserbridge');
  nativePort.onMessage.addListener(handleNativeCommand);
  nativePort.onDisconnect.addListener(() => {
    console.warn('[Browser Bridge] Native disconnected:', chrome.runtime.lastError?.message);
    nativePort = null;
    // Service Worker 唤醒后会重新连接
  });
}

connectNative();

// chrome.alarms keepalive 防止 Service Worker 挂起
chrome.alarms.create('keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepalive' && !nativePort) {
    connectNative();
  }
});

// 命令分发
async function handleNativeCommand(msg) {
  const { id, method, params } = msg;
  try {
    let result;
    if (method === 'tabs.list') {
      const tabs = await chrome.tabs.query({});
      result = { tabs: tabs.map(normalizeTab) };
    } else if (method === 'tabs.create') {
      const tab = await chrome.tabs.create({ url: params.url, active: params.active !== false });
      result = { tab: normalizeTab(tab) };
    } else if (method === 'tabs.activate') {
      await chrome.tabs.update(params.tabId, { active: true });
      result = { activated: true };
    } else if (method === 'tabs.close') {
      await chrome.tabs.remove(params.tabId);
      result = { closed: true };
    } else if (method.startsWith('debugger.')) {
      result = await handleDebuggerCommand(method, params);
    } else if (method === 'semantic.invoke') {
      result = await handleSemanticInvoke(params);
    } else if (method === 'ping') {
      result = { alive: true, timestamp: Date.now() };
    }
    nativePort.postMessage({ id, result });
  } catch (error) {
    nativePort.postMessage({
      id,
      error: { code: error.code || 'unknown', message: error.message }
    });
  }
}

function normalizeTab(tab) {
  return {
    id: String(tab.id),
    nativeTabId: tab.id,
    title: tab.title || '',
    url: tab.url || '',
    type: 'page',
  };
}
```

### 4.3 chrome.debugger 使用

```javascript
// attached tab cache：避免重复 attach
const attachedTabs = new Set();

/**
 * 确保 tab 已 attach 到 debugger。统一错误分类。
 * debugger.attach 和 debugger.send 共用此函数。
 */
async function ensureDebuggerAttached(tabId) {
  if (attachedTabs.has(tabId)) return;
  const debuggee = { tabId };
  try {
    await chrome.debugger.attach(debuggee, '1.3');
    attachedTabs.add(tabId);
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('already being debugged') || msg.includes('Another debugger')) {
      throw { code: 'debugger_already_attached', message: msg };
    }
    if (msg.includes('Cannot access') || msg.includes('restricted') || msg.includes('chrome://') || msg.includes('edge://')) {
      throw { code: 'debugger_restricted_domain', message: msg };
    }
    throw { code: 'debugger_attach_failed', message: msg };
  }
}

async function handleDebuggerCommand(method, params) {
  const debuggee = { tabId: params.tabId };

  if (method === 'debugger.attach') {
    if (attachedTabs.has(params.tabId)) {
      return { attached: true, alreadyAttached: true };
    }
    await ensureDebuggerAttached(params.tabId);
    return { attached: true };
  }

  if (method === 'debugger.detach') {
    try {
      await chrome.debugger.detach(debuggee);
      attachedTabs.delete(params.tabId);
      return { detached: true };
    } catch (e) {
      attachedTabs.delete(params.tabId);
      return { detached: true, warning: e.message };
    }
  }

  if (method === 'debugger.send') {
    await ensureDebuggerAttached(params.tabId);
    try {
      const result = await chrome.debugger.sendCommand(
        debuggee, params.command, params.params_ || {}
      );
      return result || {};
    } catch (e) {
      if (e.message?.includes('detached') || e.message?.includes('not attached')) {
        attachedTabs.delete(params.tabId);
      }
      throw { code: 'command_failed', message: e.message };
    }
  }
}

// tab 关闭时清理 attach cache
chrome.tabs.onRemoved.addListener((tabId) => {
  attachedTabs.delete(tabId);
});
```

**chrome.debugger 使用要点：**
- 第一个参数必须是 `{ tabId: number }` 形式的 Debuggee 对象
- 对已在 DevTools/Codex 中调试的 tab，`attach` 会抛出 `debugger_already_attached`
- restricted domains：`chrome://`、`edge://`、`chrome-extension://` 等无法调试
- 浏览器会显示 "is debugging this browser" 横幅
- 使用 auto-attach 模式：`debugger.send` 时如果未 attach 则自动 attach

### 4.4 content.js 语义通道

**阶段 1-3：** content.js 的语义命令仍通过现有 HTTP 轮询通道（`/extension/pull`、`/extension/result`）。这部分不改。

**阶段 4：** content.js 的语义命令改为通过 Native Messaging 转发。background.js 收到 `semantic.invoke` 后，通过 `chrome.tabs.sendMessage(tabId, ...)` 转发给对应 tab 的 content script。

## 5. Bridge 侧改造

### 5.1 新增文件

| 文件 | 职责 |
|------|------|
| `bridge/app/native_host_shim.py` | Native Messaging 协议编解码 + WebSocket 转接 |
| `bridge/app/native_session_manager.py` | HTTP 长轮询 server、session 注册、命令队列、结果路由 |
| `bridge/app/native_browser_runtime.py` | 实现与 CdpRuntime 相同的 15 个方法接口 |
| `scripts/install-native-host.sh` | 在系统中注册 native host manifest |
| `native-messaging/com.cuiguidong.browserbridge.json` | Native host manifest |

### 5.2 改造文件

| 文件 | 改造内容 |
|------|----------|
| `bridge/app/server.py` | 新增 WebSocket endpoint `/native/ws`，注入 NativeSessionManager |
| `bridge/app/browser/cdp_runtime.py` | 根据 `BROWSER_RUNTIME` 配置选择 runtime 实现 |
| `bridge/app/config.py` | 新增 `BROWSER_RUNTIME` 配置项 |
| `bridge/app/extension/extension_runtime.py` | 语义命令可选走 native messaging（逐步迁移） |
| `extension/background.js` | 新增 Native Messaging 连接和命令分发（阶段 1-3 保留 HTTP 轮询） |
| `extension/manifest.json` | 添加 `debugger` + `nativeMessaging` 权限 |

### 5.3 BROWSER_RUNTIME 配置

环境变量 `BROWSER_RUNTIME` 控制浏览器控制通道选择：

| 值 | 行为 |
|----|------|
| `auto`（默认） | 优先使用 native session，无活跃 native session 时回退 CDP 直连 |
| `native_only` | 只使用 native session，无活跃 session 时报错，不回退 CDP |
| `native_only（严格只走 native）

**阶段 2/3 验收必须在 `BROWSER_RUNTIME=native_only` 且浏览器未开 `--remote-debugging-port` 下通过。** 如果在 `auto` 模式下测试，CDP 回退可能掩盖 native 通道的失败。

### 5.4 暂不删除的文件（阶段 1-4 保留）

- `bridge/app/cdp_client.py`
- `bridge/app/cdp_ws_client.py`
- `bridge/app/cdp_service.py`
- `bridge/app/config.py` 中的 CDP 配置
- HTTP 轮询端点（`/extension/pull`、`/extension/result`、`/extension/report`）

阶段 5 全绿后才删除。

### 5.5 Native Host Shim

`native_host_shim.py` 是独立 Python 脚本，使用项目已有的 `websockets` 库（已在 `requirements.txt` 中）。核心职责：

1. 从 stdin 以 length-prefixed JSON 读取扩展消息
2. 通过 WebSocket 转发给 Bridge daemon
3. 从 WebSocket 接收 daemon 命令
4. 以 length-prefixed JSON 写入 stdout 给扩展

```python
#!/usr/bin/env python3
"""Native Messaging host shim for Browser Bridge."""
import struct
import sys
import json
import asyncio
import threading

import websockets

BRIDGE_WS_URL = "http://127.0.0.1:17777/native/session/register"

def read_native_message():
    """Read one Native Messaging message from stdin (length-prefixed JSON)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack('<I', raw_length)[0]
    data = sys.stdin.buffer.read(length)
    if not data:
        return None
    return json.loads(data)

def write_native_message(msg):
    """Write one Native Messaging message to stdout (length-prefixed JSON)."""
    encoded = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('<I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

async def run():
    async with websockets.connect(BRIDGE_WS_URL) as ws:
        # 从 daemon 接收命令并写给扩展的线程
        def daemon_to_extension():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def _recv():
                    async for data in ws:
                        msg = json.loads(data)
                        write_native_message(msg)
                loop.run_until_complete(_recv())
            except Exception:
                pass
            finally:
                loop.close()

        t = threading.Thread(target=daemon_to_extension, daemon=True)
        t.start()

        # 主线程：从扩展读消息并转发给 daemon（阻塞式 stdin）
        while True:
            msg = read_native_message()
            if msg is None:
                break
            await ws.send(json.dumps(msg, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(run())
```

### 5.6 Native Host Manifest

```json
{
  "name": "com.cuiguidong.browserbridge",
  "description": "Browser Bridge native messaging host",
  "type": "stdio",
  "path": "/absolute/path/to/browser-bridge-native-shim",
  "allowed_origins": [
    "chrome-extension://<extension-id>/"
  ]
}
```

安装位置：
- Chrome (Linux): `~/.config/google-chrome/NativeMessagingHosts/com.cuiguidong.browserbridge.json`
- Edge (Linux): `~/.config/microsoft-edge/NativeMessagingHosts/com.cuiguidong.browserbridge.json`
- Chrome (macOS): `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`
- Edge (macOS): `~/Library/Application Support/Microsoft Edge/NativeMessagingHosts/`

## 6. 迁移阶段

### 阶段 1：基础设施 + ping 验证

- 建立独立分支 `feature/native-messaging`
- 实现 `native_host_shim.py`（length-prefixed JSON 编解码 + WebSocket 转接）
- 实现 `native_session_manager.py`（HTTP 长轮询 server + session 注册）
- 安装 native host manifest
- 扩展 background.js 新增 Native Messaging 连接（**保留现有 HTTP 轮询不动**）
- **验证**：ping 往返成功、tabs.list 返回真实标签页

### 阶段 2：浏览器级操作迁移

- 实现 `native_browser_runtime.py`（15 个方法）
- 实现 `tabs.*` 方法
- 实现 `debugger.send` 代理（navigate, reload, evaluate, screenshot）
- 实现 `set_file_input_files` 通过 chrome.debugger
- `cdp_runtime.py` 根据 `BROWSER_RUNTIME` 配置选择 runtime
- **验证**：在 `BROWSER_RUNTIME=native_only` 且浏览器未开 `--remote-debugging-port` 下，每个操作与 CDP 直连结果对比
- **此阶段 HTTP 轮询和 CDP 直连都保留**

### 阶段 3：核心 workflow 回归

- 微博 `read_post` 基线
- X `read_post` + `search`
- 小红书 `read_post` + `prepare_publish_post`（重点：文件上传）
- 知乎 `read_post` + `read_hot`
- **验证**：在 `BROWSER_RUNTIME=native_only` 下全部核心 workflow 通过
- **此阶段 HTTP 轮询和 CDP 直连都保留**

### 阶段 4：语义通道迁移

- 将 ExtensionRuntime 的语义命令（read/act/verify/capabilities/probe_ready）从 HTTP pull/result 切到 Native Messaging
- 将 content script 的 page-state report 从 HTTP POST `/extension/report` 迁到 native report 消息（`{type: "report", payload: {...}}`）
- background.js 中 content script 的 `reportSnapshot()` 改为：优先通过 `nativePort.postMessage()` 发送，native 连接不可用时回退到 HTTP POST `/extension/report`
- content.js 语义命令改为通过 `chrome.tabs.sendMessage` 转发
- HTTP 轮询端点保留但标记 deprecated
- **验收**：在 native_only 模式下，`/extension/state` 返回的 `lastReport` 不为 null，且时间戳新鲜
- **此阶段 CDP 直连保留作为对照**

### 阶段 5：清理

- 全部 workflow 回归通过后：
- 删除 `cdp_client.py`、`cdp_ws_client.py`、`cdp_service.py`
- 删除 CDP 相关配置
- 删除 HTTP 轮询端点（`/extension/pull`、`/extension/result`）
- 移除扩展中的 HTTP 轮询逻辑和 `host_permissions`
- 更新文档（移除 `--remote-debugging-port` 要求）
- 合并回主分支

## 7. chrome.debugger 已知限制

| 限制 | 影响 | 对策 |
|------|------|------|
| Restricted domains（chrome://, edge:// 等） | 无法调试浏览器内部页 | 不需要，这些页不涉及 |
| 与 DevTools 不能同时调试同一 tab | 用户开 DevTools 时操作失败 | 检测 `debugger_already_attached` 错误，提示用户 |
| 与 Codex 扩展可能冲突 | Codex 也用 chrome.debugger | 测试共存场景 |
| "is debugging this browser" 横幅 | 用户可见提示 | 接受，与 DevTools 相同 |
| 跨域 iframe 受限 | 某些嵌入内容无法访问 | 按需测试 |
| DOM.setFileInputFiles 行为可能不同 | 小红书发帖上传 | 阶段 3 重点测试 |

## 8. Native Messaging 已知约束

| 约束 | 说明 |
|------|------|
| host → Chrome 最大 1 MB | daemon 发给扩展的命令通常很小，不受限 |
| Chrome → host 最大 64 MiB | 截图 base64 等大 payload 在此方向，一般不会超限 |
| 一个 native host 实例对应一个扩展连接 | Service Worker 重连会启动新 host 进程 |
| host 进程由浏览器管理 | 浏览器关闭时 host 被终止 |
| manifest 必须在系统注册路径 | 需要安装脚本 |
| shim 依赖 | 使用项目已有的 `websockets` 库（requirements.txt 中已有） |
