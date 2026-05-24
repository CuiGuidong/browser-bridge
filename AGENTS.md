# AGENTS

本文件是 `browser-bridge` 项目的 Agent 协作入口文件，仅用于本地 Agent 接手、开发、排障和交接约束。

本文件不替代项目正式文档，不复制本地环境细节，不维护具体命令清单。  
如果本文件与专门文档发生重叠，以“单一事实源”一节的边界为准。

---

## 项目定位

`browser-bridge` 是本地真实浏览器执行基座。

它负责：

- 复用真实浏览器、真实登录态和浏览器扩展
- 暴露稳定 HTTP API
- 通过 extension adapter 提供站点语义能力
- 通过 workflow 提供步骤固定、可验证的流程
- 支撑 skill、脚本、Agent 和外部业务系统调用

它不负责：

- 业务系统状态机
- 选题、文案、复盘、指标快照等业务模型
- 大规模爬虫
- 反爬虫攻防
- 绕过验证码、MFA、风控或平台限制
- 默认自动点击最终发布、删除、支付、授权确认等高风险动作

一句话心智模型：

`Skill / Agent / 外部系统 -> Browser Bridge HTTP API -> Workflow -> Extension + Adapter -> 真实浏览器页面`

---

## 接手顺序

新开会话、上下文重置、换 Agent 或长时间中断后，先读本文件，再按顺序阅读：

1. `LOCAL_DEV.md`
2. `README.md`
3. `docs/index.md`
4. `docs/architecture.md`
5. `docs/development.md`
6. `.agents/context.md`
7. `.agents/invariants.yaml`
8. `.agents/task-board.yaml`

按任务需要再读：

- 涉及本地开发搭建：读 `docs/development.md`
- 涉及部署、服务管理、故障排查：读 `docs/operations.md`
- 涉及 API：读 `docs/interfaces.md`
- 涉及站点能力：读 `docs/capabilities.md`
- 涉及新增站点：读 `docs/new-site-adaptation-guide.md`
- 涉及视频、图片、媒体缓存：读 `docs/video-asset-pipeline-design.md`
- 涉及跨项目调用：读 `docs/contracts/` 下的对应合同文档
- 涉及 `media-agent-suite`：读 `docs/contracts/media-agent-suite-contract.md`

不要跳过 `LOCAL_DEV.md`。  
本项目大量问题与宿主机、OrbStack、CDP、真实浏览器、扩展、代理、systemd 和登录态有关，不能只根据沙箱现象判断。

---

## 单一事实源

文档重叠时，不要自行综合、猜测或改写权威来源。

按以下边界判断：

1. `AGENTS.md`
   - Agent 行为规则
   - 接手顺序
   - 协作纪律
   - 上下文哨兵
   - 架构红线摘要

2. `LOCAL_DEV.md`
   - 本地宿主机事实
   - host、端口、代理、CDP、systemd、浏览器路径
   - 本地验证入口
   - 本地扩展同步路径
   - 本地测试页面

3. `README.md`
   - 公开项目入口
   - 项目定位
   - 快速开始
   - 文档导航
   - 对外可见能力概览

4. `docs/architecture.md`
   - 正式架构规范
   - 分层职责
   - 长期设计边界

5. `docs/development.md`
   - 本地开发搭建与实现细节
   - 开发工作流、调试方法、避坑点

6. `docs/interfaces.md`
   - HTTP API 行为
   - endpoint
   - 请求和响应结构

7. `docs/capabilities.md`
   - 站点支持矩阵
   - 已支持能力
   - 当前限制

8. `docs/new-site-adaptation-guide.md`
   - 新增站点适配流程
   - adapter、site module、workflow 的落点

9. `docs/operations.md`
   - 部署与服务管理
   - 环境变量、代理、故障排查

10. `docs/contracts/media-agent-suite-contract.md`
   - 与 `media-agent-suite` 的跨项目 issue-like 协作合同
   - 基座能力需求、支持状态、验收方式

11. `.agents/invariants.yaml`
   - 架构硬约束
   - 禁止模式
   - 不可破坏的边界

12. `.agents/task-board.yaml`
   - 当前任务状态
   - 已完成、进行中、待办任务
   - 后续开发入口

13. `.agents/quality-gates.md`
   - 验证命令
   - 不同改动类型对应的检查方式
    - 是否需要跑真实浏览器链路

如果文档之间出现冲突：

- 不要猜
- 不要选择性采用
- 不要在代码里绕过
- 先向用户报告冲突
- 明确说明你准备以哪个文件为准

---

## Harness 工作流

每次开发前：

1. 从 `.agents/task-board.yaml` 领取或确认任务
2. 对照 `.agents/invariants.yaml` 检查边界
3. 给出简短计划
4. 只修改完成当前任务所需的最少文件
5. 按 `.agents/quality-gates.md` 运行相关验证
6. 更新任务状态或说明未完成原因

如果任务不在 `task-board` 中：

- 先新增一条明确的小任务
- 再实施
- 不要把大任务拆成不可追踪的临时改动

如果用户只是要求分析、评审、阅读或规划：

- 不要修改代码
- 不要修改文档
- 不要生成补丁
- 只输出分析结果和建议

---

## 跨项目协作

`media-agent-suite` 是外部业务系统，不是本项目子模块。两个项目可以由不同会话窗口或不同 Agent 并行推进，沟通必须落到版本化合同文档，不能依赖聊天记忆。

协作文件：

- `browser-bridge` 侧合同：`docs/contracts/media-agent-suite-contract.md`
- `media-agent-suite` 侧需求源：`/home/cuiguidong/workspace/personal/projects/Python/media-agent-suite/docs/contracts/browser-bridge-adaptation.md`

协作方式模仿 GitHub issue：

1. `media-agent-suite` 发现基座能力缺失时，在需求源中新增 issue-like 条目，写清问题、期望合同、优先级和验收方式。
2. `browser-bridge` 侧读取需求后，在本项目合同中同步条目和状态。
3. 实现前先判断需求属于 browser-bridge 基座能力还是 media-agent-suite 业务逻辑；业务状态机、运营策略和数据入库不得进入本项目。
4. 交付后在本项目合同中记录 endpoint/workflow、params、返回字段、错误码和验证证据。
5. `media-agent-suite` 验收通过后，两边把条目从活跃需求清理到已完成摘要或关闭状态。

如果需求描述不够验收，不要猜测实现；先把条目标为 `blocked` 并说明缺少的信息。

---

## 架构硬边界

必须遵守以下边界：

- `Browser Runtime` 只负责浏览器控制和诊断，不承载站点 DOM 语义
- 站点 DOM 语义只放在 `extension/adapters/<site>-adapter.js`
- 固定流程放在 `bridge/app/sites/<site>/workflows/`
- `bridge/app/` 不复制站点 DOM 选择器
- skill 只做输入归一化、调用 workflow、整理输出
- skill 不重新接管页面生命周期
- 外部业务系统只调用 HTTP API
- 外部业务系统不依赖扩展、tab、Browser Runtime 或 adapter 内部细节
- 新站点优先按 adapter + site module + workflow 扩展
- 不为单个站点随意新增专属 HTTP endpoint
- 不把业务系统状态机塞进 `browser-bridge`
- 不使用站点私有、逆向或未正式公开的 API 替代页面适配；不要模仿站点内部 REST、GraphQL、签名、cookie/header 请求来绕过真实页面
- 站点读取优先基于真实浏览器页面的 DOM、可见状态 and extension adapter 语义；如确需调用官方公开 API，必须先说明来源、风险和账号安全影响，并取得用户明确同意

允许的分层关系：

- Browser Runtime：打开页面、复用标签页、导航、截图、基础 JS、诊断（均由 NativeBrowserRuntime 承载执行，底层无自动 CDP 通道切换；CdpRuntime 为历史兼容 Facade）
- Extension Adapter：站点匹配、页面类型、ready 探测、读取、动作、校验
- Workflow：固定步骤、页面生命周期、临时 tab 管理、流程级验证
- Skill / Agent：开放式判断、业务编排、输入归一化、结果总结
- 外部系统：只通过稳定 HTTP API 调用能力

---

## API 与 Workflow 约定

实现时遵守以下原则，具体接口以 `docs/interfaces.md` 和现有代码为准：

- API 响应使用统一 envelope
- 错误应返回明确 code、message 和 detail
- site 能力由 site module 显式声明
- dispatch 前必须检查 capability
- workflow 可以管理页面生命周期
- workflow 如果打开临时 tab，应在安全条件下关闭
- 状态变更动作应返回可验证结果
- 涉及发布、删除、支付、授权确认等高风险动作时，默认停在人工确认前
- 真实登录、验证码、MFA、风控验证不做绕过

---

## 新增站点原则

新增站点时，不要从脚本补丁开始。

优先阅读：

- `docs/new-site-adaptation-guide.md`
- `docs/architecture.md`
- `.agents/invariants.yaml`
- 现有成熟站点实现

新增站点的基本落点：

- 页面语义：`extension/adapters/<site>-adapter.js`
- 站点能力声明：`bridge/app/sites/<site>/models.py`
- 站点分发：`bridge/app/sites/<site>/site.py`
- 固定流程：`bridge/app/sites/<site>/workflows/`
- 注册入口：`bridge/app/server.py`
- 对外调用：复用统一 HTTP API

不要因为某个站点特殊，就绕开 adapter / workflow / registry 分层。

---

## 宿主链路验证

涉及以下内容时，优先怀疑环境边界，而不是先判断代码坏了：

- 真实浏览器
- 扩展
- Bridge 服务
- 登录态
- CDP
- localhost 服务
- OrbStack VM 到宿主机访问
- systemd 服务环境变量
- 代理
- 图片或媒体缓存下载

如果关键验证出现以下现象：

- 空结果
- 假成功
- 骨架页
- 读不到真实页面
- 看不到宿主浏览器状态
- curl 在沙箱中失败但宿主可能可用
- workflow 新开页面后又关闭导致 targetId 为空

不要立刻下结论。  
应按 `LOCAL_DEV.md` 的宿主侧验证方式重试。

---

## 修改后的操作纪律

修改 `extension/` 后：

- 运行 `./scripts/dev_reload_extension.sh`（该脚本先同步文件到宿主机，再触发扩展自重载，最后刷新目标页面——三步原子操作，不可拆分或跳过）
- 不要请求用户手动在 `edge://extensions` 中重载——脚本已自动完成
- 如果脚本报错，按 `.agents/quality-gates.md` 排查，而不是立即请求人工介入
- 至少验证一个站点语义读取
- 不要只看文件保存结果就宣布完成

修改 `bridge/app/` 后：

- 按 `LOCAL_DEV.md` 和 `.agents/quality-gates.md` 重启 Bridge
- 运行相关健康检查
- 涉及 workflow 或站点行为时，做对应真实链路验证

修改文档后：

- 按 `.agents/quality-gates.md` 做文档检查
- 不要把本地机器事实写入公开文档
- 不要把临时决策写成长期规则

修改或新增 `skills/` 后：

- 将对应 skill 目录完整复制到 `/home/cuiguidong/workspace/AI/agent-workflow/skills/personal-tools/`，覆盖同名目录
- 新建 skill 时同步创建，修改已有 skill 时同步覆盖
- 目标目录是 Agent 工作流的运行时 skill 来源，必须保持与本项目 `skills/` 一致

需要用户配合的动作未完成前，不给出最终测试结论。

---

## 浏览器调试方式

页面研究、交互探测、发布流程调试时：

- 优先通过现有 Bridge / Browser Runtime（以 NativeBrowserRuntime 作为主路径）控制宿主机真实浏览器
- 调试尽量低频、串行
- 先确认一次导航结果
- 再逐步追加采样
- 不要一次性大批量打开页面或高频调用
- workflow 新开临时页并关闭时，不要把 `targetId: null` 直接判断为失败

想稳定观察页面结构时：

- 可以先手动打开页面
- 再用指定 `targetId` 做定向读取
- 不要让自动 workflow 的临时页关闭策略干扰判断

---

## 安全边界

以下动作必须保持人工确认边界：

- 登录
- 登出
- 2FA / MFA
- 验证码
- 改密码
- 改邮箱
- 改手机号
- 支付
- 转账
- 发布内容
- 删除内容
- 第三方授权
- 账号绑定或解绑

默认策略：

- 可以准备
- 可以填写
- 可以预览
- 可以校验
- 不自动点击最终确认按钮

---

## 文档与计划归属

文档归属必须清楚：

- 公开项目说明：`README.md`
- 正式架构：`docs/architecture.md`
- 实现细节：`docs/development.md`
- API：`docs/interfaces.md`
- 站点支持：`docs/capabilities.md`
- 新站点适配：`docs/new-site-adaptation-guide.md`
- 本地机器事实：`LOCAL_DEV.md`
- 架构约束：`.agents/invariants.yaml`
- 验证规则：`.agents/quality-gates.md`
- 当前任务：`.agents/task-board.yaml`
- 跨项目合同：`docs/contracts/`
- 临时计划、运行时审计日志、草案：`temp/`

不要把同一类信息复制到多个文件里长期维护。  
如果必须重复摘要，只写入口级提示，并指向单一事实源。

---

## CLAUDE.md 兼容策略

本项目以 `AGENTS.md` 作为唯一 Agent 入口文件。

`CLAUDE.md` 只用于兼容 Claude Code，不维护第二套规则。  
如果需要 Claude Code 读取本文件，应在 `CLAUDE.md` 中使用 `@AGENTS.md` 导入。

不要在 `CLAUDE.md` 里复制本文件内容。  
不要让 `AGENTS.md` 与 `CLAUDE.md` 分叉。
