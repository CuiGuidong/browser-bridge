---
name: x-assistant
description: >-
  Use this skill whenever the user asks anything about X (Twitter): reading posts,
  searching, home feed, bookmarks, following or unfollowing users, and adding or removing bookmarks.
  Hard triggers include any x.com/twitter.com URL, "read this tweet/post/thread", "看这条推文",
  "X搜索", "首页时间线", "书签", "关注作者", "取关", "加书签", and "移除书签".
  
  ⚠️ CRITICAL: When viewing images from tweet output, you MUST use the `read` tool, NOT `image` tool.
  The `image` tool cannot access `/tmp/browser-bridge-cache/` directory. Always use `read(file_path="...")`.
version: 2.1.0
---

# X Assistant

## 1. 路由规则

命中以下场景时，直接执行对应脚本：

- 阅读单条推文：
  `python3 skills/x-assistant/scripts/read_post.py "<URL>"`
  - 默认输出 `read_post.v1` 语义模型：`contentItem`、`thread`、`comments`、`platform`
  - 开发排障用 `--raw` 查看 Bridge 原始 payload
  - 需要语义结果加诊断摘要时用 `--debug`
  - 可用 `--comment-limit N` 调整返回的已采集一级评论上限，默认 20；当前不承诺自动加载更多评论
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 在 X 搜索：
  `python3 skills/x-assistant/scripts/search.py "<keyword>"`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 查看首页时间线：
  `python3 skills/x-assistant/scripts/feed.py [for_you|following|both] [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 查看书签列表：
  `python3 skills/x-assistant/scripts/bookmarks.py [count]`
  - ⚠️ 若输出含 `[Image Local: ...]`，**必须用 `read` 工具读取**，不能用 `image` 工具

- 关注用户：
  `python3 skills/x-assistant/scripts/follow_user.py "<handle|profile_url>"`

- 取消关注用户：
  `python3 skills/x-assistant/scripts/unfollow_user.py "<handle|profile_url>"`

- 添加书签：
  `python3 skills/x-assistant/scripts/add_bookmark.py "<post_url>"`

- 移除书签：
  `python3 skills/x-assistant/scripts/remove_bookmark.py "<post_url>"`

当前这些固定读取/动作流程都已下沉到 Bridge workflow。

## 2. 上下文推断

当用户说这些相对指代时，可以优先从当前对话里最近一次 X 结果推断：

- “关注作者 / follow 这个作者”
- “取消关注这个作者”
- “把这条加入书签”
- “把这条从书签移除”

推断规则：

- 如果上一条是 `read_post.py` 默认结果，优先使用其中的 `contentItem.author.handle` 或 `contentItem.url`
- 如果上一条是搜索、时间线、书签列表结果，只有在用户明确指向某一条时才执行
- 如果指向不明确，就先问一个简短澄清问题，不要猜

## 3. 风险与约束

- `follow_user`、`unfollow_user`、`add_bookmark`、`remove_bookmark` 都会改账号状态
- 这些动作已经有桥端节流和操作日志，但仍应保持低频
- 执行状态变更动作后，应在答复里明确说出：
  - 是否真的发生变化
  - 是否验证成功

## 4. ⚠️ 图片处理（重要）

当推文正文包含图片标签时，底层脚本会把：

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

## 5. 输出要求

- 脚本返回的是 JSON
- `read_post.py` 默认只返回精简语义结果，不包含 `page/signals/debug/rawPayload/targetId`
- 优先提取结构化字段，不要只复述整段文本
- 阅读类请求要总结核心内容
- 动作类请求要明确：
  - `changed`
  - `verified`
  - 目标是谁或哪条推文
