# Browser Bridge Extension

Chrome/Edge 扩展，负责页面内常驻执行、站点语义读取、站点语义动作，以及和 Bridge 的主动 RPC 通信。

## 当前分工

- `content.js`
  - 页面内常驻执行者
  - 采集通用快照
  - 匹配当前页面 adapter
  - 分发 `capabilities / probe_ready / read / act / verify`
  - 通过 `background.js` 与 Bridge 通信

- `background.js`
  - 只负责和 Bridge 转发消息
  - 不再承担站点语义采集与页面内动作执行

- `adapters/*.js`
  - 站点专属语义能力实现
  - 当前主实现是 `x-adapter.js`

## Adapter 接口规范

新站点 adapter 至少应实现：

- `collect(baseSnapshot)`
- `id`
- `match()`
- `getPageType()`
- `capabilities()`
- `probeReady(context)`
- `read(kind, params, context)`
- `act(kind, params, context)`
- `verify(kind, params, context, actionResult)`

说明：

- `collect(baseSnapshot)` 仍然是当前正式运行时必需接口，因为 `content.js` 会在快照/上报链路直接调用它
- `probeReady/read/act/verify` 是主动 RPC 模型下的正式接口
- 也就是说，新站点 adapter 不能只实现主动接口而不实现 `collect()`

## 如何添加新网站支持

假设你要添加微博：

1. 新建 `adapters/weibo-adapter.js`
2. 实现上面的完整 adapter 接口
3. 在文件尾部执行：
   `window.BrowserBridgeAdapters.push(weiboAdapter);`
4. 修改扩展加载配置，确保该 adapter 会在微博页面注入
   - 当前落点是 `extension/manifest.json`
5. 完成后再补 Bridge 侧的：
   - `bridge/app/sites/weibo/models.py`
   - `bridge/app/sites/weibo/site.py`
   - `bridge/app/server.py` 的注册入口

## 安装

1. 打开 `chrome://extensions/` 或 `edge://extensions/`
2. 开启「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目中的 `extension/` 目录

## ⚠️ 开发者必读 (修改测试铁律)

如果你修改了 `content.js` 或任何 `adapters/*.js` 文件：
1. 运行 `./scripts/dev_reload_extension.sh`。
2. 该脚本会同步扩展文件、触发扩展自重载，并刷新目标站点页面。
3. 然后再运行对应 Python 验证脚本。

## 文件结构

- `manifest.json` - 扩展配置与权限声明
- `background.js` - 后台服务 Worker（只做桥接转发）
- `content.js` - 页面内常驻运行时与 RPC 分发器
- `adapters/` - 特定网站专属解析器存放目录
  - `x-adapter.js` - X/Twitter 站点语义实现
- `popup.html` / `popup.js` - 弹窗 UI
