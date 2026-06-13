# 运维指南

本指南覆盖 Browser Bridge 的服务管理、环境配置和常见故障排查。

## 服务管理

### 前台启动

安装完成后，优先使用统一启动脚本：

```bash
./scripts/start_bridge.sh
```

脚本会读取 `.env.local` 中的 `BRIDGE_HOST` 和 `BRIDGE_PORT`，并使用 `bridge/.venv` 中的 Python 启动 Bridge。

也可以手动启动：

```bash
cd bridge
source .venv/bin/activate
python -m app.server
```

### 诊断

```bash
./scripts/doctor.sh
```

`doctor.sh` 会检查 venv、扩展 manifest、Bridge HTTP、Native session 和扩展状态，并输出下一步修复建议。

### Linux systemd 服务

Linux 长期运行时可以通过 systemd 管理：

```bash
sudo systemctl restart browser-bridge.service
sudo systemctl status browser-bridge.service
journalctl -u browser-bridge.service -f
```

服务定义文件位于 `bridge/systemd/browser-bridge.service`。

### Windows + WSL

Windows + WSL 路径中，Bridge 在 WSL 内运行，Chrome/Edge 在 Windows 侧运行。Native Host manifest 和 launcher 由 Windows PowerShell 脚本安装；Bridge 启动和诊断仍在 WSL 内执行：

```bash
./scripts/start_bridge.sh
./scripts/doctor.sh
```

Windows 侧 Native Host 使用当前用户级安装，不需要管理员权限。正式产物位于：

```text
%LOCALAPPDATA%\BrowserBridge\NativeHost\
```

保留文件：

- `browser-bridge-native-host.exe`：Windows 侧 Native Messaging host launcher，由浏览器直接启动。
- `com.cuiguidong.browserbridge.json`：Native Host manifest。
- `browser-bridge-native-host.log`：Native Host 轻量连接日志。

Edge 注册表项：

```text
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.cuiguidong.browserbridge
```

Chrome 注册表项：

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.cuiguidong.browserbridge
```

实际存在哪个注册表项取决于安装脚本的 `-Browser` 参数。

## 环境变量

### Bridge 服务

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BRIDGE_HOST` | `127.0.0.1` | 监听地址 |
| `BRIDGE_PORT` | `17777` | 监听端口 |
| `BRIDGE_URL` | `http://127.0.0.1:17777` | Native Host shim 连接 Bridge 的 URL |
| `BROWSER_RUNTIME` | `auto` | 历史兼容配置项。当前无行为差异，所有页面控制已全面由 NativeBrowserRuntime 跑通并走 Native Messaging 通道。 |

> **残留说明**：`/playwright/*` 端点仍通过 Playwright CDP 连接浏览器，不受 `BROWSER_RUNTIME` 控制。这是独立的调试通道，不在本次 native 迁移范围内。

### 代理

如需通过代理访问外网资源（如图片缓存下载），通过 systemd drop-in 或环境变量配置：

```bash
http_proxy=http://<proxy_host>:<port>
https_proxy=http://<proxy_host>:<port>
all_proxy=http://<proxy_host>:<port>
NO_PROXY=127.0.0.1,localhost
```

`NO_PROXY` 确保本地流量（Bridge ↔ 扩展 ↔ 浏览器）不走代理。

## 健康检查

```bash
# 统一诊断
./scripts/doctor.sh

# Bridge 是否在线
curl --noproxy '*' -sS http://127.0.0.1:17777/health

# 当前浏览器标签页
curl --noproxy '*' -sS http://127.0.0.1:17777/tabs

# 扩展状态
curl --noproxy '*' -sS http://127.0.0.1:17777/extension/state

# 站点能力
curl --noproxy '*' -sS 'http://127.0.0.1:17777/site/capabilities?site=<site>&targetId=<id>'
```

## 故障排查

### 诊断顺序

链路失败时，按以下顺序定位，不要先改代码：

1. **浏览器**：是否已启动，Native Session 是否已连接（健康检查 `/health` 返回 `nativeSession: connected`）
2. **Bridge**：`/health` 是否正常，是否是最新代码并已重启
3. **扩展**：是否已重载，目标页面是否已刷新，`/extension/state` 是否有最近上报
4. **目标页**：`/tabs` 能否看到目标页，`/site/capabilities` 是否命中正确页面
5. **语义能力**：`/site/read` 或 `/site/action` 返回结果，错误在 Bridge、扩展还是目标页匹配阶段

### 常见问题

| 现象 | 优先怀疑 |
|------|----------|
| 沙箱命令失败，宿主命令成功 | 沙箱无法访问宿主浏览器和扩展 |
| `extension command timed out` | 扩展未重载或页面未刷新 |
| 读到骨架页或上一页内容 | 页面未完成加载就触发了读取 |
| workflow 返回 `targetId: null` | 临时标签页已在 workflow 内关闭，正常现象 |
| 图片缓存下载失败 | 检查 bridge 服务环境中的代理配置和网络可达性 |
| Native Host 消息长度异常 | manifest 指向的进程 stdout 输出了非协议字节；检查是否误用 `.cmd` / `wsl.exe` 转发 |

### 旧版残留

- Bridge 代码修改后未重启 → curl 仍在访问旧版逻辑
- 扩展代码修改后未刷新页面 → 旧页面仍运行旧版 content script
- 这两种情况都会制造"明明改对了，测试还失败"的假象

### Windows + WSL 清理边界

可以清理的调试产物：

```text
C:\Users\<user>\AppData\Local\Temp\browser-bridge-edge-profile
C:\Users\<user>\AppData\Local\Temp\browser-bridge-extension
/tmp/browser-bridge-pycache
/tmp/browser-bridge-edge-profile
/tmp/browser-bridge-cache
```

不要当作垃圾清理的正式产物：

```text
%LOCALAPPDATA%\BrowserBridge\NativeHost\
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.cuiguidong.browserbridge
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.cuiguidong.browserbridge
```

如果需要卸载 Browser Bridge，再删除这些正式安装产物和对应注册表项。
