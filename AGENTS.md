# AGENTS

## 验证宿主链路

- 涉及真实浏览器、扩展、Bridge、本地登录态、`host.orb.internal`、`127.0.0.1:17777`、CDP attach 的脚本或命令验证时，不要先根据沙箱内失败结论判断脚本或服务异常。
- 如果关键验证命令在沙箱内出现 `Failed to open post page`、空结果、假成功、看不到宿主浏览器状态等现象，应尽快按同一命令申请提权到宿主侧重试。
- 本项目已验证过：`python3 skills/x-assistant/scripts/read_post.py "<x-status-url>"` 在沙箱内可能失败，但提权到宿主侧后可成功读取；后续验证同类脚本时应优先提权，避免误判。

## 调试前置动作

- 一旦修改 `extension/` 下任意文件，必须先停下来请求用户执行“重载扩展 + 刷新目标页面”，用户确认完成前不要继续给出测试结论。
- 一旦修改 `bridge/app/` 下会参与服务运行的代码，必须先停下来请求用户重启 bridge 服务，用户确认完成前不要继续给出测试结论。
- 需要重载扩展或重启 bridge 时，Agent 不应自行假设已完成，应明确向用户求助并等待确认后再继续测试。

## 浏览器调试方式

- 涉及页面研究、交互探测、发布流程调试时，优先通过 CDP/Bridge 控制宿主机真实浏览器（`127.0.0.1:17777`），不要改用内置浏览器工具替代主链路验证。
- 调试节奏保持低频、串行；先做一次导航，再按需逐步采样，不要并发或高频重复访问页面。

## 开发计划导航

- 小红书图文发帖 Plan：[/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/temp/xiaohongshu-publish-plan.md](file:///home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/temp/xiaohongshu-publish-plan.md)
- 小红书图文发帖 Tasks：[/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/temp/xiaohongshu-publish-task.md](file:///home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/temp/xiaohongshu-publish-task.md)
