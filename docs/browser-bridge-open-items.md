# Browser Bridge 待确认 / 待补充事项

_Last updated: 2026-03-13_
_Status: active_

> 这是开发期间的集中待确认清单。

## 当前待确认项

### 1. Bridge 运行方式
- 当前 Phase 2 使用 Python 本地 HTTP 服务。
- 后续需确认：最终是长期常驻进程、手动启动脚本，还是 service 化。
- 当前处理：继续按手动启动 + 本地调试推进。

### 2. FastAPI / 标准库
- 当前 skeleton 用的是 Python 标准库 `http.server`。
- 现在功能闭环已基本打通，后续需判断是否升级到 FastAPI + uvicorn，以提升扩展性、调试体验和后续维护质量。
- 当前处理：暂未迁移。

### 3. Open URL 语义
- 当前 `open` 默认新开 target/tab。
- 后续需确认：是否还需要支持“在现有 tab 导航到新 URL”。
- 当前处理：保持“新开 tab”语义。

### 4. Activate 语义
- CDP activate 不一定等价于桌面层绝对前台焦点。
- 后续需确认：是否需要额外桌面层焦点保障。
- 当前处理：只保证 CDP target activate 语义。

### 5. 页面读取深度
- 当前已实现：
  - 轻量 `page-info`
  - `page-content`（基于 `document.body.innerText`）
- 后续需确认：下一阶段优先做 DOM 查询接口、结构化元素检索，还是直接进入点击/输入能力。
- 当前处理：页面观察能力已具备基础版本。

### 6. 最终 bridge 对外接口稳定性
- 后续需确认：是否把当前 Phase 2 API 视为长期契约，还是允许在后续阶段调整。
- 当前处理：按内部 API 看待，不承诺稳定到最终版。

### 7. Edge 启动方式
- 当前默认由用户手动启动宿主 Mac 上真实 Edge，并带 remote debugging 参数。
- 后续需确认：是否需要 agent 辅助生成启动脚本/别名，或保持人工手动启动。
- 当前处理：保持人工手动启动。

### 8. 真正的定时心跳
- 用户提出希望建立 5 分钟心跳来提醒持续推进项目。
- 当前处理：先采用项目内“心跳自检”约定，不直接改宿主机计划任务或系统调度。
- 后续需确认：是否需要真正落地到系统级 cron / heartbeat / OpenClaw 周期机制。
