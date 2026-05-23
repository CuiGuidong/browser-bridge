# 文档导航

本文件是项目文档的角色索引，帮助开发者和 Agent 快速定位正确的信息源。

## 入口文件

| 文件 | 读者 | 用途 |
|------|------|------|
| `README.md` | 人类 | 项目定位、快速开始、文档导航 |
| `AGENTS.md` | Agent | 路由规则、接手顺序、工作纪律、架构红线 |
| `CLAUDE.md` | Claude Code | 工具适配层，导入 `AGENTS.md` |
| `LOCAL_DEV.md` | 维护者 | 本机宿主环境事实（不进入公开仓库） |

## docs/ — 项目知识库

| 文件 | 权威范围 | 说明 |
|------|----------|------|
| `architecture.md` | 正式架构约束 | 分层职责、核心原则、数据模型、扩展指南 |
| `development.md` | 开发指南 | 前置条件、安装、启动、开发工作流、调试方法、避坑点 |
| `operations.md` | 运维指南 | systemd 服务管理、环境变量、代理、故障排查 |
| `interfaces.md` | 接口参考 | HTTP API、workflow 参数、站点能力声明 |
| `capabilities.md` | 站点能力矩阵 | 支持的站点、能力、输入形态、当前限制 |
| `new-site-adaptation-guide.md` | 新站点适配流程 | adapter / workflow / skill 落点、开发 SOP |
| `video-asset-pipeline-design.md` | 视频管线设计 | B 站/抖音视频理解管线草案（暂不实现） |

## .agents/ — Agent 协作层

| 文件 | 用途 |
|------|------|
| `context.md` | Agent 接手摘要，当前项目状态快照 |
| `invariants.yaml` | 架构硬约束、禁止模式、不可破坏的边界 |
| `quality-gates.md` | 按改动类型的验证矩阵 |
| `task-board.yaml` | 当前任务状态（已完成、进行中、待办） |
| `task-template.md` | 新建任务的模板 |
| `specs/` | 设计规格 |
| `plans/` | 实施计划 |
| `reviews/` | 审查报告 |
| `handoff/` | 会话交接文档 |

## 跨项目参考

| 文件 | 用途 |
|------|------|
| `temp/media-agent-suite-contract.md` | 与 media-agent-suite 的接口合同 |

## 读取顺序

**首次接手**：`AGENTS.md` → `LOCAL_DEV.md` → `README.md` → `docs/index.md` → `docs/architecture.md` → `docs/development.md` → `.agents/context.md` → `.agents/invariants.yaml` → `.agents/task-board.yaml`

**按任务深入**：

- 涉及 API → `docs/interfaces.md`
- 涉及站点能力 → `docs/capabilities.md`
- 涉及新增站点 → `docs/new-site-adaptation-guide.md`
- 涉及视频/媒体 → `docs/video-asset-pipeline-design.md`
- 涉及部署运维 → `docs/operations.md`
- 涉及跨项目调用 → `temp/media-agent-suite-contract.md`
