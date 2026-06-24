---
name: weibo-assistant
description: >-
  Use this skill whenever the user asks anything about Weibo: reading the home feed,
  reading hot feeds or hot search lists, searching Weibo, and reading a single post from
  PC/mobile/share links.
  
  ⚠️ CRITICAL: When viewing images from post output, you MUST use the `read` tool, NOT `image` tool.
  The `image` tool cannot access `/tmp/browser-bridge-cache/` directory. Always use `read(file_path="...")`.
version: 1.0.0
---

# Weibo Assistant

## 1. 路由规则

- 读取首页微博流：
  `python3 skills/weibo-assistant/scripts/read_home.py [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 读取热门微博流：
  `python3 skills/weibo-assistant/scripts/read_hot_feed.py [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 读取热搜榜：
  `python3 skills/weibo-assistant/scripts/read_hot_search.py [count]`

- 读取单条微博：
  `python3 skills/weibo-assistant/scripts/read_post.py "<url|share_text>"`
  - 默认输出 `read_post.v1` 语义模型：`contentItem`、`thread`、`comments`、`platform`
  - 开发排障用 `--raw` 查看 Bridge 原始 payload
  - 需要语义结果加诊断摘要时用 `--debug`
  - 可用 `--comment-limit N` 调整返回的已采集一级评论上限，默认 20；当前不承诺自动加载更多评论
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 搜索微博：
  `python3 skills/weibo-assistant/scripts/search.py "<keyword>" [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

## 2. 范围与约束

- 当前只做只读能力
- 固定流程优先走 bridge workflow
- `read_post.py` 兼容多种微博分享链接输入
- 不在 skill 层做最终跳转解析，交给真实浏览器落地

## 3. 输出要求

- 首页/热门流/搜索返回结构化 `items`
- 热搜榜返回榜单 `items`
- 单帖默认返回精简 `read_post.v1` 语义结果，不包含 `page/signals/debug/rawPayload/targetId`
- 单帖优先读取：
  - `contentItem.author`
  - `contentItem.published`
  - `contentItem.text`
  - `contentItem.media`
  - `contentItem.metrics`
  - `comments.items`

## 4. ⚠️ 图片处理（重要）

当微博正文包含图片标签时，底层 workflow 会把：

`[Image: URL]`

替换成：

`[Image Local: /tmp/browser-bridge-cache/xxxx.jpg | Remote: https://...]`

### 正确的读取方式

需要看图时，**必须使用 `read` 工具读取 `Local` 路径**：
```
read(file_path="/tmp/browser-bridge-cache/xxxx.jpg")
```

### ❌ 错误 vs ✅ 正确

| ❌ 错误 | ✅ 正确 |
|--------|--------|
| `image(file_path="/tmp/browser-bridge-cache/xxxx.jpg")` | `read(file_path="/tmp/browser-bridge-cache/xxxx.jpg")` |

**原因**：`image` 工具无法访问 `/tmp/browser-bridge-cache/` 目录，只有 `read` 工具可以。

**再次强调**：看到 `[Image Local: ...]` 时，用 `read` 工具，不要用 `image` 工具。
