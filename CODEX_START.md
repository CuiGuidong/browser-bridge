# 给 Codex / AI Coding Agent 的开场白

下面这段可以直接复制给新会话。

---

你现在接手 `browser-bridge-project`。

这是一个本地真实浏览器执行基座，目标是让 Agent、skill、脚本和外部业务系统通过 HTTP API 使用真实浏览器、真实登录态和浏览器扩展完成页面读取、站点语义操作和固定 workflow。

请先不要写代码，先按顺序阅读：

1. `AGENTS.md`
2. `LOCAL_DEV.md`
3. `README.md`
4. `docs/architecture-spec.md`
5. `docs/implementation-guide.md`
6. `harness/context.md`
7. `harness/invariants.yaml`
8. `harness/task-board.yaml`

重要边界：

- CDP 只负责浏览器控制和诊断。
- 站点 DOM 语义只放在 extension adapter。
- 固定流程放在 workflow。
- skill 不重新接管页面生命周期。
- 外部业务系统不依赖 DOM、selector、tab、CDP 或扩展内部细节。
- 高风险动作默认需要人工确认。

本地验证基线：

```bash
curl --noproxy '*' -sS http://127.0.0.1:17777/health
python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'
```

修改纪律：

- 改 `extension/` 后运行 `./scripts/dev_reload_extension.sh`
- 改 `bridge/app/` 后重启 `browser-bridge.service`

请先完成：

1. 检查当前 task-board。
2. 确认宿主链路是否可用。
3. 从最高优先级 `todo` 任务开始制定最小修改计划。
4. 按 `harness/quality-gates.md` 验证。
5. 更新任务状态或说明未完成原因。

每次输出请包含：

- 本次目标
- 修改文件
- 验证方式
- 是否符合 `harness/invariants.yaml`
