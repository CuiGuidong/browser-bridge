# AGENTS

## 验证宿主链路

- 涉及真实浏览器、扩展、Bridge、本地登录态、`host.orb.internal`、`127.0.0.1:17777`、CDP attach 的脚本或命令验证时，不要先根据沙箱内失败结论判断脚本或服务异常。
- 如果关键验证命令在沙箱内出现 `Failed to open post page`、空结果、假成功、看不到宿主浏览器状态等现象，应尽快按同一命令申请提权到宿主侧重试。
- 本项目已验证过：`python3 skills/x-assistant/scripts/read_post.py "<x-status-url>"` 在沙箱内可能失败，但提权到宿主侧后可成功读取；后续验证同类脚本时应优先提权，避免误判。
