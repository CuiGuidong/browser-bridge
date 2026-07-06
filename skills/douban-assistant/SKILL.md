---
name: douban-assistant
description: >-
  Use this skill whenever the user asks anything about Douban: reading a movie/TV subject,
  searching Douban subjects, or setting a subject interest state to 想看/在看/看过.
  Hard triggers include any douban.com URL, "豆瓣", "想看", "在看", "看过",
  "读这个豆瓣条目", and "把这部剧加入想看".
---

# Douban Assistant

Use this skill for Douban subject workflows.

## Capabilities

- Read a Douban movie/TV subject with `scripts/read_post.py`.
- Search Douban subjects with `scripts/search.py`.
- Set interest state with `scripts/set_interest.py`.

## Safety

- When the user provides an exact Douban subject URL, the agent may set `wish`, `do`, or `collect` and verify the result.
- When the user only provides a title or recommendation text, search first. If the subject is not unique, ask the user to confirm.
- Do not rate, write comments, publish reviews, bypass login, solve captchas, bypass risk controls, or click final confirmation dialogs when the page requires human confirmation.

## Scripts

```bash
python3 skills/douban-assistant/scripts/read_post.py 'https://movie.douban.com/subject/37523009/'
python3 skills/douban-assistant/scripts/search.py '金特务 本色回归'
python3 skills/douban-assistant/scripts/set_interest.py 'https://movie.douban.com/subject/37523009/' wish
```

`read_post.py` defaults to `douban.subject.v1`. Use `--raw` for the full Bridge payload and `--debug` for semantic output plus diagnostics.

When validating local development, set:

```bash
BRIDGE_URL=http://127.0.0.1:17777
```

## Image Processing Rules

- 帖子正文包含 `[Image: URL]` 标签以标明图片位置。本脚本不下载图片，图片本地化由调用方或归档流程自行处理。
- 阅读时以正文图片标签顺序为准；debug/raw 中的 media[] 作为资产清单，不改变正文顺序语义。
- 识图时，按当前 Agent 环境选择可用图片读取方式。如工具只支持本地文件，可先下载到 /tmp 下的任务目录，识别完成后删除。
