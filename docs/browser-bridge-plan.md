# Browser Bridge 技术方案（定稿草案）

_Last updated: 2026-03-12_

## 1. 项目目标

构建一个**真实浏览器桥（Real Browser Bridge）**，让 OpenClaw / agent 可以在**真实登录态、真实浏览器环境**下帮助用户：

- 访问链接
- 读取页面
- 操作网页
- 点击、输入、提交简单表单
- 在复杂页面中执行较稳的交互流程

核心目标不是极致自动化，也不是大规模爬虫，而是：

> 在尽量接近用户本人操作的前提下，降低简单风控/机器人拦截概率，并优先保护账号安全。

---

## 2. 明确的非目标

本项目**不追求**：

- 大规模爬虫
- 批量账号矩阵
- 极限反检测 / 高级 stealth 对抗
- 自动绕过验证码 / 2FA / 登录验证
- 完整的通用网页自动化平台
- 第三方云中控 / 第三方 relay / 第三方代操作服务

本项目默认是**本地优先、低频、单用户、自用型网页助理桥**。

---

## 3. 核心设计原则

### 3.1 真实浏览器优先

必须使用用户自己的真实 Chrome / Edge 浏览器实例作为身份与登录态载体。

原因：
- 真实用户 profile
- 真实 cookie / localStorage / session
- 真实安装扩展、字体、历史环境
- 更接近真人浏览行为
- 比独立自动化上下文更不容易触发简单风控

### 3.2 CDP 作为主控制面

Chrome DevTools Protocol (CDP) 是默认主控制层。

CDP 负责：
- 连接真实浏览器
- 枚举 / 管理 tabs
- 页面导航
- 执行 JS
- DOM 查询
- 简单点击 / 输入 / 读取页面状态

### 3.3 浏览器扩展做轻增强，不做主控

扩展是辅助层，不是核心控制器。

扩展可负责：
- 获取当前 tab 的轻量页面摘要
- 暴露页面内更稳定的语义锚点
- 将简单页面动作封装为低侵入快捷路径
- 与本地 bridge 通信

扩展**不得**：
- 连接第三方服务端承接核心控制逻辑
- 上传敏感页面内容到第三方
- 成为账号或会话控制的黑盒入口

### 3.4 Playwright 保留，但只能 attach 到真实浏览器

Playwright 的角色是**复杂操作执行器**，不是浏览器身份环境。

只能这样使用：
- attach 到现有真实 Chrome / Edge 实例
- 复用真实 profile / 会话
- 在复杂页面中使用 locator / wait / frame / evaluate 能力

不能这样使用：
- 默认启动新的自动化浏览器上下文作为主路径
- 默认依赖 headless 或独立 profile

### 3.5 安全优先于效率

项目不追求极致速度与吞吐。

为了降低账号风险，应主动接受：
- 慢一点
- 操作间隔更自然
- 某些高风险动作必须人工确认
- 某些 challenge 直接停下，不强行突破

---

## 4. 总体架构

```text
OpenClaw / Agent
    ↓
本地 browser-bridge 服务
    ↓
默认：CDP 连接真实 Chrome / Edge
    ↓
可选增强：本地浏览器扩展
    ↓
复杂流程：Playwright attach over CDP
```

### 4.1 分层职责

#### Layer 1: 真实浏览器实例
- Chrome / Edge
- 用户真实 profile
- 用户真实登录态

#### Layer 2: 本地 browser-bridge
- 接受 agent 的统一控制请求
- 管理 CDP 连接
- 路由动作到 extension quick path / raw CDP path / Playwright attach path
- 提供结构化返回

#### Layer 3: 浏览器扩展
- 页面轻量状态采集
- 简单动作辅助
- 与本地 bridge 通信

#### Layer 4: Playwright attach
- 复杂页面流程
- 更稳定的 locator / wait / frame handling
- 不直接承载用户身份环境

---

## 5. 执行路径策略

### 5.1 Path A: Extension Quick Path

适合：
- 读取当前页标题、URL、摘要
- 获取主要正文
- 轻量点击
- 简单输入
- 当前页面语义定位

特点：
- 快
- 轻
- 对简单页面无需动用完整 CDP/Playwright 流程

### 5.2 Path B: CDP Direct Path

默认主路径。

适合：
- tab 管理
- 页面导航
- DOM 查询
- JS 执行
- 页面状态读取
- 轻中等复杂度交互

### 5.3 Path C: Playwright Attach Path

适合：
- 多步骤复杂流程
- iframe / shadow DOM / SPA
- 不稳定页面，需要 wait / retry / locator
- 表单链路较长的站点

这是重路径，非默认。

---

## 6. 安全边界与人工确认规则

### 6.1 必须人工确认的动作

以下动作必须设计 hard stop：
- 登录
- 登出
- 2FA / MFA
- 验证码
- 改密码
- 改邮箱 / 手机号
- 支付 / 转账
- 发布内容
- 删除数据
- 授权第三方应用
- 账号设置修改

### 6.2 默认禁止的能力

bridge 不应默认提供：
- 自动过验证码
- 自动过短信/邮箱验证码
- 模拟支付确认
- 大规模批量站点操作
- 高频轮询同站点

### 6.3 行为节奏约束

bridge 内部应考虑：
- 同站点动作最小间隔
- 页面加载后的自然等待
- 尽量避免机械规律操作节奏
- 检测到异常 challenge 时直接停下

---

## 7. 技术路线定稿

### 7.1 浏览器选择

- **完全放弃 Safari**
- 仅支持：
  - Chrome
  - Edge

原因：
- CDP 原生支持成熟
- Playwright attach 更顺
- 扩展生态更适合做本地增强

### 7.2 服务部署位置

优先候选：
1. 用户的主力 Mac（最接近真实环境）
2. 用户局域网内一台长期在线设备（如 NAS）

### 7.3 关于 NAS 上 Docker Edge

这是一个**可行但有前提**的路线。

#### 可行点
- NAS 内存充裕，适合长驻浏览器容器
- Docker 便于管理与隔离
- 如果浏览器实例长期运行，bridge 连接与会话复用会更稳定

#### 关键前提
1. 该 Edge/Chrome 容器必须尽可能接近“真实使用环境”
2. 需要明确远程桌面/显示方案，便于人工接管与确认
3. 需要稳定暴露 CDP 端口，仅对可信局域网或桥服务开放
4. 最好避免“完全无头 + 干净 profile”作为默认形态

#### 风险与局限
- Docker 里的浏览器仍然可能比你主力 Mac 上的真实日常浏览器更像“特殊环境”
- 某些网站会对 Linux 容器环境、虚拟显示环境更敏感
- 如果你的核心目标是“尽量像你本人”，那么**主力设备上的真实浏览器**通常仍优于 NAS 容器浏览器

#### 结论
- **NAS Docker Edge 可以做 bridge runtime 和长期驻留浏览器**
- 但它在“接近真人环境”这一点上，未必优于你的主力桌面浏览器
- 所以更像是：
  - 一个可行部署候选
  - 不是天然最佳选择

### 7.4 关于当前 OpenClaw 运行环境（OrbStack）

当前 OpenClaw 运行在 OrbStack 虚拟机里。

这意味着：
- 需要确认从当前环境访问宿主机和家庭局域网的连通性
- 理论上通常可以访问宿主机网络与局域网设备，但不能凭空假设所有端口都直通
- 在真正开发前，需要单独做网络连通性验证：
  - bridge 主机 IP 可达性
  - CDP 端口可达性
  - 本地 bridge HTTP/WebSocket 端口可达性

因此，“Mac 能访问 NAS，NAS 和 Mac 在同一家庭局域网”并不自动等于“当前 agent 运行环境就能直接访问 NAS 的目标端口”。

这部分必须在实现前做一次实际连通性测试。

### 7.5 Phase 1 已确认的环境事实

- 主力 Mac 上的真实 Edge 已可用，并能通过 `--remote-debugging-port=<port>` 成功开启 CDP。
- 端口 `9222` 不适合作为默认值，因为宿主环境中已与 OrbStack 占用冲突；`9333` 已验证可正常使用。
- 当前 OpenClaw / OrbStack 环境可通过 `host.orb.internal` 访问宿主机上的 Edge CDP 服务。
- 访问宿主机 CDP 时，不能直接使用默认的 `Host: host.orb.internal:<port>`；需要显式发送 `Host: 127.0.0.1:<port>`，否则目标服务会拒绝请求。
- 这说明后续 bridge / client 层需要明确处理 Host header，而不是假设普通 HTTP 访问即可。
- `host.orb.internal` 仅用于访问宿主 Mac；访问家庭局域网其他设备（如 NAS）时，当前 OrbStack/OpenClaw 环境可直接通过其局域网 IP 访问，无需该魔法域名。
- NAS 上已预先部署 `kasmweb edge` 容器，并通过反向代理将对外 `http://192.168.31.232:9333` 转发到实际 HTTPS/CDP 端口；从当前 OpenClaw / OrbStack 环境已验证可访问 `/json/version`。
- 虽然 NAS 路线已具备初步连通性，但当前开发测试主线仍坚持使用宿主 Mac 上的真实 Edge，以避免额外网络和环境变量带来的不可预期干扰。

---

## 8. Browser Bridge v1 范围（当前已拍板）

v1 只做以下能力：

1. 列出当前浏览器 tabs
2. 选择 / 聚焦 tab
3. 打开链接
4. 获取当前页：
   - title
   - url
   - visible text summary
5. 简单点击
6. 简单输入
7. 执行少量 JS
8. 截图
9. 返回结构化结果

### v1 默认策略
- 默认：CDP
- 简单页面：扩展 quick path
- 复杂页面：Playwright attach

### v1 明确不做
- 自动登录
- 自动过验证码
- 大规模任务调度
- 第三方 relay/云控制
- 高级 stealth 对抗

---

## 9. skill 设计方向

未来应设计成共享 skill suite，而不是单一脚本。

建议技能层次：
- `browser-bridge`：门面 skill
- `browser-bridge-basic`：基础页面操作
- `browser-bridge-playwright`：复杂交互路径
- `browser-bridge-auth-safe`：高风险动作边界说明

但当前阶段不先展开实现细节，先以本地技术方案为准。

---

## 10. 当前阶段决策结论

### 已确认的关键结论
- 抛弃 Safari
- Chrome / Edge only
- CDP 作为根基
- 扩展做轻增强
- Playwright 只能 attach 到真实浏览器
- 不走第三方 skill 壳 + 远端服务端路线
- 不追求大规模自动化
- 账号安全优先于效率
- 高风险动作必须人工确认

### 当前未决问题
- bridge 最终部署在主力 Mac 还是 NAS Docker Edge
- OrbStack 当前环境到候选 bridge 主机的网络连通性
- 扩展与 bridge 的通信方式（Native Messaging / localhost / WebSocket）
- CDP 端口与访问控制策略

这些未决项应在后续 plan 阶段逐项落定。
