---
name: xiaohongshu-assistant
description: >-
  Use this skill whenever the user asks anything about Xiaohongshu (RED / 小红书):
  reading a note, reading the home recommendation feed, or searching by keyword.
  Hard triggers include any xiaohongshu.com URL, "小红书", "读这篇小红书", "读笔记",
  "小红书首页", "小红书搜索", and "搜索小红书".
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
  - 仅保留远程 `[Image: URL]` 标签，无本地路径

- 查看小红书首页推荐：
  `python3 skills/xiaohongshu-assistant/scripts/home.py [count]`
  - 列表输出仅保留远程 `[Image: URL]` 标签，无本地路径

- 在小红书搜索：
  `python3 skills/xiaohongshu-assistant/scripts/search.py "<keyword>" [count]`
  - 列表输出仅保留远程 `[Image: URL]` 标签，无本地路径

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

## 4. ⚠️ 图片处理规则

- 默认输出只提供远程图片 URL，不下载图片。
- 默认阅读以正文图片标签顺序为准；debug/raw 中的 media[] 只作为资产清单，不改变正文顺序语义。
- 需要识图时，按当前 Agent 环境选择可用图片读取方式；如工具只支持本地文件，先下载到 /tmp 下的任务目录，识别完成后删除。
- 需要保存到 Obsidian 时，由 to-obsidian 流程下载并本地化附件；下载失败时保留远程引用并记录失败列表。

如果是视频笔记，当前只会保留视频标记或 `videos` 字段，不缓存视频文件。
