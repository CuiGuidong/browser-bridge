# Browser Bridge

让 AI Agent 控制你真实浏览器（Chrome/Edge）的 HTTP API 桥。

## 目标

在**真实登录态、真实浏览器环境**下，帮助 AI Agent 完成简单网页操作：
- 访问链接、读取页面内容
- 点击、输入、表单提交
- 截图、执行 JS

核心原则：**账号安全优先于效率**，高风险动作需人工确认。

## 架构

```
OpenClaw / Agent
    ↓
Browser Bridge (HTTP API)
    ↓
CDP (Chrome DevTools Protocol)
    ↓
Real Chrome / Edge Browser
```

## 当前能力

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /tabs` | 列出浏览器 tab |
| `POST /open` | 打开新页面 |
| `POST /activate` | 切换 tab |
| `GET /page-info` | 获取页面 title/url |
| `GET /page-content` | 获取页面文本内容 |
| `POST /screenshot` | 截图 |
| `GET /query` | CSS 选择器查询 DOM |
| `POST /click` | 点击元素 |
| `POST /fill` | 输入文本 |
| `GET /wait` | 等待页面稳定 |

### Playwright 路径 (Path C)

复杂页面操作使用 Playwright attach：

| 端点 | 功能 |
|------|------|
| `POST /playwright/connect` | 连接 Playwright 到浏览器 |
| `POST /playwright/disconnect` | 断开连接 |
| `GET /playwright/pages` | 获取所有页面 |
| `POST /playwright/click` | Playwright 点击 |
| `POST /playwright/fill` | Playwright 填值 |
| `POST /playwright/evaluate` | 执行 JavaScript |
| `GET /playwright/wait-selector` | 等待元素出现 |

## 快速开始

### 1. 启动带 CDP 的浏览器

```bash
# Edge (macOS)
open -a Microsoft\ Edge --args --remote-debugging-port=9333

# Chrome
google-chrome --remote-debugging-port=9333
```

### 2. 启动 Bridge

```bash
cd bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python -m app.server
```

Bridge 监听 `http://127.0.0.1:17777`

API 文档：`http://127.0.0.1:17777/docs`

### 3. 调用示例

```bash
# 获取 tabs
curl http://127.0.0.1:17777/tabs

# 打开页面
curl -X POST http://127.0.0.1:17777/open -H "Content-Type: application/json" -d '{"url":"https://example.com"}'

# 点击元素
curl -X POST http://127.0.0.1:17777/click -H "Content-Type: application/json" -d '{"selector":"a","targetId":"xxx"}'
```

## 配置

修改 `app/config.py`：
- `CDP_HOST`: 浏览器 CDP 地址（默认 `host.orb.internal`）
- `CDP_PORT`: CDP 端口（默认 `9333`）
- `BRIDGE_PORT`: Bridge 服务端口（默认 `17777`）

## 安全边界

以下动作**必须人工确认**：
- 登录/登出、2FA/MFA、验证码
- 改密码、支付、发布内容
- 删除数据、授权第三方应用

## 扩展 (可选)

项目包含一个 Chrome/Edge 扩展作为轻量增强层：

```bash
cd extension
# 在 chrome://extensions 加载此目录
```

扩展提供：
- Popup 状态检查
- 快速页面操作
- Bridge 连接状态查看

## 技术栈

- Python 3.13+ (FastAPI + uvicorn)
- WebSocket (`websockets==16.0`)
- CDP (Chrome DevTools Protocol)

## License

MIT