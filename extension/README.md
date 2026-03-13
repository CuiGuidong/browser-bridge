# Browser Bridge Extension

Chrome/Edge 扩展，提供浏览器内快速操作入口。

## 安装

1. 打开 `chrome://extensions/`
2. 开启「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择 `extension` 目录

## 功能

- **Popup 状态检查**: 查看 bridge 连接状态
- **页面信息**: 获取当前页 title/url
- **页面内容**: 读取页面文本
- **元素点击**: CSS 选择器点击
- **元素输入**: CSS 选择器填值
- **元素查询**: CSS 选择器查找

## 使用

1. 先启动 bridge: `python -m app.server`
2. 加载扩展
3. 点击扩展图标查看状态
4. 在页面上右键 → 查看扩展选项或通过 popup 操作

## 文件结构

- `manifest.json` - 扩展配置
- `background.js` - 后台服务 worker
- `content.js` - 页面注入脚本
- `popup.html` / `popup.js` - 弹窗 UI