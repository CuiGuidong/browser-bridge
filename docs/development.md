# 开发指南

本指南面向需要修改 Browser Bridge 代码的开发者或 Agent，覆盖开发工作流、调试方法和关键避坑点。

普通用户安装入口见：

- [README.md](../README.md)
- [installation.md](installation.md)

本机个性化配置（端口、代理、宿主机路径等）见 `LOCAL_DEV.md`。

## 前置条件

- Python 3.10+
- Chrome 或 Edge 浏览器（支持加载扩展，且已建立 Native Messaging 连接）
- 浏览器扩展加载能力（开发者模式）

## 项目结构

```text
bridge/app/          # HTTP API 服务（FastAPI）
extension/           # 浏览器扩展（Manifest V3）
skills/              # 面向 Agent 的站点 skill 脚本
docs/                # 项目文档
agents/             # Agent 协作层（约束、任务、验证）
temp/                # 本地临时材料与运行时审计日志
scripts/             # 开发辅助脚本
tests/               # 测试
```

## 安装与启动

### 1. 启动浏览器

正常启动 Chrome 或 Edge 即可，**无需** `--remote-debugging-port` 参数。

### 2. 安装 Native Host

```bash
# 查看扩展 ID（在 edge://extensions 或 chrome://extensions 中）
./scripts/install-native-host.sh <extension-id>
```

该脚本将 native host manifest 安装到系统目录，使浏览器扩展能通过 Native Messaging 与 Bridge 通信。

Windows + WSL 开发时不要使用这个 Linux/macOS shell 脚本安装 Windows 侧 Native Host。先运行：

```bash
./scripts/setup_wsl.sh
```

再按脚本输出在 Windows PowerShell 中执行：

```powershell
powershell -ExecutionPolicy Bypass -File "<windows-path>\install-native-host.ps1" `
  -ExtensionId "<extension-id>" `
  -Browser both `
  -BridgeUrl "http://127.0.0.1:17777"
```

### 3. 启动 Bridge

```bash
cd bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python -m app.server
```

Bridge 默认监听 `http://127.0.0.1:17777`，可通过 `BRIDGE_HOST` 和 `BRIDGE_PORT` 环境变量覆盖。

交互式文档：`http://127.0.0.1:17777/docs`

### 4. 加载扩展

在 `chrome://extensions` 或 `edge://extensions` 中开启开发者模式，加载 `extension/` 目录。扩展启动后会自动通过 Native Messaging 连接 Bridge。

## 开发心智模型

本项目不是纯代码项目。真实运行链路涉及 Python 代码、扩展代码、浏览器标签页状态、宿主机系统服务和登录态。

**先怀疑宿主边界，再怀疑代码。** 看到以下现象时，不要立即改代码：

- `Failed to open post page`
- 明明打开了页面，但拿到骨架页或上一页内容
- `extension command timed out`
- 本地服务看起来"离线"
- 沙箱失败但用户说宿主机同命令成功

高频原因：浏览器没开、Native Session 未连接（例如扩展未加载或 Native Host 未安装）、扩展没重载、页面没刷新、沙箱看不到宿主浏览器。

Windows + WSL 下尤其注意：

- 正式 Edge profile 的扩展 ID 才能写入 Native Host manifest；临时 profile 跑通不代表正式浏览器已接入。
- 如果沙箱里 `curl 127.0.0.1:17777` 失败，但真实 WSL shell 成功，应按宿主侧结果判断 Bridge 状态。
- Windows Native Host 应由 Windows 浏览器直接启动 Windows 可执行文件，再通过 HTTP 连接 WSL Bridge；不要用 `.cmd` 或 `wsl.exe` 转发 Native Messaging stdin/stdout。

## 验证方式

### 健康检查

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

### 基线验证（微博单帖读取）

```bash
python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'
```

基线验证确认：Bridge 在线 → 扩展与浏览器通信正常 → adapter 命中 → 图片缓存链路正常。如果基线失败，不要先在站点 DOM 逻辑上绕圈。

### Python 编译检查

```bash
env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/server.py bridge/app/browser/cdp_runtime.py bridge/app/native_browser_runtime.py bridge/app/native_session_manager.py bridge/app/native_host_shim.py
```

### 调试入口

| 接口 | 用途 |
|------|------|
| `/health` | Bridge 健康状态 |
| `/tabs` | 当前浏览器标签页列表 |
| `/extension/state` | 扩展最近上报状态 |
| `/site/capabilities?site=<site>&targetId=<id>` | 站点能力探测 |

完整接口参考见 `docs/interfaces.md`。

## 开发工作流

### 修改扩展代码后

1. 修改 `extension/` 下的文件
2. 运行 `./scripts/dev_reload_extension.sh`
   - 该脚本执行三步原子操作：① 同步文件到宿主机扩展目录 ② 调用 Bridge API 触发扩展自重载 ③ 刷新目标站点页面
   - **不要拆分这三步**，不要跳过同步直接重载
   - **不要请求用户手动重载**——脚本已自动完成全部操作
   - 如果脚本超时或失败，先检查 bridge 是否在线（`curl --noproxy '*' -sS http://127.0.0.1:17777/health`），再检查扩展 Service Worker 状态
3. 验证至少一个站点语义读取

**铁律：** 扩展重载不等于旧标签页里的页面脚本自动更新。旧页面可能仍在运行旧版 `content.js`，会制造"明明改对了，测试还失败"的假象。脚本已处理页面刷新，但如果验证仍失败，手动刷新目标页面后重试。

### 修改 Bridge 代码后

1. 修改 `bridge/app/` 下的文件
2. 重启 Bridge 服务（`sudo systemctl restart browser-bridge.service` 或手动重启）
3. 运行健康检查

不重启会导致 curl 仍在访问旧版逻辑。

### 新增站点

按 `docs/new-site-adaptation-guide.md` 的 SOP 推进。基本落点：

1. adapter：`extension/adapters/<site>-adapter.js`
2. 站点模块：`bridge/app/sites/<site>/`
3. 注册：`bridge/app/server.py`
4. workflow：`bridge/app/sites/<site>/workflows/`
5. skill（可选）：`skills/<site>-assistant/`

只读站点可直接继承 `bridge/app/sites/read_only_site.py` 的 `ReadOnlySite` 基类。

#### Adapter 开发要点

- 先做 `match()` / `getPageType()` / `probeReady()`，再做读取，最后做动作
- 不要先写 workflow，更不要先写高风险动作
- 每个状态变更动作必须有 `verify()`
- SPA 中过于激进的可见性检查可能误杀真实内容（X 的图片、长文块、懒加载内容）
- ready 判断不能只看 `document.readyState`，还需确认目标内容容器真正到位

#### 扩展 RPC 约束

- 扩展主动 RPC 命令**必须带目标页约束**（`targetUrl`），不能做成"任意 tab 抢单"
- 当前匹配规则：规范化后的 `exact_url`，仅 X 额外支持 `x_status_id`
- `content.js` 是页面内实际执行者；页面没刷新 → 旧 content script → `extension command timed out`

## 状态变更动作规则

所有状态变更动作（关注/取关、书签增删等）至少需要：

- `before`：执行前状态
- `changed`：是否变更
- `verified`：页面内校验
- `after`：执行后状态

其他要求：

- 必须有节流（Bridge 已对状态变更做低频节流）
- 必须写审计日志（当前写入 `temp/x-state-actions.jsonl`）
- 找不到目标或按钮时**宁可报错，不要猜**

## 什么时候不应该做 Bridge workflow

以下任务不建议做成 workflow，应交给 skill 编排原子能力：

- "整理我的书签"
- "根据内容质量帮我清理关注列表"
- "看完这条帖子后，如果作者值得关注就关注"

判断标准：任务规则是否开放、是否依赖上下文。固定流程 → workflow，开放决策 → skill。

## 调试方法

### 推荐调试顺序

链路失败时按以下顺序定位，不要先改业务代码：

1. 浏览器是否启动，Native Session 是否已连接（健康检查 `/health` 返回 `nativeSession: connected`）
2. Bridge `/health` 是否正常，是否最新代码并已重启
3. 扩展是否已重载，目标页面是否已刷新，`/extension/state` 是否有最近上报
4. `/tabs` 能否看到目标页，`/site/capabilities` 是否命中正确页面
5. `/site/read` 或 `/site/action` 返回结果，错误在 Bridge、扩展还是目标页匹配阶段

### Workflow 标签页策略

- 默认允许新开临时标签页
- 标签页达到上限（当前 `30`）时强制复用同站点标签页
- workflow 结束后关闭本次新开的临时标签页
- 返回 `targetId: null` 通常表示临时页已关闭，是正常现象
- 传入 `targetId` 时，workflow 仍会将该 tab 导航到目标 URL

### 常见问题

| 现象 | 优先怀疑 |
|------|----------|
| 沙箱命令失败，宿主命令成功 | 沙箱无法访问宿主浏览器和扩展 |
| `extension command timed out` | 扩展未重载或页面未刷新 |
| 读到骨架页或上一页内容 | 页面未完成加载就触发了读取 |
| workflow 返回 `targetId: null` | 临时标签页已在 workflow 内关闭，正常现象 |
| 图片缓存下载失败 | 检查 bridge 服务环境中的代理配置和网络可达性 |
| Native Host 报异常消息长度 | stdout 被 shell / wrapper 噪音污染，检查 manifest 是否指向可靠的 native host 进程 |

### 临时产物清理

调试 Windows + WSL 链路时可能创建临时 Edge profile、临时扩展副本、pycache 或图片缓存。正式验证完成后应清理这些临时目录，避免把调试状态误认为产品安装状态：

```text
C:\Users\<user>\AppData\Local\Temp\browser-bridge-edge-profile
C:\Users\<user>\AppData\Local\Temp\browser-bridge-extension
/tmp/browser-bridge-pycache
/tmp/browser-bridge-edge-profile
/tmp/browser-bridge-cache
```

不要删除 `%LOCALAPPDATA%\BrowserBridge\NativeHost`，它是 Windows Native Host 的正式用户级安装目录。

### 图片缓存注意事项

- 不同站点的 CDN 对 bridge 侧下载器要求不一致
- 微博图片：`urllib` 可能返回 403，过重的 `curl` 参数也可能失败
- 更稳的做法：让下载器走宿主侧可用的最小 `curl` 路径
- 如果 bridge 服务清空了代理环境，要确认不会影响外网媒体下载
- 排查时先检查服务环境变量，再判断站点适配逻辑

## 测试页面

| 站点 | URL |
|------|-----|
| X 单帖 | `https://x.com/billtheinvestor/status/2038173185875775987` |
| 小红书单帖 | `https://www.xiaohongshu.com/explore/69c6469e000000001d01d9d1` |
| 微博单帖 | `https://weibo.com/6105713761/Qy80W8wXc` |
| 微博首页 | `https://weibo.com/` |
| 微博热搜 | `https://weibo.com/hot/search` |
| 微博搜索 | `https://s.weibo.com/weibo?q=OpenClaw` |
| 微博移动 | `https://m.weibo.cn/status/5281987678962257` |

## 已知残余风险

- `follow_user / unfollow_user` 依赖 DOM 启发式按钮定位，非绝对刚性
- 小红书视频笔记只保留视频存在标记，不缓存视频文件
- 小红书媒体提取依赖页面结构启发式，页面改版时可能需调整
- 部分站点媒体缓存依赖 bridge 服务环境中的代理可达性
- 真实浏览器页面状态偶尔有时序波动，skill 层仍需少量等待与重试
- 旧接口仍在保留，扩功能时要防止回流到旧接口上加站点特判

## 核心开发原则

1. 不把 CDP 拉回站点语义层
2. 不让 skill 脚本重新长成一堆补丁
3. 不让状态变更动作靠"猜测目标"完成
