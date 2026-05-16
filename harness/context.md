# Harness Context

本项目是 `browser-bridge`，一个本地真实浏览器执行基座。

核心链路：

```text
Skill / Script / Agent / External App
  -> Browser Bridge HTTP API
    -> Workflow
      -> Extension + Adapter
        -> Real Browser Page
```

主要目录：

- `bridge/app/`：HTTP API、CDP runtime、workflow 调度、站点注册。
- `extension/`：浏览器扩展、content script、background、站点 adapter。
- `skills/`：面向 Codex/Agent 的站点 skill 脚本。
- `docs/`：公开架构、API、站点能力和实现指南。
- `harness/`：本地 harness engineering 约束、任务板和质量门。
- `temp/`：本地临时计划、跨项目合同和未公开任务材料。

当前已支持站点：

- X：读帖、搜索、首页流、书签、关注/取关、加书签/移除书签。
- 小红书：读笔记、首页、搜索、图文发布前准备、笔记指标、主页指标。
- 微博：首页、热门、热搜、单帖、搜索。
- 知乎：内容页、主页指标、搜索。
- B 站：视频页元信息、主页指标、搜索。
- 抖音：视频页元信息、主页指标、搜索。
- Reddit：帖子页、用户/Subreddit 指标、搜索。

视频站当前只读取元信息和公开互动指标，不解析视频画面、音轨、字幕或口播内容。

外部业务系统：

```text
/home/cuiguidong/.openclaw/workspace/projects/media-agent-suite
```

跨项目合同：

```text
temp/media-agent-suite-contract.md
```

Agent 开发前必须确认：

- 当前任务属于浏览器控制、站点语义、固定 workflow、skill 编排，还是外部业务系统合同。
- 修改 `extension/` 后必须自动同步并重载扩展。
- 修改 `bridge/app/` 后必须重启 bridge。
- 涉及真实浏览器链路时，不能只凭沙箱失败判断代码异常。
