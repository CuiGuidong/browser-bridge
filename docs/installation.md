# 安装指南

本文面向第一次安装 Browser Bridge 的用户。开发工作流见 [development.md](development.md)，服务排障见 [operations.md](operations.md)。

## 安装模型

Browser Bridge 单机部署由三部分组成：

```text
Bridge daemon
  -> Native Host
    -> Browser Extension
      -> Real Browser Page
```

- Bridge daemon：本项目的 FastAPI 服务。
- Native Host：由 Chrome/Edge 通过 Native Messaging 启动的本机进程。
- Browser Extension：浏览器扩展，负责页面内 adapter 和浏览器操作。

Python 依赖安装到项目内 `bridge/.venv`，不需要全局 `pip install`。

## macOS 单机安装

前置条件：

- macOS
- Chrome 或 Edge
- Python 3.10+

运行：

```bash
./scripts/setup_macos.sh
```

脚本会：

- 创建 `bridge/.venv`
- 安装 `requirements.txt`
- 生成 `extension/manifest.json`
- 询问 Bridge 监听地址和端口
- 引导你加载 `extension/`
- 安装 Chrome/Edge 用户级 Native Host manifest

加载扩展：

1. 打开 `chrome://extensions` 或 `edge://extensions`。
2. 开启 Developer mode。
3. 选择 Load unpacked。
4. 选择本项目的 `extension/` 目录。
5. 复制扩展 ID，按脚本提示粘贴，或重新运行：

```bash
./scripts/setup_macos.sh --extension-id <extension-id>
```

启动：

```bash
./scripts/start_bridge.sh
```

诊断：

```bash
./scripts/doctor.sh
```

## Windows + WSL 安装

Windows + WSL 路径中：

- WSL 侧运行项目代码、Python venv 和 Bridge daemon。
- Windows 侧运行 Chrome 或 Edge。
- Windows 侧安装 Native Host manifest 和 launcher。
- Windows launcher 由浏览器直接启动，通过 HTTP 连接 WSL 内的 Bridge。

不要把 Windows Native Host 做成 `.cmd` 调 `wsl.exe` 的转发链路。Native Messaging 要求 stdout 只能输出协议帧，shell 或 `wsl.exe` 链路上的额外字节会让浏览器把非协议内容当成消息长度，表现为 Native Host 消息长度异常。

当前安装脚本会在 Windows 侧使用 .NET Framework 自带的 C# 编译器生成一个很小的 launcher：

```text
%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
```

如果该编译器不存在，脚本会失败并提示安装 .NET Framework build tools，或改用预构建的 Native Host launcher。

### 1. WSL 侧 setup

在 WSL 项目目录运行：

```bash
./scripts/setup_wsl.sh
```

脚本会创建 venv、安装依赖、生成 `extension/manifest.json`，并输出 Windows PowerShell 安装命令。

### 2. Windows 侧加载扩展

按 `setup_wsl.sh` 输出的 Windows 路径，在 Chrome/Edge 中加载 `extension/`。

### 3. Windows 侧安装 Native Host

在 Windows PowerShell 中运行 `setup_wsl.sh` 输出的命令，形态如下：

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\scripts\windows\install-native-host.ps1" `
  -ExtensionId "<extension-id>" `
  -Browser edge `
  -BridgeUrl "http://127.0.0.1:17777"
```

如果实际加载扩展的是 Chrome，把 `-Browser edge` 改成 `-Browser chrome`。只有在两个浏览器都加载了同一个扩展 ID 时才使用 `-Browser both`。

扩展 ID 必须从当前实际加载 `extension/` 目录的浏览器扩展详情页复制，不要从旧日志、历史配置或任意 `chrome-extension://` 标签页推断。

安装脚本会把 Native Host manifest 和 launcher 写入用户级目录，并在 `HKCU` 下注册对应浏览器的 Native Messaging host。

Windows 安装产物位于：

```text
%LOCALAPPDATA%\BrowserBridge\NativeHost\
```

正常会保留：

- `browser-bridge-native-host.exe`
- `browser-bridge-native-host.log`
- `com.cuiguidong.browserbridge.json`

安装脚本可能临时生成 C# 源文件用于编译 launcher，编译后会删除；旧版 `.cmd` wrapper 也会被清理。

### 4. WSL 侧启动和诊断

```bash
./scripts/start_bridge.sh
./scripts/doctor.sh
```

如果 `doctor.sh` 显示 Bridge 可达但 Native session 未连接，优先检查 Windows 侧是否已重新加载扩展，以及 PowerShell 安装命令中的 extension id、`-Browser` 和 `BridgeUrl` 是否正确。

## Linux 单机安装

Linux 单机路径可使用现有脚本：

```bash
python3 -m venv bridge/.venv
bridge/.venv/bin/python3 -m pip install -r requirements.txt
cp extension/manifest.prod.json extension/manifest.json
./scripts/install-native-host.sh <extension-id>
./scripts/start_bridge.sh
```

需要 systemd 管理时，参考 [operations.md](operations.md)。

## 监听地址

setup 脚本会询问 Bridge host：

- `127.0.0.1`：只监听本机，默认推荐。
- `0.0.0.0`：监听本机所有网卡，适合局域网内其他设备访问。

无论 Bridge 监听哪个地址，本机 Native Host shim 默认可以通过 `BRIDGE_URL` 或 `127.0.0.1:<port>` 连接 Bridge。

## Native Host manifest

Native Host manifest 是浏览器读取的本机 JSON 文件。它告诉 Chrome/Edge：

- native host 的名称
- 要启动哪个本机进程
- 允许哪个扩展连接

macOS 和 Linux 使用浏览器约定目录中的 JSON 文件；Windows 使用注册表指向 manifest 文件。本项目脚本会自动生成这些文件，普通用户不需要手写 JSON。

Windows + WSL 场景中，manifest 的 `path` 应指向 Windows 可执行文件，例如：

```text
C:\Users\<user>\AppData\Local\BrowserBridge\NativeHost\browser-bridge-native-host.exe
```

它不应指向 WSL 路径，也不应指向需要 shell 转发的 `.cmd` 文件。

官方参考：

- Chrome Native Messaging: <https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging>
- Microsoft Edge Native Messaging: <https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging>

## 常见检查

Bridge 健康检查：

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

扩展状态：

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/extension/state
```

统一诊断：

```bash
./scripts/doctor.sh
```

Windows + WSL 下，如果 Codex、CI 或其他沙箱里访问 `127.0.0.1:17777` 失败，不一定代表 Bridge 没启动。先在真实 WSL shell 中重试 `curl --noproxy '*' -sS http://127.0.0.1:17777/health`，再判断服务状态。
