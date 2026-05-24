# Native Messaging 无感控制架构设计规格 (Historical / Superseded)

> [!IMPORTANT]
> **历史设计/实施过程产物 (Historical / Superseded)**
> 本文件是 `feature/native-messaging` 分支在迁移与双模式架构设计过程中的历史 spec/plan，仅用于记录设计背景、讨论线索和历史推演。
> **它不代表当前项目的最终架构事实**。关于项目的最新及正式事实，请以正式文档 [docs/architecture.md](file:///home/cuiguidong/workspace/personal/projects/Python/browser-bridge-project/docs/architecture.md) 以及实际运行代码为准。

_日期：2026-05-24_
_状态：已实现并归档，**不代表当前架构**_

---

## 1. 背景与动机

目前 `browser-bridge` 项目已通过 Native Messaging 移除了对浏览器 `--remote-debugging-port=9333` 的启动依赖，通过扩展代理了底层 CDP 命令。

然而，扩展对 `chrome.debugger.attach` / `sendCommand` 的调用会导致浏览器顶部出现强制性的安全调试横幅：
> `"Browser Bridge Extension 已开始调试此浏览器"`

为了提供绝对平滑、无感、原生的“日常浏览器助手”级伴侣体验，我们需要在通信基座中对 **常规控制操作进行 No-Debugger 架构升级**，彻底干掉常规操作下的调试横幅，同时保留极其克制且原生的 CDP 功能作为特定需求的后备能力。

---

## 2. 核心设计原则

1.  **出厂无横幅**：除极其特殊且无法平替的物理操作外，微博、知乎、小红书的日常读取、导航、刷新、脚本计算、甚至文件上传等所有主流操作，必须 100% 避免触发调试横幅。
2.  **不增加配置负担**：不对用户暴露所谓的“模式配置项”，不设自适应开关。系统内部高内聚、硬性平替。
3.  **极致 DOM 文件注入**：抛弃多步的 CDP 级 `DOM.setFileInputFiles`，改用网页内容脚本直接拉取 Blob + DOM 原生 `DataTransfer` 注入，彻底干掉文件上传时的调试横幅。

---

## 3. 架构双闸设计与 Git 状态转换（无横幅及运行时权限安全收敛）

为了确保在常规操作中绝对不意外激活 `chrome.debugger`，且防范高层 API 的越权与安全性漏洞，本设计建立三道强力闸口：

1.  **物理权限与 Manifest 自动构建硬闸**：
    *   在 `extension/` 目录下拆分并长期维护三份文件：
        *   `manifest.prod.json` (生产模板：**物理去除 `"debugger"` 权限声明**，是正式出厂与打包发布的唯一事实源)。
        *   `manifest.dev.json` (开发模板：保留 `"debugger"` 权限，用于特种 CDP 诊断与高级调试)。
        *   `manifest.json` (Chrome 加载的实际入口文件，**此文件写入 `.gitignore` 排除提交**)。
    *   **Git 状态转换策略**：
        *   在实施第一阶段，显式在本地工作区执行：
            ```bash
            git rm --cached extension/manifest.json
            ```
            在 Git 树中安全地取消对该物理入口文件的跟踪，将其彻底与版本历史分离，防止误提交开发权限。
    *   **构建与重载映射机制**：
        *   修改 `./scripts/dev_reload_extension.sh`，在同步与触发重载的前置原子操作中，**增加自动覆盖逻辑**：若为开发态，自动将 `manifest.dev.json` 复制或软链为 `manifest.json`，再同步至宿主加载。
        *   在生产发布/打包脚本中，强制将 `manifest.prod.json` 覆盖输出为 `manifest.json` 进行纯净打包，确保发布产物 100% 物理上不含 `"debugger"`。
2.  **后端路由软闸**：
    *   后端 `NativeBrowserRuntime` 拦截任何 `debugger.*` 动作。若未检测到高级授权开发权限，拒绝向下游发送，避免产生未授权 of 底层通道报错。
3.  **运行时最小权限收敛闸（运行时安全防御与白名单机制）**：
    *   为了防止生产版声明的 `"<all_urls>"` 导致越权安全漏洞，后端 `NativeBrowserRuntime` 强行实施运行时支持站点的**白名单硬过滤与后缀比对拦截 (suffix match)**：
        *   **白名单机械聚合并注入（实现细节）**：
            1.  在 `SiteRegistry` (位于 `bridge/app/sites/registry.py`) 中，增加一个方法 `get_allowed_hosts() -> List[str]`，从所有已注册的 site module 中的 `hosts` 属性中聚合出所有的 hosts 列表并返回。
            2.  在 `bridge/app/server.py` 初始化时，将 `site_registry` 全局实例注入到 `CdpRuntime` 中，并继而传入 `NativeBrowserRuntime`。
            3.  当对指定 Tab 域名执行 JS/截图/上传时，后端从 URL 提取 hostname，对 `get_allowed_hosts()` 列表进行严密的、带点边界的安全 `suffix match` 校验：
                `hostname == allowed_host or hostname.endswith("." + allowed_host)`
                这能确保 `evilweibo.com` 等钓鱼/伪装域名绝不会被误放行通过。
        *   **生产拦截模式 (Default)**：对于非白名单域名（例如 `mail.google.com`），后端直接拦截并强行抛出 `security_violation` 错误。
        *   **开发模式豁免 (`DEVELOPMENT_MODE = true`)**：只有当读取进程环境变量 `os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"` 时，才豁免此白名单限制（用于新站点开发调试）。

---

## 4. 全新高层通信协议指令设计

后端不再向下发送底层的 `debugger.send`，而是使用一组高层通信协议指令，扩展完全通过 MV3 的原生 API 予以承载。

### 4.1 协议指令格式定义

#### 1) 页面导航 `tab.navigate`
*   **请求 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "method": "tab.navigate",
      "params": {
        "tabId": 12345,
        "url": "https://weibo.com/"
      }
    }
    ```
*   **响应 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "result": {
        "navigated": true
      }
    }
    ```

#### 2) 页面刷新 `tab.reload`
*   **请求 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "method": "tab.reload",
      "params": {
        "tabId": 12345,
        "ignoreCache": true
      }
    }
    ```
*   **响应 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "result": {
        "reloaded": true
      }
    }
    ```

#### 3) JS 脚本计算 `tab.evaluate` (收窄后的 returnByValue 合同)
*   **注意（合同约束）**：**仅支持 `returnByValue` 风格的可序列化表达式**。DOM 节点、函数、循环对象、特殊 Promise 必须在表达式内部转化为可 JSON 序列化对象，否则将返回失败。
*   **请求 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "method": "tab.evaluate",
      "params": {
        "tabId": 12345,
        "expression": "document.readyState"
      }
    }
    ```
*   **响应 Payload（统一 Envelope 定义）**：
    *   **成功响应**：
        ```json
        {
          "id": "cmd_xxxxxx",
          "result": {
            "value": "complete"
          }
        }
        ```
    *   **失败响应**：
        ```json
        {
          "id": "cmd_xxxxxx",
          "error": {
            "code": "js_eval_failed",
            "message": "ReferenceError: xxx is not defined",
            "stack": "..."
          }
        }
        ```

#### 4) 页面截图 `tab.screenshot`
*   **限制**：仅支持可见区，不支持 CDP 独有的全网页滚动滚动截图。
*   **请求 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "method": "tab.screenshot",
      "params": {
        "tabId": 12345,
        "format": "png"
      }
    }
    ```
*   **响应 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "result": {
        "data": "base64_encoded_image_string..."
      }
    }
    ```

#### 5) 本地文件上传 `tab.uploadFile` (无限制、强绑定 Ticket 页面拉取设计)
*   **背景**：Native Messaging 存在 **1 MB** 单条消息限制，且跨进程消息传递大体积 Base64 会造成渲染进程的卡顿或发送失败。
*   **安全与模块解耦重塑（富属性绑定的 Ticket 授权防伪机制与实现细节）**：
    1.  **防止循环导入与模块解耦**：拒绝裸 path 直读。为防止 `server.py` 与 `native_browser_runtime.py` 在引用 Token 数据结构时发生致命的 Python **循环导入 (Circular Import)**，我们将其彻底拆分为一个自包含、零外部依赖的独立模块：`bridge/app/upload_tokens.py`。
    2.  **Ticket 授权机制**：由 `upload_tokens.py` 内部维护一个全局线程安全的 `_upload_tokens` 内存 Map，并暴露签发 (`issue_upload_token`) 与消费验证 (`consume_upload_token`) 接口。
    3.  **富属性多重校验绑定**：在 `_upload_tokens` 内存映射中绑定以下关键字段：
        `fileId` -> `{ path, size, mime, sessionId, tabId, expectedOrigin, createdAt }`
    3.  **临时本地回环端点与跨域预检放行 (实现细节)**：
        *   后端增开本地回环端点：`GET /dev/file/get?id=<fileId>`，**仅限本地 127.0.0.1 访问**。
        *   页面内容脚本 `content.js` 在发起 fetch 拉取时，必须在请求头中硬性携带：
            `X-Browser-Bridge-Tab-Id: <tabId>`
            `X-Browser-Bridge-Session-Id: <sessionId>`
        *   为了防范跨域预检 (CORS Preflight) 拦截，Bridge daemon 的 OPTIONS 预检及 GET 请求中，必须强加支持该 Header 的跨域响应头：
            ```python
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-Browser-Bridge-Tab-Id, X-Browser-Bridge-Session-Id"
            response.headers["Cache-Control"] = "no-store"
            ```
        *   **CORS 防御与安全核验**：后端在拉取时比对请求的 `Origin` 头与 `expectedOrigin`，且校验 `X-Browser-Bridge-Tab-Id` 是否与绑定 `tabId` 严格一致，以及 30 秒有效生存期，否则一律返回 `403 Forbidden` JSON 封套。
    4.  **原子消费时机 (Atomic Consumption)**：**严禁先 Pop 再校验**，以防预检报错误烧 Ticket。后端提供只读获取 (`get_upload_token`) 和销毁 (`remove_upload_token`) 接口。仅在全部首包校验通过、**即将向浏览器返回数据流响应的瞬间**，再调用销毁消费。
    5.  **失败重签机制**：如果传输意外断开，内容脚本反馈 background，由后端 `NativeBrowserRuntime` 自动重新生成全新 fileId 并重下发指令。
*   **网页端直拉 Blob 传输重构**：
    *   后端下发 `tab.uploadFile` 仅发送轻量 JSON 索引（含 name 和 fileId）。
    *   扩展收到后直接将其发送给 `content.js`。
    *   页面侧（`content.js`）直接发起 fetch，从本地 `http://127.0.0.1:17777/dev/file/get?id=<fileId>` 流式读取二进制数据并生成原生 `Blob`。
    *   **传输性能边界**：此方案绕过了 background base64 中转。文件在页面端实例化为 W3C `File` 时仍会占用网页渲染进程的临时物理内存，大文件传输开销受限于浏览器自身的 GC 及 DOM 注入性能。
*   **请求 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "method": "tab.uploadFile",
      "params": {
        "tabId": 12345,
        "selector": "input[type='file']",
        "files": [
          {
            "name": "image.jpg",
            "fileId": "file_nonce_hex_xxxxxx"
          }
        ]
      }
    }
    ```
*   **响应 Payload**：
    ```json
    {
      "id": "cmd_xxxxxx",
      "result": {
        "uploaded": true
      }
    }
    ```

---

## 5. 关键实现技术细节

### 5.1 扩展与内容脚本权限配置

为了确保内容脚本及背景脚本有绝对权限跨域连接本地 daemon，且能完全发挥原生 `chrome.scripting` 脚本计算和截图能力：
*   在 `manifest.prod.json` 与 `manifest.dev.json` 中均硬性声明主机和脚本执行权限：
    ```json
    "permissions": [
      "activeTab",
      "tabs",
      "scripting",
      "storage",
      "alarms",
      "nativeMessaging"
    ],
    "host_permissions": [
      "<all_urls>",
      "http://127.0.0.1:17777/*"
    ]
    ```

### 5.2 扩展背景脚本 (`background.js`) 的原生平替与安全配置

#### 1) `tab.evaluate` 平替（基于 `chrome.scripting.executeScript` 与 Promise 解析）
```javascript
async function handleTabEvaluate(params) {
  const { tabId, expression } = params;

  const results = await chrome.scripting.executeScript({
    target: { tabId: tabId },
    world: 'MAIN',
    func: async (expr) => {
      try {
        const resultVal = await eval(expr);
        return { ok: true, value: resultVal };
      } catch (e) {
        return { ok: false, error: e.message, stack: e.stack };
      }
    },
    args: [expression]
  });

  const res = results[0]?.result;
  if (!res) {
    return { error: { code: 'js_eval_failed', message: 'No result from executeScript' } };
  }
  if (!res.ok) {
    return { error: { code: 'js_eval_failed', message: res.error, stack: res.stack } };
  }
  return { result: { value: res.value } };
}
```

#### 2) `tab.screenshot` 激活与现场 try/finally 恢复现场策略
*   **切换与现场强制恢复设计**：
    ```javascript
    async function handleTabScreenshot(params) {
      const { tabId, format } = params;

      const targetTab = await chrome.tabs.get(tabId);
      const windowId = targetTab.windowId;

      // 1. 获取该窗口当前活动状态的 tab
      const activeTabs = await chrome.tabs.query({ windowId: windowId, active: true });
      const originalActiveTab = activeTabs[0];

      let wasSwitched = false;

      try {
        if (originalActiveTab && originalActiveTab.id !== tabId) {
          // 2. 现场不一致，切换至目标 tab
          await chrome.tabs.update(tabId, { active: true });
          wasSwitched = true;
          // 3. 经验等待（非同步阻塞对齐，150ms 经验延迟），等待浏览器完成当前帧渲染
          await new Promise((resolve) => setTimeout(resolve, 150));
        }

        // 4. 执行截图
        const dataUrl = await chrome.tabs.captureVisibleTab(windowId, {
          format: format || 'png'
        });

        const base64Data = dataUrl.split(',')[1];
        return { data: base64Data };
      } finally {
        // 5. 强保障！无论截图成功还是抛错，均 100% 恢复原先的 active 状态现场
        if (wasSwitched && originalActiveTab) {
          await chrome.tabs.update(originalActiveTab.id, { active: true });
        }
      }
    }
    ```

---

### 5.3 扩展内容脚本 (`content.js`) 的本地 HTTP 文件拉取与 DataTransfer 注入

```javascript
// background.js 转发逻辑（极轻量）：
async function handleTabUploadFile(params) {
  const { tabId, sessionId, selector, files } = params;

  // 注入 tabId 与 sessionId 供内容脚本拉取文件时作为头部携带
  const filesWithTabContext = files.map(f => ({ ...f, tabId, sessionId }));

  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, {
      action: 'domFileUpload',
      payload: { selector, files: filesWithTabContext }
    }, (res) => resolve(res || { error: 'No response from content script' }));
  });
}
```

```javascript
// content.js 页面侧拉取与 DOM 原生直注逻辑（流式加载与内存重组）：
async function handleDomFileUpload(payload) {
  const { selector, files } = payload;
  const input = document.querySelector(selector);
  if (!input) throw new Error("File input element not found");

  const dt = new DataTransfer();
  for (const f of files) {
    // 页面端持有一次性 fileId, 跨域直连本地 daemon 拉取原生 Blob，硬性携带 Tab-Id 及 Session-Id 校验头
    const response = await fetch(`http://127.0.0.1:17777/dev/file/get?id=${encodeURIComponent(f.fileId)}`, {
      headers: {
        "X-Browser-Bridge-Tab-Id": String(f.tabId),
        "X-Browser-Bridge-Session-Id": String(f.sessionId)
      }
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch file: ${response.statusText}`);
    }
    const blob = await response.blob();
    const file = new File([blob], f.name, { type: blob.type || 'application/octet-stream' });
    dt.items.add(file);
  }

  input.files = dt.files;
  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new Event('input', { bubbles: true }));
  return { uploaded: true };
}
```

---

## 6. 现有 runtime 调用面 -> 新协议替换矩阵

| 现有底层调用 (在 `native_browser_runtime.py` 中) | 使用的新高层协议 | 行为差异 / 实现方式 | 验收与验证手段 |
| --- | --- | --- | --- |
| `list_tabs` | `tabs.list` | 无改变，继续使用 `chrome.tabs.query` | 正常返回标签列表 |
| `_try_reuse_tab` (导航) | `tab.navigate` | 不发 `Page.navigate`，调用 `chrome.tabs.update` | 页面成功载入目标页 |
| `navigate_tab` (开启导航) | `tab.navigate` | 不发 `Page.navigate`，调用 `chrome.tabs.update` | 页面成功载入目标页 |
| `_wait_for_page_load` | `tab.evaluate` | 调用 `tab.evaluate` 查询 `document.readyState` | 返回 `'complete'` 状态 |
| `reload_tab` | `tab.reload` | 不发 `Page.reload`，调用 `chrome.tabs.reload` | 页面执行重载 |
| `execute_js` | `tab.evaluate` | 不发 `Runtime.evaluate`，调用 `chrome.scripting` | 获取到表达式返回值 |
| `capture_screenshot` | `tab.screenshot` | 不发 `Page.captureScreenshot`，执行 **激活-截图-恢复** 并且带 `try/finally` 强回切 | 获取合法的 PNG 图像字节 |
| `get_page_content` | `tab.evaluate` | 通过执行一段通用 DOM 内容获取 JS 代码 | 拿到合法的页面 Markdown 或 HTML |
| `probe_page_readiness` | `tab.evaluate` | 通过执行 Selector DOM 状态查询 JS 脚本 | 查询到元素就绪状态 |
| `query_elements` | `tab.evaluate` | 通过执行 DOM Selector 查询 JS 脚本 | 返回匹配 of 元素列表 |
| `set_file_input_files_by_selector` | `tab.uploadFile` | 不发一系列 DOM.querySelector 等，改用 **Ticket 校验中转 + 页面侧直接流式 Blob 直注** | 表单收到文件并生成上传预览 |

---

## 7. 范围边界与排他说明

> [!WARNING]
> **关于 `/playwright` CDP 路由的排他说明**：
>
> 鉴于本项目在 `native-only` 分支中已经彻底清除了 CDP 所有的直连通道，原有的 `/playwright/connect` 依靠暴露浏览器原生 CDP WebSocket 端口以进行直连的链路在正常情况下已不再可用。
>
> **降低复杂度，本设计规格明确声明【不覆盖 `/playwright` 路由及其控制指令】。** 建议将 `/playwright` 相关的历史残留端点进行安全隔离或在下一会话中彻底剥离废弃。

---

## 8. 验收与质量守门

1.  **小红书 `prepare_publish_post` 多图/大图（<= 5MB）上传预览（硬性第一验收指标）**：
    *   **步骤**：在 `normal` 模式下，传入 **多张大图（每张 <= 5MB）** 进行发布前图片准备。
    *   **成功标准**：内容脚本直接拉取 Blob，网页成功渲染出多图预览（DOM 内生成图像片段），且期间 **100% 绝对没有出现调试警告横幅**。
2.  **大文件与短视频上传兼容性（高级性能测试/可选验证项）**：
    *   **步骤**：传入 **10MB ~ 30MB 之间的短视频** 进行上传流程压力测试。
    *   **要求**：在性能日志中记录：实际文件大小、浏览器内存表现（利用 `performance.memory` 或系统监视器）以及注入时的最大响应延时。不作为本规格书第一阶段发版 of 硬阻断性指标。
3.  **安全隔离与运行时阻断验证**：
    *   **步骤**：打开一个非已注册适配站点的私密页面（如 `https://github.com`），从外部发起 `/evaluate` 请求。
    *   **成功标准**：后端路由在 `NativeBrowserRuntime` 白名单硬性阻断下，安全地拦截并返还 `security_violation` 错误，禁止向该网页派送任何控制脚本。
4.  **截图页面现场 try/finally 恢复现场验证**：
    *   **步骤**：打开两个不同的 Tab，在第二个 Tab 正被截图时，人为强行制造一个错误（如传入损坏的截图参数格式），测试后台截图逻辑中断。
    *   **成功标准**：截图报错，但浏览器活动标签页在 `finally` 块触发下 **100% 自动切回初始活动页面，没有改变用户的 Tab 活动现场**。
