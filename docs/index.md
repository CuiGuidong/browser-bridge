# 文档导航

本文件是公开项目文档的角色索引，帮助用户、开发者和集成方快速定位正确的信息源。

## 入口文件

| 文件 | 读者 | 用途 |
|------|------|------|
| [../README.md](../README.md) | 用户 | 项目定位、快速开始、能力概览、文档入口 |
| [installation.md](installation.md) | 用户 | macOS、Windows + WSL、Linux 单机安装 |
| [interfaces.md](interfaces.md) | 集成方 | HTTP API、workflow 参数、返回结构、错误结构 |
| [development.md](development.md) | 开发者 | 本地开发、调试、验证、扩展重载和避坑点 |
| [operations.md](operations.md) | 运维者 | 服务管理、环境变量、诊断和故障排查 |

## docs/ — 项目知识库

| 文件 | 权威范围 | 说明 |
|------|----------|------|
| [architecture.md](architecture.md) | 正式架构约束 | 分层职责、核心原则、数据模型、扩展指南 |
| [capabilities.md](capabilities.md) | 站点能力矩阵 | 支持的站点、能力、输入形态、当前限制 |
| [new-site-adaptation-guide.md](new-site-adaptation-guide.md) | 新站点适配流程 | adapter / workflow / skill 落点、开发 SOP |
| [video-asset-pipeline-design.md](video-asset-pipeline-design.md) | 视频管线设计 | B 站/抖音视频理解管线草案 |

## 本机协作文件

维护者可以在本地使用被 `.gitignore` 忽略的 `AGENTS.md`、`CLAUDE.md`、`LOCAL_DEV.md`、`agents/` 和 `docs/contracts/` 记录 Agent 约束、本机环境事实、任务状态、过程产物和跨项目协作合同。

这些文件不属于公开安装和集成说明，不应作为开源用户的使用前置条件，也不应包含在普通贡献提交中。

## 读取顺序

首次使用：

1. [../README.md](../README.md)
2. [installation.md](installation.md)
3. [operations.md](operations.md)

集成调用：

1. [../README.md](../README.md)
2. [interfaces.md](interfaces.md)
3. [capabilities.md](capabilities.md)

修改代码：

1. [architecture.md](architecture.md)
2. [development.md](development.md)
3. [operations.md](operations.md)
4. 按任务需要阅读 [interfaces.md](interfaces.md)、[capabilities.md](capabilities.md) 或 [new-site-adaptation-guide.md](new-site-adaptation-guide.md)
