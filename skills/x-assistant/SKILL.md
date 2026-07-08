---
name: x-assistant
description: >-
  Use this skill whenever the user asks anything about X (Twitter): reading posts,
  searching, home feed, bookmarks, following or unfollowing users, and adding or removing bookmarks.
  Hard triggers include any x.com/twitter.com URL, "read this tweet/post/thread", "看这条推文",
  "X搜索", "首页时间线", "书签", "关注作者", "取关", "加书签", and "移除书签".
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
  - 可用 `--comment-limit N` 调整返回的一级评论上限，默认 20；workflow 会尝试滚动加载更多评论，但不保证拿到平台全量评论

- 在 X 搜索：
  `python3 skills/x-assistant/scripts/search.py "<keyword>"`

- 查看首页时间线：
  `python3 skills/x-assistant/scripts/feed.py [for_you|following|both] [count]`

- 查看书签列表：
  `python3 skills/x-assistant/scripts/bookmarks.py [count]`

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

## 4. ⚠️ 图片处理规则

- 帖子正文包含 `[Image: URL]` 标签以标明图片位置。本脚本不下载图片，图片本地化由调用方或归档流程自行处理。
- 阅读时以正文图片标签顺序为准；debug/raw 中的 media[] 作为资产清单，不改变正文顺序语义。
- 识图时，按当前 Agent 环境选择可用图片读取方式。如工具只支持本地文件，可先下载到 /tmp 下的任务目录，识别完成后删除。

## 5. 输出要求

- 脚本返回的是 JSON
- `read_post.py` 默认只返回精简语义结果，不包含 `page/signals/debug/rawPayload/targetId`
- 优先提取结构化字段，不要只复述整段文本
- 阅读类请求要总结核心内容
- 动作类请求要明确：
  - `changed`
  - `verified`
  - 目标是谁或哪条推文

## 6. ⚠️ 视频下载与处理规则

- 帖子正文如果包含 `[Video | Poster: URL]` 标签，表示该帖子含有视频。其中 `URL` 为视频的海报/封面图片。
- X 平台主推文长视频在未播放前在 DOM 中并不存在真正的 `<video>` 标签，且播放时使用的是 blob 加密流。因此本适配器底座不提供真实的视频下载链接。
- 如果用户要求下载视频，请引导或直接调用专门的视频下载 Skill/工具（如基于 `yt-dlp` 的下载工具），传入推文本身的 URL（例如 `https://x.com/username/status/statusId`）进行视频提取与下载。

