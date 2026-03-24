# 异步图片预载系统 (Async Image Preloader) 任务清单

_本文档为下一步 AI Agent 接手开发时的行动指南。_

## 任务目标
实现确定性的双标签文本替换机制，并增加一个非阻塞的后台图片下载守护进程，实现极速且无感的多模态视觉闭环。

## 执行步骤

- [ ] **步骤 1：创建后台下载器脚本**
  - 创建 `skills/x-assistant/scripts/async_image_downloader.py`。
  - 逻辑要求：接收通过系统参数 (sys.argv) 或标准输入传入的 `URL -> 本地路径` 映射对。
  - 具备缓存检查：如果目标路径文件已存在，直接跳过下载。
  - 具备并发下载能力：使用 `urllib` 多线程下载指定的 URL。
  - 具备缓存清理能力：运行之初，顺手扫描 `/tmp/browser-bridge-cache/` 目录，删除修改时间超过 24 小时的旧图片文件。

- [ ] **步骤 2：在核心脚本中实现正则替换与分离拉起**
  - 修改 `skills/x-assistant/scripts/read_post.py` (后续推广到 feed/search)。
  - 在获取到文本后，编写正则表达式查找所有 `\[Image: (https://pbs\.twimg\.com/media/[^\]]+)\]`。
  - 根据提取到的 URL，计算 MD5 和格式后缀（默认 `.jpg`，也可从 `format=` 解析）。
  - 生成 `[Image Local: /tmp/browser-bridge-cache/<MD5>.jpg | Remote: URL]` 并替换原文。
  - 整理出需要下载的列表，使用 `subprocess.Popen` 以脱离进程组的方式静默启动 `async_image_downloader.py`。
  
- [ ] **步骤 3：验证与联调**
  - 运行 `python3 skills/x-assistant/scripts/read_post.py "https://x.com/i/status/2036116722084974791"`。
  - 检查终端返回的 JSON 是否极速输出且包含 `[Image Local: ... | Remote: ...]`。
  - 检查几秒钟后，`/tmp/browser-bridge-cache/` 目录下是否真的出现了对应的图片文件。

- [ ] **步骤 4：更新 SKILL.md**
  - 在 `SKILL.md` 中补充说明，告诉 Agent：如果你在报文中看到了 `[Image Local: <path> | Remote: <url>]`，并且你需要查看图片，请直接使用系统的读取文件工具读取 Local 路径。如果失败再尝试自行获取 Remote 链接。

- [ ] **步骤 5：收尾提交**
  - 将架构思想补充进 `docs/implementation-guide.md`（可覆盖掉之前关于 Base64 的旧讨论）。
  - 提交 Git Commit。
  - 清理本 `docs/temp/` 下的两个规划与任务文档。