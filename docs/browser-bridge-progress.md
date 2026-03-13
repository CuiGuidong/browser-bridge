# Browser Bridge 进度记录

_Last updated: 2026-03-12_

## 当前阶段

阶段：**方案冻结 / 文档化**

目标：
- 把已讨论并拍板的架构、边界、技术路线写成稳定文档
- 避免后续因为上下文过长丢失关键决策
- 作为后续实现 plan 与阶段验收的依据

---

## 已完成

- 明确项目目标：真实浏览器桥，不做重型爬虫/代操作服务
- 明确非目标：不做批量爬虫、验证码绕过、第三方云控制
- 确认浏览器路线：**Chrome / Edge only**，抛弃 Safari
- 确认主控制面：**CDP first**
- 确认扩展角色：**轻增强，不做主控**
- 确认 Playwright 角色：**只 attach 到真实浏览器实例**
- 确认安全原则：账号安全优先，高风险动作人工确认
- 形成技术方案文档：`docs/browser-bridge-plan.md`

---

## 当前已确认决策

1. **第一优先部署位置**
   - 主力 Mac 上的真实 Edge 浏览器
   - 原因：调试难度最低，网络阻碍最少，先打通本地真实浏览器链路，后续迁移到 NAS 更容易

2. **第一阶段浏览器选择**
   - Edge 优先
   - 理由：用户当前主力使用 Edge；Chrome/Edge 内核接近，但应优先贴近用户真实日常环境

3. **第一阶段目标**
   - 只做“连通性和可行性验证”
   - 这是项目继续推进的前提

4. **协作策略**
   - 当前阶段先由主协调者控盘
   - 后续到了可明确拆分的模块（如网络、浏览器、扩展、bridge）时，可按需调度 weekday agents 或 subagents 协作，但必须由主协调者统一收口

---

## 当前未决项

1. **扩展通信方式**
   - localhost HTTP
   - WebSocket
   - Native Messaging

2. **访问控制策略**
   - CDP 暴露方式
   - 是否只允许本地监听
   - 是否需要额外反向代理 / ACL

3. **Mac 与 NAS 双路线的后续切换策略**
   - 当前开发测试坚持以宿主 Mac 上的真实 Edge 为主
   - NAS 路线暂不进入实现主线，但其环境可达性已提前验证成功，可作为后续迁移候选

---

## 下一阶段建议（待执行）

进入：**Phase 2 - bridge skeleton 与最小 CDP 接入**

当前阶段已确认：
- Phase 1 通过
- Phase 2 采用 Python
- 截图能力后置，不作为 Phase 2 必做项

Phase 2 聚焦：
1. Python 本地 HTTP bridge skeleton
2. 宿主 Mac 上真实 Edge CDP 的访问适配（包括 Host header 处理）
3. 最小 API：health / version / tabs / open / activate / optional page-info
4. 统一响应 schema

### Phase 2 当前结果
- 最小 API 已全部打通：health / version / tabs / open / activate / page-info
- `open` 的实现细节已确认：当前 Edge `/json/new` 仅接受 `PUT`
- 已进一步打通页面观察能力：
  - `GET /page-content`
  - `POST /screenshot`
- 当前阶段已从“skeleton”进入“最小可用且具备页面观察能力的 bridge”状态

---

## Phase 1 结果更新

### 已验证通过

1. **主力 Mac 上真实 Edge 可作为第一优先浏览器载体**
2. **Edge 可通过启动参数成功启用 CDP**
3. **9333 作为调试端口可正常返回标准 `/json/version` 信息**
4. **当前 OpenClaw / OrbStack 环境可以通过 `host.orb.internal` 访问宿主机上的 Edge CDP 服务**
5. **访问宿主机 CDP 时需要显式修正 Host header**：
   - 直接访问 `http://host.orb.internal:9333/...` 会被目标服务拒绝
   - 使用 `Host: 127.0.0.1:9333` 头后可正常访问

### Phase 1 判断

Phase 1（环境与连通性验证）**通过**。

这意味着：
- 真实 Edge + CDP 路线在当前环境下成立
- 当前 OrbStack/OpenClaw 环境到宿主机浏览器实例的访问链路成立
- 后续可以进入下一阶段：bridge skeleton 与最小 CDP 接入实现

---

## 当前状态判断

项目状态：**可以进入真实工程实现阶段，且已完成第一阶段环境可行性验证**

当前最重要的资产：
- 技术路线已拍板
- 安全边界已拍板
- 架构分层已拍板
- 文档已落地
- Phase 1 已完成并通过
- Phase 2 已形成临时执行指南：`browser-bridge-phase-2.md`
- 用户已授权进入“心流开发模式”：后续可连续开发，不必每一步确认；但必须记录未确认事项、环境变更、安装内容，并在用户醒来后集中汇报

这意味着接下来可以按工程方式推进，而不是继续靠长对话堆上下文。

---

## 临时执行文档

- `browser-bridge-phase-2.md`
  - 用途：当前阶段的可编码任务拆解与执行参考
  - 性质：临时文档
  - 处理方式：本阶段完成后可删除或归档
