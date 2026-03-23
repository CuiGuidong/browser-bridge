# Browser Bridge 架构规范 (Architecture Spec)

_最后更新: 2026-03-23_
_状态: 正式规范_

## 1. 目标 (Purpose)

Browser Bridge 是一个本地优先的“桥梁”，允许 AI Agent 通过结构化的 HTTP API 操作用户真实的 Chrome/Edge 浏览器，同时保留用户真实的登录状态、Cookie、用户资料和浏览环境。

**主要目标:**
- 在真实网站上提供安全、低频、拟人化的操作辅助

**非目标 (Non-goals):**
- 大规模批量爬虫
- 参与反爬虫攻防战
- 绕过验证码 / 2FA（双因素认证）
- 云端中继控制面板
- 自动执行高风险账户操作

## 2. 系统模型 (System Model)

```text
Agent / OpenClaw skill
  -> Browser Bridge HTTP API
    -> Path A: Browser Extension (浏览器扩展) / 语义层
    -> Path B: CDP (Chrome DevTools Protocol) 直接控制层
    -> Path C: Playwright 附加控制层
```

## 3. 设计约束 (Design Constraints)

- 仅限真实浏览器：Chrome / Edge
- 优先使用宿主机（Mac）真实的浏览器，而不是合成的容器身份
- 必须本地优先
- 高风险操作必须需要人工确认
- 浏览器扩展只是功能增强，不是唯一的控制平面
- Playwright 只能附加（attach）到现有的浏览器实例上，不能启动一个新的自动化身份

## 4. 核心组件 (Core Components)

### 4.1 CDP HTTP 客户端
职责：
- 调用 `/json/version`, `/json/list`, `/json/new`, `/json/activate` 等端点
- 当通过 OrbStack 访问宿主机浏览器时，注入必要的 `Host: 127.0.0.1:9333` 请求头

### 4.2 CDP WebSocket 客户端
职责：
- `Runtime.evaluate` (执行 JS)
- `Page.captureScreenshot` (截图)
- 提供基于 DOM 的读取、点击、输入等辅助方法

### 4.3 Bridge 服务端
职责：
- 规范化 targets (标签页) / 页面信息
- 暴露供 Agent 调用的 HTTP API
- 收集页面的就绪状态 (readiness probes)
- 将扩展层上报的数据 (hints) 与 CDP 兜底抓取的数据进行合并

### 4.4 扩展层 (Extension Layer)
职责：
- 观察并理解页面语义
- 包含特定网站的适配器 (site-specific adapters)
- 向 Bridge 持续上报当前活跃页面的状态
- 提供高频网站的数据解析（目前已实现 X / Twitter）

### 4.5 Playwright 附加层
职责：
- 处理稳健且复杂的交互
- 提供定位器 (locator)、等待 (wait)、表单提交流程
- 面向未来更重的自动化工作流

## 5. 当前 API 列表 (Current API Surface)

### 基础 Bridge API
- `GET /health`
- `GET /version`
- `GET /tabs`
- `POST /open`
- `POST /activate`
- `GET /wait`
- `GET /page-info`
- `GET /page-content`
- `GET /probe-readiness`
- `POST /read-page`
- `POST /screenshot`
- `GET /query`
- `POST /click`
- `POST /fill`

### 扩展集成 API (Extension Integration)
- `POST /extension/report`
- `GET /extension/state`

### Playwright API
- `POST /playwright/connect`
- `POST /playwright/disconnect`
- `GET /playwright/pages`
- `POST /playwright/click`
- `POST /playwright/fill`
- `POST /playwright/evaluate`
- `GET /playwright/wait-selector`

## 6. 就绪模型 (Readiness Model)

Bridge **绝不能**把单纯的死等 (`sleep`) 作为主要的加载判断策略。

页面的就绪信号 (Readiness signals) 是分层的：

### 通用就绪判断
- `document.readyState` 状态
- URL 和页面 Title 的稳定性
- 页面正文长度达到阈值
- （可选）关键 CSS 选择器是否出现

### 特定网站的就绪判断
- 网站专属的适配器提供语义级别的就绪状态
- 当前已支持的适配器：`x` (Twitter)

### 网络感知的就绪判断
- 预期信号：最近的网络请求是否有一段“静默期” (quiet period)
- 当前状态：请求探针已接入扩展上报机制以及 X 的就绪打分中，但仍需在长期真实会话中进一步验证。

## 7. 网站适配器模型 (Site Adapter Model)

适配器抽象必须支持以下功能：
- `match()`: 匹配域名
- `collect()`: 收集页面数据
- 对页面进行语义分类
- 提取页面的核心内容 (Primary content extraction)
- 专属网站的就绪状态判断

当前的适配器：
- `generic` (通用)
- `x` (Twitter)

针对 X 的专有 Skill 封装：
- `skills/x-assistant` (包含搜索、首页流、单帖读取脚本)

## 8. 安全边界 (Safety Boundary)

遇到以下操作时，Bridge 必须进行硬拦截或要求人工明确确认：
- 登录 / 登出
- 2FA / MFA（双因素认证）
- 验证码挑战
- 修改密码 / 邮箱 / 手机号
- 支付 / 转账
- 发布或删除内容
- 第三方应用授权

当前状态：
- 仅作为策略在文档中规定
- 尚未在路由级别的代码中实现强制拦截

## 9. 已知局限性 (Known Limitations)

- 扩展的安装与重新加载仍然需要人类在浏览器端手动操作。
- X 适配器已能提取正文和时间线列表，但在部分边缘页面可能仍会夹带时间线或元数据噪音。