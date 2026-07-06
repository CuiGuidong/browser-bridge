---
name: weibo-assistant
description: >-
  Use this skill whenever the user asks anything about Weibo: reading the home feed,
  reading hot feeds or hot search lists, searching Weibo, and reading a single post from
  PC/mobile/share links.
version: 1.0.0
---

# Weibo Assistant

## 1. 路由规则

- 读取首页微博流：
  `python3 skills/weibo-assistant/scripts/read_home.py [count]`

- 读取热门微博流：
  `python3 skills/weibo-assistant/scripts/read_hot_feed.py [count]`

- 读取热搜榜：
  `python3 skills/weibo-assistant/scripts/read_hot_search.py [count]`

- 读取单条微博：
  `python3 skills/weibo-assistant/scripts/read_post.py "<url|share_text>"`
  - 默认输出 `read_post.v1` 语义模型：`contentItem`、`thread`、`comments`、`platform`
  - 开发排障用 `--raw` 查看 Bridge 原始 payload
  - 需要语义结果加诊断摘要时用 `--debug`
  - 可用 `--comment-limit N` 调整返回的已采集一级评论上限，默认 20；当前不承诺自动加载更多评论

- 搜索微博：
  `python3 skills/weibo-assistant/scripts/search.py "<keyword>" [count]`

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

## 4. ⚠️ 图片处理规则

- 帖子正文包含 `[Image: URL]` 标签以标明图片位置。本脚本不下载图片，图片本地化由调用方或归档流程自行处理。
- 阅读时以正文图片标签顺序为准；debug/raw 中的 media[] 作为资产清单，不改变正文顺序语义。
- 识图时，按当前 Agent 环境选择可用图片读取方式。如工具只支持本地文件，可先下载到 /tmp 下的任务目录，识别完成后删除。
