# media-agent-suite 协作合同

本文档是 `browser-bridge` 侧维护的跨项目协作合同，记录 `media-agent-suite` 对浏览器执行基座的能力需求、支持状态和验收结论。

对应的需求源在：

```text
/home/cuiguidong/workspace/personal/projects/Python/media-agent-suite/docs/contracts/browser-bridge-adaptation.md
```

## 协作边界

- `media-agent-suite` 只能通过 browser-bridge HTTP API 调用浏览器页面能力。
- `media-agent-suite` 不直接操作浏览器、CDP、扩展、tab、DOM selector 或第三方平台 API。
- 缺少基座能力时，`media-agent-suite` 侧新增需求条目，不在业务系统内绕过实现。
- `browser-bridge` 侧只交付通用页面能力、站点语义、固定 workflow、错误结构和能力发现。
- 选题、文案、复盘、业务状态机、指标入库和运营决策仍归 `media-agent-suite`。

## Issue-Like 条目格式

跨会话或跨 Agent 沟通时，使用类似 GitHub issue 的条目。每个条目必须能被另一个会话独立理解和验收。

```markdown
### BB-MAS-YYYYMMDD-序号：一句话标题

- 状态：proposed | accepted | in_progress | blocked | delivered | verified | closed
- 提出方：media-agent-suite | browser-bridge
- 负责人：browser-bridge | media-agent-suite | 待定
- 优先级：high | medium | low
- 需求来源：media-agent-suite docs/contracts/browser-bridge-adaptation.md 对应条目
- 问题描述：现象、错误、缺失能力或具体数据样例
- 期望合同：endpoint/workflow、params、返回字段、错误码或能力发现要求
- 边界说明：哪些内容不属于本条目，特别是业务逻辑和高风险动作
- 验收方式：命令、HTTP 示例、真实浏览器 smoke、单元测试或文档检查
- 最新进展：按时间追加，不覆盖历史
```

## 当前活跃条目

（暂无）

## 已交付能力摘要

| 能力 | browser-bridge 合同 | media-agent-suite 用途 | 状态 |
|------|---------------------|------------------------|------|
| 热榜和关键词搜索 | `read_trending` / `read_hot_search` / `search` 等 workflow | 热点发现和关键词发现 | verified |
| 小红书准备发布 | `xiaohongshu.prepare_publish_post` | 发布任务进入人工确认前状态 | verified |
| 主页指标读取 | `read_profile_metrics` | 对标博主主页快照 | verified |
| 作品读取和指标读取 | `read_post` / `read_post_metrics` | 作品解析、指标采集、URL 归因 | verified |
| 能力发现 | `GET /site/capabilities` | 业务系统判断缺失能力并给出明确错误 | verified |
| 结构化错误 | `/workflow/run`、`/site/read`、`/site/action` error envelope | 区分能力缺失、登录态、人确认和 workflow 失败 | verified |

## 维护规则

- `media-agent-suite` 侧新增需求后，应在本文件的“当前活跃条目”创建或同步对应条目。
- `browser-bridge` 侧实现后，把条目状态改为 `delivered`，并记录接口、字段、错误码和验证证据。
- `media-agent-suite` 验收通过后，把状态改为 `verified` 或 `closed`，并在两边文档中清理“当前活跃需求”。
- 如果能力请求会触发发布、删除、支付、授权、验证码、MFA 或账号安全边界，默认要求人工确认，不能把最终高风险动作做成自动执行。
- 本文件只记录跨项目合同，不记录业务产品规划、运营策略或临时调试过程。
