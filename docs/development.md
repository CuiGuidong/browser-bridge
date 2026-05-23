# 开发指南

本指南面向需要在本地搭建和开发 Browser Bridge 的开发者或 Agent。

本机个性化配置（端口、代理、宿主机路径等）见 `LOCAL_DEV.md`。

## 前置条件

- Python 3.10+
- Chrome 或 Edge 浏览器（支持 CDP）
- 浏览器扩展加载能力（开发者模式）

## 项目结构

```text
bridge/app/          # HTTP API 服务（FastAPI）
extension/           # 浏览器扩展（Manifest V3）
skills/              # 面向 Agent 的站点 skill 脚本
docs/                # 项目文档
harness/             # Agent 协作层（约束、任务、验证）
temp/                # 临时计划与跨项目合同
scripts/             # 开发辅助脚本
tests/               # 测试
```

## 安装与启动

### 1. 启动带 CDP 的浏览器

```bash
# macOS — Edge
open -a "Microsoft Edge" --args --remote-debugging-port=9222

# macOS — Chrome
open -a "Google Chrome" --args --remote-debugging-port=9222

# Linux — Chrome
google-chrome --remote-debugging-port=9222
```

默认 CDP 端口为 `9222`。如本地端口被占用，可通过环境变量覆盖：

```bash
export CDP_PUBLIC_HOST=127.0.0.1
export CDP_CONNECT_HOST=127.0.0.1
export CDP_PORT=9222
```

### 2. 启动 Bridge

```bash
cd bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python -m app.server
```

Bridge 默认监听 `http://127.0.0.1:17777`，可通过 `BRIDGE_HOST` 和 `BRIDGE_PORT` 环境变量覆盖。

交互式文档：`http://127.0.0.1:17777/docs`

### 3. 加载扩展

在 `chrome://extensions` 或 `edge://extensions` 中开启开发者模式，加载 `extension/` 目录。

## 验证方式

### 健康检查

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

### 基线验证（微博单帖读取）

```bash
python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'
```

基线验证确认：Bridge 在线 → 扩展与浏览器通信正常 → adapter 命中 → 图片缓存链路正常。

### Python 编译检查

```bash
env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/server.py bridge/app/cdp_service.py bridge/app/browser/cdp_runtime.py
```

## 开发工作流

### 修改扩展代码后

1. 修改 `extension/` 下的文件
2. 运行 `./scripts/dev_reload_extension.sh`（同步到宿主机目录、触发扩展自重载、刷新目标站点页面）
3. 验证至少一个站点语义读取

### 修改 Bridge 代码后

1. 修改 `bridge/app/` 下的文件
2. 重启 Bridge 服务（`sudo systemctl restart browser-bridge.service` 或手动重启）
3. 运行健康检查

### 新增站点

按 `docs/new-site-adaptation-guide.md` 的 SOP 推进：

1. adapter：`extension/adapters/<site>-adapter.js`
2. 站点模块：`bridge/app/sites/<site>/`
3. 注册：`bridge/app/server.py`
4. workflow：`bridge/app/sites/<site>/workflows/`
5. skill（可选）：`skills/<site>-assistant/`

只读站点可直接继承 `bridge/app/sites/read_only_site.py` 的 `ReadOnlySite` 基类。

## 调试入口

| 接口 | 用途 |
|------|------|
| `/health` | Bridge 健康状态 |
| `/tabs` | 当前浏览器标签页列表 |
| `/extension/state` | 扩展最近上报状态 |
| `/site/capabilities?site=<site>&targetId=<id>` | 站点能力探测 |

完整接口参考见 `docs/api-reference.md`。

## 测试页面

| 站点 | URL |
|------|-----|
| X 单帖 | `https://x.com/billtheinvestor/status/2038173185875775987` |
| 小红书单帖 | `https://www.xiaohongshu.com/explore/69c6469e000000001d01d9d1` |
| 微博单帖 | `https://weibo.com/6105713761/Qy80W8wXc` |
| 微博首页 | `https://weibo.com/` |
| 微博热搜 | `https://weibo.com/hot/search` |
