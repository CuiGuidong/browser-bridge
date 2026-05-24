# 运维指南

本指南覆盖 Browser Bridge 的服务管理、环境配置和常见故障排查。

## 服务管理

### systemd 服务

Bridge 推荐通过 systemd 管理：

```bash
# 重启
sudo systemctl restart browser-bridge.service

# 查看状态
sudo systemctl status browser-bridge.service

# 查看日志
journalctl -u browser-bridge.service -f
```

服务定义文件位于 `bridge/systemd/browser-bridge.service`。

### 手动启动

```bash
cd bridge
source .venv/bin/activate
python -m app.server
```

## 环境变量

### Bridge 服务

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BRIDGE_HOST` | `127.0.0.1` | 监听地址 |
| `BRIDGE_PORT` | `17777` | 监听端口 |
| `BROWSER_RUNTIME` | `auto` | 浏览器控制通道：`auto`（优先 native，回退 CDP）或 `native_only` |

在 OrbStack VM 中访问宿主机浏览器时，`CDP_CONNECT_HOST` 需设为 `host.orb.internal`。

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

1. **浏览器**：是否已启动，CDP 端口是否可访问
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

### 旧版残留

- Bridge 代码修改后未重启 → curl 仍在访问旧版逻辑
- 扩展代码修改后未刷新页面 → 旧页面仍运行旧版 content script
- 这两种情况都会制造"明明改对了，测试还失败"的假象
