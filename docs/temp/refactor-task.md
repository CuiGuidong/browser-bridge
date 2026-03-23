# 扩展架构重构任务清单

_本文档为下一步 AI Agent 接手开发时的行动指南。_

## 任务目标
将单体文件 `content.js` 拆分为 `content.js` (生命周期底座) 和 `adapters/x-adapter.js` (特定网站插件)，并废弃冗余的 `site-adapters.js`。

## 执行步骤

- [ ] **步骤 1：创建 X 适配器文件**
  - 在 `extension/` 目录下新建文件夹 `adapters/`。
  - 创建文件 `extension/adapters/x-adapter.js`。
  - 将目前 `content.js` 中的 `extractRichText`, `cleanXPrimaryText`, `extractXTimeline`, `detectXHomeFeedMode` 和 `xAdapter` 对象的定义**全部剪切**到 `x-adapter.js` 中。
  - 在 `x-adapter.js` 文件的最后一行添加注册逻辑：
    `window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];`
    `window.BrowserBridgeAdapters.push(xAdapter);`

- [ ] **步骤 2：净化核心底座 (`content.js`)**
  - 清理掉步骤 1 中被移走的 X 专属代码。
  - 在文件最顶部（或紧挨着日志打印）初始化全局注册表：`window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];`
  - 修改 `collectSnapshot` 函数，使其动态查找适配器：
    ```javascript
    function collectSnapshot() {
      const base = collectGenericSnapshot();
      // 遍历注册表寻找匹配当前域名的适配器
      const activeAdapter = window.BrowserBridgeAdapters.find(adapter => adapter.match());
      if (activeAdapter) {
        return activeAdapter.collect(base);
      }
      return base;
    }
    ```

- [ ] **步骤 3：修改 `manifest.json` 按需加载**
  - 修改 `content_scripts` 数组，分别注入插件和底座：
    ```json
    "content_scripts": [
      {
        "matches": ["*://*.x.com/*", "*://*.twitter.com/*"],
        "js": ["adapters/x-adapter.js"],
        "run_at": "document_idle"
      },
      {
        "matches": ["<all_urls>"],
        "js": ["content.js"],
        "run_at": "document_idle"
      }
    ]
    ```

- [ ] **步骤 4：严格的人机交互测试**
  - ⚠️ **严禁直接运行 Python 脚本测试！**
  - 提示人类用户：“请前往 chrome://extensions 重新加载扩展，然后切换到 X 长文章页面按下 F5 刷新。”
  - 等待人类确认后，再执行 `python3 skills/x-assistant/scripts/read_post.py "https://x.com/i/status/2035203452780138972"`。
  - 验证终端输出中是否包含 `[Image: URL]`。

- [ ] **步骤 5：清理历史遗留**
  - 测试通过后，彻底删除 `extension/site-adapters.js`。
  - 删除 `background.js` 中的 `importScripts('site-adapters.js');` 行。

- [ ] **步骤 6：收尾提交**
  - 确认无误后，提交 Git Commit，并删除本 `docs/temp/` 临时文件夹。
