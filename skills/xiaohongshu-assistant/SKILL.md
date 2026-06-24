---
name: xiaohongshu-assistant
description: >-
  Use this skill whenever the user asks anything about Xiaohongshu (RED / 小红书):
  reading a note, reading the home recommendation feed, or searching by keyword.
  Hard triggers include any xiaohongshu.com URL, "小红书", "读这篇小红书", "读笔记",
  "小红书首页", "小红书搜索", and "搜索小红书".
  
  ⚠️ CRITICAL: When viewing images from note output, you MUST use the `read` tool, NOT `image` tool.
  The `image` tool cannot access `/tmp/browser-bridge-cache/` directory. Always use `read(file_path="...")`.
version: 1.0.0
---

# Xiaohongshu Assistant

## 1. 路由规则

命中以下场景时，直接执行对应脚本：

- 阅读单篇小红书笔记：
  `python3 skills/xiaohongshu-assistant/scripts/read_post.py "<URL|note_id|share_text>"`
  - 默认输出 `read_post.v1` 语义模型：`contentItem`、`thread`、`comments`、`platform`
  - 开发排障用 `--raw` 查看 Bridge 原始 payload
  - 需要语义结果加诊断摘要时用 `--debug`
  - 可用 `--comment-limit N` 调整返回的已采集一级评论上限，默认 20；当前不承诺自动加载更多评论
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 查看小红书首页推荐：
  `python3 skills/xiaohongshu-assistant/scripts/home.py [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 在小红书搜索：
  `python3 skills/xiaohongshu-assistant/scripts/search.py "<keyword>" [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 准备图文发布（停在发布前，不点击发布）：
  `python3 skills/xiaohongshu-assistant/scripts/prepare_publish.py "<title>" "<content>" "<image_path>" [more_image_paths...]`

## 2. 范围与约束

- 只支持网页版小红书
- 默认依赖真实浏览器已登录状态
- 当前支持只读能力，以及图文发布前准备能力
- 不做点赞、收藏、关注、评论等状态变更动作
- 发帖链路默认停在最终“发布”按钮前，等待人工确认

`read_post.py` 当前支持这些输入形态：

- 纯 `note_id`
- PC 长链接
- `xhslink.com` 短链
- 带分享文案的整段文本

短链处理原则：

- skill 负责从输入中提取 URL
- 最终跳转解析交给真实浏览器完成
- 不在 skill 里额外做短链 HTTP 解析

## 3. 输出要求

- 脚本返回 JSON
- 阅读笔记默认返回精简 `read_post.v1` 语义结果，不包含 `page/signals/debug/rawPayload/targetId`
- 阅读笔记时优先提取：
  - `contentItem.title`
  - `contentItem.author`
  - `contentItem.text`
  - `contentItem.media`
  - `contentItem.metrics`
  - `comments.items`
- 首页和搜索优先提取：
  - `title`
  - `author`
  - `excerpt`
  - `cover`
  - `url`
- 准备发布优先返回：
  - `targetId`
  - `pageType`
  - `activeTab`
  - `titleLength`
  - `contentLength`
  - `checkpoint.awaitingManualPublish`

## 4. 图片处理

当笔记正文包含图片标签时，底层 workflow 会把：

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

如果是视频笔记，当前只会保留视频标记或 `videos` 字段，不缓存视频文件。
