# Native Messaging 无感控制架构（No-Debugger 升级）实施计划 (Historical / Superseded)

> [!IMPORTANT]
> **历史设计/实施过程产物 (Historical / Superseded)**
> 本文件是 `feature/native-messaging` 分支在迁移与双模式架构设计过程中的历史 spec/plan，仅用于记录设计背景、讨论线索和历史推演。
> **它不代表当前项目的最终架构事实**。关于项目的最新及正式事实，请以正式文档 [docs/architecture.md](file:///home/cuiguidong/workspace/personal/projects/Python/browser-bridge-project/docs/architecture.md) 以及实际运行代码为准。

> **给执行 Agent：** 请按任务逐项仔细执行，保持改动精准聚焦，并严格运行每一项列出的验证命令。只有当完成的项目变更达到“可独立解释、可独立回滚”的边界时，才在最终收尾阶段调用 `finalize-change`。本实施计划保持未暂存状态。

**目标：** 将 browser-bridge 底层的常规控制操作从 CDP 直连与 `chrome.debugger` 通道无缝迁移至 MV3 原生的 Extension API 与页面端直接流式拉取注入，彻底干掉浏览器顶部的安全警告调试横幅，同时保障极高安全性的非循环模块结构与带点边界的运行时主机白名单拦截。

**计划密度：** Detailed low-context

**实现思路：**
1. 后端彻底改发高层 Native 协议指令，全面覆盖 navigate, reload, evaluate, screenshot, upload 等常规调用；
2. 扩展在 `handleNativeCommand(msg)` 入口拦截高层指令，使用 `chrome.tabs` 与 `chrome.scripting` (world: 'MAIN') 在后台完全平替 CDP；
3. 大文件通过独立的 `upload_tokens.py` 模块提供“先校验、后消费”的 Ticket 签发，由内容脚本直接跨域 fetch 本地 Blob 进行 DOM 直注，彻底隔离并杜绝 Python 循环导入；
4. 物理权限级与**带点边界**的运行时白名单后缀匹配拦截，双闸并重，收敛安全受攻击面。

**技术栈：** Python 3.10+, FastAPI, Chrome Extension MV3 API, HTML5 DataTransfer API

**输入：** [.agents/specs/2026-05-24-native-messaging-no-debugger-design-spec.md](file:///home/cuiguidong/workspace/personal/projects/Python/browser-bridge-project/.agents/specs/2026-05-24-native-messaging-no-debugger-design-spec.md)

---

## 验收到验证矩阵

| 验收项 | 验证类型 | 证据目标 |
| --- | --- | --- |
| **微博/知乎常规读取无横幅** | 集成读取测试 | 运行 `python3 skills/weibo-assistant/scripts/read_post.py`，微博内容抓取 ok:true，且浏览器顶部 **100% 绝对没有调试横幅**。 |
| **小红书大图/多图上传预览（第一硬验收）** | 端到端文件注入 | 运行小红书 workflow 传入多张图片（每张 <=5MB），网页编辑器中成功展示图片预览 DOM，且 **100% 无横幅**。 |
| **非白名单/钓鱼网页后台控制硬性阻断** | 运行时安全阻断 | 尝试对非白名单（如 `github.com`）或伪装钓鱼域名（如 `evilweibo.com`）执行 evaluate 脚本，后端强行拦截并返回 403 阻断错误。 |
| **截图异常 finally 恢复现场** | 稳定性回弹测试 | 截图非活动 Tab 时故意抛错，活动标签页在 `finally` 块触发下 **100% 自动切回初始活动页面**，不改动用户 Tab 现场。 |
| **避开循环导入** | 静态模块完整性 | `bridge/app/server.py` and `bridge/app/native_browser_runtime.py` 均可正常被 Python 解释器导入而不报 any Circular Import 错误。 |

---

## 阶段 1：Git 状态剥离与双 Manifest 自动构建

### Task 1.1：剥离 manifest.json 版本追踪并定义双模板
**Purpose：** 取消 Git 对物理入口 `manifest.json` 的跟踪，防止开发期权限被误提交。

**Files：**
- Modify: `.gitignore`
- Create: `extension/manifest.prod.json` (生产模板)
- Create: `extension/manifest.dev.json` (开发模板)

**Steps：**
1.  [x] 在工作区根目录执行 Git 缓存移除命令：
    ```bash
    git rm --cached extension/manifest.json
    ```
2.  [x] 在 `.gitignore` 文件末尾追加一行：
    ```text
    extension/manifest.json
    ```
3.  [x] 复制现有的 `extension/manifest.json` 为 `extension/manifest.prod.json`：
    *   **修改**：物理移除 `"permissions"` 数组中的 `"debugger"`。
    *   **修改**：在 `"host_permissions"` 数组中追加：
        ```json
        "host_permissions": [
          "<all_urls>",
          "http://127.0.0.1:17777/*"
        ]
        ```
4.  [x] 复制 `extension/manifest.json` 为 `extension/manifest.dev.json`：
    *   **修改**：保留 `"debugger"`，并追加相同的 `"host_permissions"`。

**Acceptance：** `git status` 显示 `extension/manifest.json` 已被安全 untrack 并列入忽略，双 manifest 模板就绪。
**Verification：**
```bash
git status --short
```
预期：
`D extension/manifest.json` (在暂存区表现为删除)
`?? extension/manifest.prod.json`
`?? extension/manifest.dev.json`

---

### Task 1.2：重构扩展重载脚本支持 Manifest 自动加载
**Purpose：** 让热重载脚本自动根据开发态覆盖生成入口 `manifest.json`。

**Files：**
- Modify: `scripts/dev_reload_extension.sh`

**Steps：**
1.  [x] 在 `scripts/dev_reload_extension.sh` 执行实际同步和同步命令前，加入 Manifest 复制规则：
    *   如果 `extension/manifest.dev.json` 存在，强行将其拷贝为 `extension/manifest.json`：
        ```bash
        cp extension/manifest.dev.json extension/manifest.json
        ```
2.  [x] 确保脚本输出中有明确的 Manifest 复制日志。

**Acceptance：** 运行重载脚本时，`extension/manifest.json` 被自动创建且其内容与 `manifest.dev.json` 完全一致。
**Verification：**
```bash
./scripts/dev_reload_extension.sh
cat extension/manifest.json | grep "debugger"
```
预期：输出中包含 `"debugger"` 权限。

---

## 阶段 2：后端白名单机械聚合、注入与运行时硬拦截

### Task 2.1：在 SiteRegistry 中支持允许域名允许列表机械聚合
**Purpose：** 提供允许域名的 suffix match 机械匹配源。

**Files：**
- Modify: `bridge/app/sites/registry.py`

**Steps：**
1.  [x] 在 `registry.py` 中，定义 `get_allowed_hosts(self) -> list[str]` 方法：
    *   遍历已注册的所有 `site_module`，从 `site_module.hosts` 中聚合出所有的 hosts 并返回列表。
2.  [x] 编写静态 compile 测试以确保该方法可用。

**Acceptance：** 导入 `server.py` 中的全局 `site_registry` 实例并调用，能正常返回包含微博、小红书、知乎等已注册主机的域名列表。
**Verification：**
```bash
python3 -c "from bridge.app.server import site_registry; print(site_registry.get_allowed_hosts())"
```
预期：输出中包含 `['weibo.com', 'xiaohongshu.com', 'zhihu.com']` 等站点域名。

---

### Task 2.2：运行时白名单拦截与依赖注入重构
**Purpose：** 隔离并注入白名单检测，确保非白名单域名物理阻断。

**Files：**
- Modify: `bridge/app/config.py`
- Modify: `bridge/app/browser/cdp_runtime.py`
- Modify: `bridge/app/native_browser_runtime.py`
- Modify: `bridge/app/server.py`

**Steps：**
1.  [x] **在 `bridge/app/config.py` 中手动加载 `.env.local` 文件**：
    *   在 `config.py` 头部添加一个轻量级的文件解析函数，寻找工作目录或本模块上层目录下的 `.env.local` 文件。
    *   解析其中的 `DEVELOPMENT_MODE` 或其他配置，如果当前 `os.environ` 中不存在对应变量，则写入 `os.environ`。
    *   在 `config.py` 中公开定义 `DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"`。
2.  [x] 在 `cdp_runtime.py` and `native_browser_runtime.py` 中，升级构造函数 `__init__`：
    *   支持接收 `site_registry=None` 并保存在私有变量 `self._site_registry` 中。
3.  [x] 在 `server.py` 的初始化中，修改 `browser_runtime` 的实例化行：
    *   `browser_runtime = CdpRuntime(native_session_manager=native_session_manager, site_registry=site_registry)`
4.  [x] 在 `native_browser_runtime.py` 中，设计私有校验方法 `_assert_host_allowed(self, target_id)`：
    *   通过 `self.get_page_info(target_id)` 提取当前 Tab 的真实 URL。
    *   **开发模式判断对齐**：使用 `bridge.app.config.DEVELOPMENT_MODE` 进行判断：若为 `True`，豁免拦截（打印 warning 即可）。
    *   若为生产模式，解析 URL 的 `hostname`。**执行严密的带点边界后缀比对**：
        ```python
        is_allowed = False
        for allowed_host in self._site_registry.get_allowed_hosts():
            if hostname == allowed_host or hostname.endswith("." + allowed_host):
                is_allowed = True
                break
        if not is_allowed:
            raise HTTPException(status_code=403, detail="security_violation: Host is not in the registered site allowlist")
        ```
        这彻底防止了形如 `evilweibo.com`、`fakegoogle.com` 等钓鱼/钓鱼域名欺骗绕过白名单限制。
5.  [x] **全调用面覆盖**：在所有会下发 `tab.evaluate`、`tab.screenshot`、`tab.uploadFile` 的底层方法（包括 `execute_js`, `capture_screenshot`, `set_file_input_files_by_selector`, `get_page_content`, `probe_page_readiness`, `query_elements`）的首行，**均强行硬性调用** `self._assert_host_allowed(target_id)` 执行安全防御。

**Acceptance：** 尝试对不受支持的测试域名或伪造域名发送 evaluate 脚本时，直接抛出 `security_violation` 异常并被拦截。
**Verification：**
*   编译 Python 代码。
*   **白名单正常阻断测试**：使用 Bridge 接口 `/open` 打开不受支持的主机（例如 `https://github.com`）获取一个 targetId，随后向该 targetId 发起 `/evaluate` 请求。
    *   预期：请求失败并返回 403 阻断错误（`security_violation`）。
*   **钓鱼域名阻断测试**：使用 Bridge 接口 `/open` 打开钓鱼域名（例如 `https://evilweibo.com`）获取一个 targetId，随后向该 targetId 发起 `/evaluate` 请求。
    *   预期：**请求同样必须被硬性拒绝并返回 403 阻断错误！**

---

## 阶段 3：独立 Token 签发模块与本地中转（先校验后消费，防预检烧毁）

### Task 3.1：建立独立 upload_tokens 模块并注册安全中转端点
**Purpose：** 隔离 Token 内存数据结构，彻底杜绝 `server.py` 和 `native_browser_runtime.py` 之间的循环依赖，并提供“先校验、后消费”的防御逻辑。

**Files：**
- Create: `bridge/app/upload_tokens.py` (独立自包含模块)
- Modify: `bridge/app/server.py` (只注册 HTTP 端点，不持有 Map)

**Steps：**
1.  [x] 创建全新文件 `bridge/app/upload_tokens.py`，实现线程安全的 Token 签发、获取与销毁：
    ```python
    import threading
    import time
    import secrets

    _upload_tokens = {}
    _upload_tokens_lock = threading.Lock()

    def issue_upload_token(path, size, mime, session_id, tab_id, expected_origin):
        file_id = secrets.token_hex(16)
        with _upload_tokens_lock:
            _upload_tokens[file_id] = {
                "path": path,
                "size": size,
                "mime": mime,
                "session_id": session_id,
                "tab_id": tab_id,
                "expected_origin": expected_origin,
                "created_at": time.time()
            }
        return file_id

    def get_upload_token(file_id):
        # 仅读取校验，不执行 pop/销毁
        with _upload_tokens_lock:
            return _upload_tokens.get(file_id)

    def remove_upload_token(file_id):
        # 显式移除销毁
        with _upload_tokens_lock:
            _upload_tokens.pop(file_id, None)
    ```
2.  [x] 在 `bridge/app/server.py` 中导入上述三个方法，并注册 `/dev/file/get`：
    *   **限制**：核验请求 IP 必须为 `127.0.0.1`，否则直接 403。
    *   **CORS 预检与 X-Browser-Bridge-Tab-Id 头部支持**：
        ```python
        # OPTIONS 与 GET 均强加
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "X-Browser-Bridge-Tab-Id, X-Browser-Bridge-Session-Id"
        response.headers["Cache-Control"] = "no-store"
        ```
    *   **校验与销毁流程重构**：
        *   首先调用 `get_upload_token(id)` 只读获取凭证（不销毁）。
        *   比对 `createdAt` 超时（30秒内）。
        *   比对 Request Header 中携带的 `X-Browser-Bridge-Tab-Id` 与绑定 `tab_id` 一致。
        *   比对 `Origin` 头是否与 `expected_origin` 完全一致。
        *   校验文件大小不超过 **50 MB**。
        *   **安全消费时机**：仅在上述所有校验成功通过、**即将向浏览器返回数据响应流的第一字节瞬间**，再调用 `remove_upload_token(id)` 执行物理销毁！这彻底防止了因为预检错误、误配置或跨域 OPTIONS 握手将 Token 错误烧毁的稳定性故障。
        *   使用 `FileResponse` 流式安全发送该文件二进制流。

**Acceptance：** 模块结构清爽，端点跨域校验极其扎实，无任何循环导入警告。
**Verification：**
*   解释器导入验证：
    ```bash
    python3 -c "import bridge.app.server; import bridge.app.native_browser_runtime"
    ```
    预期：顺利导入，退出码 0，无任何 Circular Import 报错。

---

## 阶段 4：扩展常规指令原生平替与 DOM 页面侧 Blob 直注

### Task 4.1：重构 background.js 实现新高层协议原生平替
**Purpose：** 去除 attach debugger 操作，在正确的 Native 命令入口中用纯 MV3 原生 API 实现常规控制。

**Files：**
- Modify: `extension/background.js`

**Steps：**
1.  [x] **核心命令入口纠偏**：定位 `background.js` 中的 **`handleNativeCommand(msg)`** 函数。
2.  [x] 在 `handleNativeCommand(msg)` 函数内、**在 `method.startsWith('debugger.')` 判定分支之前**，拦截并添加对以下 `tab.*` 高层指令的响应处理（**不要**错误地加到 `chrome.runtime.onMessage` 内部，那是内容脚本消息接收区）：
    *   `tab.navigate` -> `await chrome.tabs.update(params.tabId, { url: params.url })`。
    *   `tab.reload` -> `await chrome.tabs.reload(params.tabId, { bypassCache: params.ignoreCache !== false })`。
    *   `tab.screenshot` -> **实现 active tab 切换与 try/finally 强回切现场恢复状态机**。
    *   `tab.evaluate` -> **使用 `chrome.scripting.executeScript` 配合 `world: 'MAIN'` 并用 `await` 执行 eval(expr)**。统一失败返回标准的 error envelope。
    *   `tab.uploadFile` -> 直接将携带 tabId, sessionId 属性的极轻量 `files` 转发给 `content.js`。
3.  [x] **收窄 attach debugger 时机**：仅当 method 明确为 `debugger.*` 且不是上述高层命令时，才执行 attach，常规状况下绝对不启动 debugger。

**Acceptance：** `background.js` 完美分发并处理新 Native 指令，彻底隔离横幅。
**Verification：** 静态运行编译，保证扩展代码无任何语法错误。

---

### Task 4.2：在 content.js 中实现跨域直接 Blob fetch 与 DOM 注入
**Purpose：** 让页面侧在真实的 DOM 上下文中直接拉取本地临时 Ticket 文件并注入 input，避开 Base64 开销。

**Files：**
- Modify: `extension/content.js`

**Steps：**
1.  [x] 在内容脚本的 `chrome.runtime.onMessage` 中，增加 `domFileUpload` 的 action 响应：
    *   寻找 `payload.selector` 目标元素。
    *   遍历 `payload.files`：
        *   **直接发起网页端的跨域 `fetch` 请求**，硬性传递 tab-id 与 session-id 校验头：
            ```javascript
            const response = await fetch(`http://127.0.0.1:17777/dev/file/get?id=${encodeURIComponent(f.fileId)}`, {
              headers: {
                "X-Browser-Bridge-Tab-Id": String(f.tabId),
                "X-Browser-Bridge-Session-Id": String(f.sessionId)
              }
            });
            ```
        *   拉取完毕后使用 `await response.blob()` 获取原生 Blob 字节对象。
        *   使用 `new File([blob], f.name, {type: blob.type})` 实例化 W3C 标准 File 对象。
        *   利用 `new DataTransfer()` 构造 `FileList`，并强行塞入 input 框中，触发 change 与 input 原生事件。

**Acceptance：** 扩展下发上传指令后，网页端的 File Input 框被自动注入该本地文件。

---

## 阶段 5：后端指令分发路由全部 debugger.send 替换与集成验证

### Task 5.1：全面替换 native_browser_runtime.py 中所有的 debugger.send 调用（极其核心）
**Purpose：** 100% 覆盖并重塑所有的 debugger.send 操作，彻底在常规控制链路中消灭调试横幅，并补齐白名单校验和 Ticket 构造细节。

**Files：**
- Modify: `bridge/app/native_browser_runtime.py`

**Steps：**
1.  [x] **替换 1：_try_reuse_tab 导航平替**
    *   定位 `_try_reuse_tab` 中使用 `self._cmd("debugger.send", {"command": "Page.navigate"})` 的地方。
    *   改用高层的 `tab.navigate` 与 `tab.evaluate`，拒绝任何 Page.enable。
2.  [x] **替换 2：navigate_tab 导航平替**
    *   定位 `navigate_tab` 中的 CDP 导航调用。
    *   改发高层的 `self._cmd("tab.navigate", {"tabId": tab_id, "url": url})`。
3.  [x] **替换 3：_wait_for_page_load 轮询就绪平替**
    *   定位使用 `self._cmd("debugger.send", {"command": "Runtime.evaluate", "expression": "document.readyState"})` 的轮询。
    *   改用高层的 `self._cmd("tab.evaluate", {"tabId": tab_id, "expression": "document.readyState"})`。
4.  [x] **替换 4：reload_tab 刷新平替**
    *   定位 `reload_tab` 中的 `Page.reload` CDP。
    *   改发高层的 `self._cmd("tab.reload", {"tabId": tab_id, "ignoreCache": True})`。
5.  [x] **替换 5：execute_js 执行脚本平替**
    *   定位 `execute_js` 中的 `Runtime.evaluate`。
    *   改发高层的 `self._cmd("tab.evaluate", {"tabId": tab_id, "expression": expression})`。
6.  [x] **替换 6：capture_screenshot 截图平替**
    *   定位 `capture_screenshot` 中的 `Page.captureScreenshot`。
    *   改发高层的 `self._cmd("tab.screenshot", {"tabId": tab_id, "format": fmt})`。
7.  [x] **替换 7：get_page_content 页面提取平替**
    *   定位使用 `Runtime.evaluate` 执行提取内容的 JS。
    *   改用高层的 `tab.evaluate` 执行脚本，**并且首行补齐** `self._assert_host_allowed(target_id)` 校验。
8.  [x] **替换 8：probe_page_readiness 就绪探测平替**
    *   定位 `probe_page_readiness` 中的 `Runtime.evaluate` 探测。
    *   改发高层的 `tab.evaluate`，**并且首行补齐** `self._assert_host_allowed(target_id)` 校验.
9.  [x] **替换 9：query_elements 元素查询平替**
    *   定位 `query_elements` 中执行 DOM 查找的 `Runtime.evaluate`。
    *   改发高层的 `tab.evaluate`，**并且首行补齐** `self._assert_host_allowed(target_id)` 校验。
10. [x] **替换 10：set_file_input_files_by_selector 文件上传平替**
    *   彻底废弃使用 `DOM.enable` / `DOM.getDocument` / `DOM.querySelector` / `DOM.setFileInputFiles` / `DOM.resolveNode` 的全套 CDP 直连。
    *   **预期来源构造（实现细节）**：
        *   调用 `self._find_tab_by_id(tab_id)` 获取 URL，调用 urlparse 强行解析拼装出 `scheme://host[:port]` 格式作为 `expected_origin`。
        *   调用 `self._sid()` 作为 `sessionId`。
        *   **首行补齐** `self._assert_host_allowed(tab_id)` 校验。
        *   遍历 `files`：从 **独立的 `upload_tokens.py` 模块** 调用 `issue_upload_token(path, size, mime, sessionId, tab_id, expected_origin)` 生成 fileId。
        *   向下发送高层命令：
            ```python
            self._cmd("tab.uploadFile", {
                "tabId": tab_id,
                "sessionId": self._sid(),
                "selector": selector,
                "files": [{"name": os.path.basename(f), "fileId": fid} for f, fid in zip(files, file_ids)]
            })
            ```

**Acceptance：** 后端发送 of 命令全部升级为新系统高层协议，且能够正确签发和安全路由 Ticket。
**Verification：**
1.  **静态编译无语法错误**。
2.  **健康检查**：`/health` 返回正常。
3.  **微博/知乎读取基线测试（100% 绝对无横幅核心验收）**：
    ```bash
    python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'
    ```
    预期：微博读取 ok:true，期间 Edge/Chrome 浏览器顶部 **100% 绝对没有任何警告调试横幅**。
4.  **小红书多图上传预览回归（硬性验收第一优先级）**：
    *   准备多张小图（<=5MB），运行小红书 workflow。
    *   预期：上传成功，编辑器中成功展现图片预览 DOM，且 100% 无横幅！
5.  **大视频压力兼容性测试**：
    *   传入 20MB 视频文件，记录系统指标与执行日志。
