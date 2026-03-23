# Browser Bridge Extension

Chrome/Edge 扩展，提供浏览器内快速语义抓取与操作入口。它也是 Browser Bridge 系统实现高级内容理解（Path A）的核心基石。

## 架构：核心底座与插件注册模式

为了保证极高的维护性与对 AI Agent 的友好度，本扩展采取了**按需加载的插件注册制 (Plugin Registry Pattern)**：

- **`content.js`**: 通用的生命周期底座。它注入到 `<all_urls>`，负责监听页面变动、劫持网络请求探针、执行基础的文字快照，并将数据定时上报给 Bridge 服务端。它维护着全局注册表 `window.BrowserBridgeAdapters = []`。
- **`adapters/*.js`**: 网站专属适配器。它们通过 `manifest.json` 在特定的域名下被**优先注入**，执行极高难度的 DOM 解析任务（如 X 的富文本图文混排提取），并在文件末尾将自己挂载到全局注册表中。

### 如何添加新网站的支持？

假设你要添加对 YouTube 的支持：
1. 在 `adapters/` 目录下新建 `youtube-adapter.js`。
2. 实现带有 `id`, `match()`, `collect(baseSnapshot)` 的 Adapter 对象，并在文件尾部执行 `window.BrowserBridgeAdapters.push(youtubeAdapter);`。
3. 修改 `manifest.json` 的 `content_scripts`，将 `adapters/youtube-adapter.js` 匹配到 `*://*.youtube.com/*`，并**确保它放在 `content.js` 的配置之前**。

## 安装

1. 打开 `chrome://extensions/` 或 `edge://extensions/`
2. 开启「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目中的 `extension/` 目录

## ⚠️ 开发者必读 (修改测试铁律)

如果你修改了 `content.js` 或任何 `adapters/*.js` 文件：
1. 必须前往扩展管理页面点击**“重新加载 (Reload)”**。
2. 必须回到你要测试的目标网页上，按下 **F5 彻底刷新页面**（尤其是单页应用 SPA），否则页面依然运行的是旧缓存脚本！
3. 然后再运行你的 Python 验证脚本。

## 文件结构

- `manifest.json` - 扩展配置与权限声明
- `background.js` - 后台服务 Worker（仅做消息中转）
- `content.js` - 核心通用内容注入脚本（引擎）
- `adapters/` - 特定网站专属解析器存放目录
  - `x-adapter.js` - X/Twitter 深度解析器
- `popup.html` / `popup.js` - 弹窗 UI