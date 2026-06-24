---
name: zhihu-assistant
description: >-
  Use this skill whenever the user asks anything about Zhihu (知乎): reading a post
  (question/answer/article), reading the hot list, searching Zhihu, reading user profile
  metrics, and checking login status. Hard triggers include any zhihu.com URL, "知乎",
  "知乎搜索", "知乎热榜", "读这篇知乎", "看这个回答", "知乎主页".

  ⚠️ CRITICAL: When viewing images from post output, you MUST use the `read` tool, NOT `image` tool.
  The `image` tool cannot access `/tmp/browser-bridge-cache/` directory. Always use `read(file_path="...")`.
version: 1.0.0
---

# Zhihu Assistant

## 1. 路由规则

- 读取知乎单帖（问题/回答/文章）：
  `python3 skills/zhihu-assistant/scripts/read_post.py "<url>"`
  - 默认输出 `read_post.v1` 语义模型：`contentItem`、`thread`、`comments`、`platform`
  - 开发排障用 `--raw` 查看 Bridge 原始 payload
  - 需要语义结果加诊断摘要时用 `--debug`
  - 可用 `--comment-limit N` 调整返回的已采集一级评论上限，默认 20；当前不承诺自动加载更多评论
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 读取知乎热榜：
  `python3 skills/zhihu-assistant/scripts/read_hot.py [count]`

- 搜索知乎：
  `python3 skills/zhihu-assistant/scripts/search.py "<keyword>" [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 读取用户/机构主页指标：
  `python3 skills/zhihu-assistant/scripts/read_profile.py "<url>"`

- 检查知乎登录状态：
  `python3 skills/zhihu-assistant/scripts/account_status.py`

## 2. 范围与约束

- 当前只做只读能力，无写入/关注/点赞等动作
- 固定流程优先走 bridge workflow
- `read_post.py` 兼容知乎问题页、回答页、文章页 URL
- 支持的 URL 形态：
  - `https://www.zhihu.com/question/<id>`
  - `https://www.zhihu.com/question/<id>/answer/<id>`
  - `https://zhuanlan.zhihu.com/p/<id>`
  - `https://www.zhihu.com/p/<id>`
  - `https://www.zhihu.com/people/<slug>`
  - `https://www.zhihu.com/org/<slug>`

## 3. 输出要求

- 热榜/搜索返回结构化 `items`
- 单帖默认返回精简 `read_post.v1` 语义结果，不包含 `page/signals/debug/rawPayload/targetId`
- 单帖优先读取：
  - `contentItem.title`
  - `contentItem.author`
  - `contentItem.text`
  - `contentItem.metrics`
  - `platform.specific.questionDescription`
  - `comments.items`
- 用户主页返回：
  - `followers`
  - `following`
  - `posts`
  - `recentPosts`

## 4. ⚠️ 图片处理（重要）

当知乎正文包含图片标签时，底层 workflow 会把：

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
