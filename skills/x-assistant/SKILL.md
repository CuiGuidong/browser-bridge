---
name: x-assistant
description: >-
  Use this skill whenever the user asks anything about X (Twitter) content retrieval.
  Hard triggers include any x.com/twitter.com URL, "read this tweet/post/thread",
  "看这条推文", "阅读推文", "总结这条X", "X搜索", "搜推文", "看首页时间线", and "for you/following".
  Route single-post reads to scripts/read_post.py first, searches to scripts/search.py,
  and home feed reads to scripts/feed.py. Prefer this skill over generic web reading for X tasks.
version: 1.1.0
---

# X (Twitter) Smart Assistant

## 1. 路由执行规则 (Routing Rules)

命中以下场景时，直接执行对应的专属脚本：

*   **场景 A：用户提供推文链接 (含 `/status/`)，或要求“阅读这条推文”**
    *   **执行：** `python3 skills/x-assistant/scripts/read_post.py "<URL>"`

*   **场景 B：在 X 上搜索内容 (例如：“搜一下关于 xxx 的讨论”)**
    *   **执行：** `python3 skills/x-assistant/scripts/search.py "<keyword>"`
    *   *说明：* 对宽泛概念（如“AI智能体”），须将其拆解为中英双语精准关键词（如 "AI Agents" 和 "AI智能体"），分多次调用本脚本，最后由你合并去重。一次任务最多搜索 3 次。

*   **场景 C：查看首页、刷时间线 (例如：“看看今天 X 上有什么新鲜事”)**
    *   **执行：** `python3 skills/x-assistant/scripts/feed.py [for_you|following|both] [count]`

## 2. 多模态与图片阅读 (Vision & Images)

当推文包含配图时，底层脚本已在后台异步下载这些图片，并在 JSON 文本中插入双锚点标签：
`[Image Local: /tmp/browser-bridge-cache/xxxx.jpg | Remote: https://...]`

*   **看图机制：** 请根据用户的需求，自行判断是否需要查看图片内容来辅助回答问题。你可以直接读取标签中的 `Local` 绝对路径来获取图片。

## 3. 数据处理与输出要求

1. 脚本会返回结构化的 JSON 数据。
2. 请解析 JSON 并提取核心信息（如 `text`, `authorInfo`）。
3. 根据用户的提问，用自然、流畅的语言（如 Markdown、列表）进行总结或解答。