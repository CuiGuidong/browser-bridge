# Browser Bridge 扩展架构重构计划 (Plugin Registry Pattern)

_状态：草案 / 待执行_

## 1. 重构背景
目前 `extension/content.js` 既负责全局的 DOM 生命周期管理（注入探针、MutationObserver 监听），又硬编码了上百行的 X (Twitter) 专属解析逻辑（图文交叉提取）。
这导致：
1. 文件过于庞大，不利于 AI Agent 维护，浪费 Token。
2. 缺乏隔离性，修改 X 的逻辑容易导致核心底座崩溃。
3. 扩展性差，难以优雅地接入新的网站（如 YouTube, 小红书）。

## 2. 目标架构设计：依赖反转与按需加载
将系统一分为二：
- **核心生命引擎 (`content.js`)**：只负责基础的页面状态判断、网络心跳和统一上报。不包含任何特定网站的逻辑。
- **独立网站插件 (`adapters/*.js`)**：每个网站的专属 DOM 提取逻辑作为一个独立对象存在，并通过全局数组向底座“注册”自己。

### 核心机制：
1. **全局注册表**：
   在 `content.js` 最顶部定义 `window.BrowserBridgeAdapters = [];`。
2. **插件注册**：
   在 `adapters/x-adapter.js` 底部执行 `window.BrowserBridgeAdapters.push(xAdapter);`。
3. **按需注入 (`manifest.json`)**：
   利用 Chrome Content Scripts 的 URL 匹配功能：
   - `<all_urls>` -> 注入 `content.js`
   - `*://*.x.com/*` -> 注入 `adapters/x-adapter.js` (并在 `content.js` 之前或之后加载，但由于共享 window，只要在 `MutationObserver` 触发时能读到即可)。
   *(注：推荐将 adapter 先行加载，确保底座启动时立即能获取到字典。)*

## 3. 预期成果
重构后，增加一个新网站的支持，只需要新建一个不到 100 行的 `adapters/new-site.js` 并修改 `manifest.json` 即可，**绝对不需要修改 `content.js`**，彻底实现 0 耦合。
