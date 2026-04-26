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

- 查看小红书首页推荐：
  `python3 skills/xiaohongshu-assistant/scripts/home.py [count]`

- 在小红书搜索：
  `python3 skills/xiaohongshu-assistant/scripts/search.py "<keyword>" [count]`

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
- 阅读笔记时优先提取：
  - `title`
  - `author`
  - `text`
  - `images`
  - `videos`
  - `url`
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

如果是视频笔记，当前只会保留视频标记或 `videos` 字段，不缓存视频文件。
