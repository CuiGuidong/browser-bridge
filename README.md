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
Path A: Extension 语义增强
Path B: CDP (Chrome DevTools Protocol)
Path C: Playwright attach
    ↓
Real Chrome / Edge Browser
```

## 当前能力

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /version` | 浏览器/CDP 版本信息 |
| `GET /tabs` | 列出浏览器 tab |
| `POST /open` | 打开新页面 |
| `POST /activate` | 切换 tab |
| `POST /evaluate` | 在指定 tab 执行 JS |
| `GET /page-info` | 获取页面 title/url |
| `GET /page-content` | 获取页面文本内容 |
| `GET /probe-readiness` | 页面就绪探针 |
| `POST /read-page` | 带就绪判断的页面读取 |
| `POST /screenshot` | 截图 |
| `GET /query` | CSS 选择器查询 DOM |
| `POST /click` | 点击元素 |
| `POST /fill` | 输入文本 |
| `GET /wait` | 等待页面稳定 |

### Extension 路径 (Path A)

| 端点 | 功能 |
|------|------|
| `POST /extension/report` | 扩展上报页面语义信号 |
| `GET /extension/state` | 查看最近扩展状态 |

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

**非常重要：Bridge 必须依赖宿主机浏览器开启 CDP 端口运行！**

```bash
# Edge (macOS)
open -a "Microsoft Edge" --args --remote-debugging-port=9333

# Chrome (macOS)
open -a "Google Chrome" --args --remote-debugging-port=9333

# Chrome (Linux)
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

Bridge 默认监听 `http://127.0.0.1:17777`

API 文档：`http://127.0.0.1:17777/docs`

### 2.1 可选：注册 systemd 系统服务（sudo）

```bash
cd bridge/systemd
bash install-system-service.sh
```

常用管理命令：

```bash
# 查看状态
bash bridge/systemd/browser-bridgectl.sh status

# 重启
bash bridge/systemd/browser-bridgectl.sh restart

# 查看最近日志
bash bridge/systemd/browser-bridgectl.sh logs 120
```

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

修改 `bridge/app/config.py`：
- `BRIDGE_HOST` / `BRIDGE_PORT`（默认 `127.0.0.1:17777`）
- `CDP_BASE_URL`（默认 `http://127.0.0.1:9333`）
- `CDP_HOST_HEADER`（默认 `127.0.0.1:9333`）
- `CDP_WS_BASE_URL`（默认 `ws://127.0.0.1:9333`）

## ⚠️ 常见排障与避坑 (Troubleshooting)

1. **服务连通性报错 / Connection Refused (HTTP 500)**
   * **症状**：AI Agent 调用 `open` 或 `read_page` 脚本时，一直循环报错甚至直接抛出 `Connection refused` 500 错误。
   * **根因**：**宿主机的浏览器没有启动，或者没有开启调试端口！** AI Agent 常常误以为是 bridge 的代码写错了或扩展坏了。
   * **解决**：立即让用户在宿主机运行启动命令：`open -a "Microsoft Edge" --args --remote-debugging-port=9333`。
2. **更多深度技术坑点**：请阅读 `docs/implementation-guide.md`。

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
- 页面语义信号上报（已实现 X adapter，支持时间线与多媒体图文结构化抽取）

## X 增强（进行中）

- 时间线读取（`/home`、`/search`、`/explore`）
- `read-page` 中对 X 时间线的轻量滚动预加载（Light Scroll）
- `skills/x-assistant/` 下提供 `search.py` / `feed.py` / `read_post.py` 脚本，支持广告过滤与降噪
- Home Feed 支持区分 `for_you` / `following`（中英文标签兼容）
- Home Feed 默认双流读取（为你推荐 + 正在关注）各 20 条，可配置条数与连续读取
- 标签复用优先：优先复用同域 tab，避免每次操作新开标签页

## 技术栈

- Python 3.13+ (FastAPI + uvicorn)
- WebSocket (`websockets==16.0`)
- CDP (Chrome DevTools Protocol)

## License

MIT
