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
- 单帖优先返回：
  - `author`
  - `publishedAt`
  - `text`
  - `images`
  - `videos`
  - `url`
