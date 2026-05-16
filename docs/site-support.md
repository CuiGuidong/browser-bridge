# Browser Bridge 站点能力矩阵

_最后更新：2026-05-16_
_状态：公开能力说明_

本文档回答两个问题：

- 当前到底支持哪些站点、哪些能力
- 每个站点的输入形态、能力边界和当前限制是什么

更底层的架构约束见：

- [architecture-spec.md](architecture-spec.md)
- [video-asset-pipeline-design.md](video-asset-pipeline-design.md)

更偏实现与踩坑的说明见：

- [implementation-guide.md](implementation-guide.md)

## 总览

| 站点 | 读取 | 搜索 | 动作 | 发布 |
|------|------|------|------|------|
| X | 单帖、首页流、趋势流、书签、主页指标、登录状态 | 支持 | 关注/取关、书签增删 | 暂不支持 |
| 小红书 | 单篇笔记、首页推荐流、笔记指标、主页指标、登录状态 | 支持 | 暂无账号状态变更动作 | 图文发帖准备 |
| 微博 | 单帖、首页流、热门微博流、热搜榜、主页指标、登录状态 | 支持 | 暂无账号状态变更动作 | 暂不支持 |
| 知乎 | 内容页、热榜、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| B 站 | 视频页元信息、热门视频、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| 抖音 | 视频页元信息、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| Reddit | 帖子页、热门流、用户/Subreddit 指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| YouTube | 视频页元信息、频道/主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| 微信公众号 | 文章页元信息、账号/来源页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| 豆瓣 | 条目/笔记/评论页元信息、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| HackerNews | 条目/讨论页、用户指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| Instagram | 帖子/Reel 元信息、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| 雪球 | 帖子/讨论页元信息、主页指标、登录状态 | 支持 | 暂不支持 | 暂不支持 |
| 东方财富 | 页面/行情信息页元信息、搜索结果、登录状态 | 支持 | 暂不支持 | 暂不支持 |

## X

### 当前能力

- `read_post`
- `read_timeline`
- `list_bookmarks`
- `read_profile_metrics`
- `expand_post`
- `switch_feed`
- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`
- `account_status`

### 当前 workflow

- `read_post`
- `search`
- `list_bookmarks`
- `read_home`
- `read_trending`
- `read_profile_metrics`
- `follow_user`
- `unfollow_user`
- `add_bookmark`
- `remove_bookmark`
- `account_status`

### 当前 skill

- `skills/x-assistant/read_post.py`
- `skills/x-assistant/search.py`
- `skills/x-assistant/feed.py`
- `skills/x-assistant/bookmarks.py`
- `skills/x-assistant/follow_user.py`
- `skills/x-assistant/unfollow_user.py`
- `skills/x-assistant/add_bookmark.py`
- `skills/x-assistant/remove_bookmark.py`

### 适合的使用场景

- 阅读单条推文或 thread
- 搜索某个关键词
- 获取首页时间线
- 获取趋势流和主页公开指标
- 查看书签
- 基于 Agent 判断执行关注或书签动作

## 小红书

### 当前能力

- `read_post`
- `read_home`
- `search`
- `prepare_publish_post`
- `read_post_metrics`
- `read_profile_metrics`
- `account_status`

### 当前 workflow

- `read_post`
- `read_home`
- `search`
- `prepare_publish_post`
- `read_post_metrics`
- `read_profile_metrics`
- `account_status`

### 当前 skill

- `skills/xiaohongshu-assistant/read_post.py`
- `skills/xiaohongshu-assistant/home.py`
- `skills/xiaohongshu-assistant/search.py`
- `skills/xiaohongshu-assistant/prepare_publish.py`

### `read_post` 输入兼容

- 纯 `note_id`
- PC 长链接
- `xhslink.com` 短链
- 带分享文案的整段文本

### 图文发帖准备的当前边界

- 必填：`title`、`content`、至少一个宿主机图片路径
- 当前只做到图文笔记编辑态准备，不点击最终“发布”
- workflow 会保留编辑页，并返回 `checkpoint.awaitingManualPublish = true`

### 适合的使用场景

- 阅读单篇笔记
- 获取首页推荐流
- 搜索小红书内容
- 由 Agent 先准备好图文发帖内容，再由人工确认发布
- 采集已发布笔记和主页公开指标

## 微博

### 当前能力

- `read_home`
- `read_hot_feed`
- `read_hot_search`
- `read_post`
- `search`
- `read_profile_metrics`
- `account_status`

### 当前 workflow

- `read_home`
- `read_hot_feed`
- `read_hot_search`
- `read_post`
- `search`
- `read_profile_metrics`
- `account_status`

### 当前 skill

- `skills/weibo-assistant/read_home.py`
- `skills/weibo-assistant/read_hot_feed.py`
- `skills/weibo-assistant/read_hot_search.py`
- `skills/weibo-assistant/read_post.py`
- `skills/weibo-assistant/search.py`

### `read_post` 输入兼容

- PC 长链接
- `m.weibo.cn/status/...` 移动链接
- `mapp.api.weibo.cn/...html` 轻享版分享链接
- 带分享文案的整段文本

### 适合的使用场景

- 获取首页微博流
- 获取热门微博流
- 获取热搜榜
- 阅读单条微博
- 搜索微博
- 获取微博主页公开指标

## 知乎 / B 站 / 抖音 / Reddit / YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富

### 当前能力

- `read_post`
- `read_profile_metrics`
- `search`
- `account_status`

### 当前 workflow

- `read_post`
- `read_profile_metrics`
- `search`
- `account_status`

### 第一版基础设施边界

- 知乎：读取问题/回答/文章页的标题、作者、摘要和公开互动指标；读取主页公开指标；搜索结果做语义链接列表。
- B 站：把视频页作为 `post` 读取标题、UP 主、简介、封面和播放/点赞/评论/收藏/投币/弹幕等公开指标。
- 抖音：把视频页作为 `post` 读取标题/描述、作者、封面和点赞/评论/收藏/分享等公开指标。
- Reddit：读取帖子标题、正文摘要、作者、分数/评论数；读取用户或 Subreddit 页公开指标；搜索结果做语义链接列表。
- YouTube：把视频/Shorts 页作为 `post` 读取标题、频道、描述、封面和页面可见互动指标；频道页作为 profile metrics；搜索结果做语义链接列表。
- 微信公众号：读取 `mp.weixin.qq.com` 文章页标题、作者/公众号、摘要和封面；通过搜狗微信结果页提供搜索入口；不做群发、草稿创建或发布动作。
- 豆瓣：读取条目、笔记、影评/书评等页面元信息和页面可见指标；搜索结果做语义链接列表。
- HackerNews：读取 item 讨论页和用户页的公开信息；搜索通过 Algolia 结果页读取链接列表。
- Instagram：读取帖子/Reel 和主页可见元信息；不关注、不点赞、不评论、不发帖。
- 雪球：读取帖子/讨论页、用户页和搜索页可见信息；不做交易、关注、发帖或自选股修改。
- 东方财富：读取页面和行情信息页可见元信息；不做交易、登录态资金相关读取或账号状态修改。

这些 OpenCLI-inspired 站点当前采用轻量通用 adapter 配置，目标是先建立真实浏览器 + extension adapter + workflow 的安全只读入口。后续如果某个站点需要更高质量字段，应按单站 adapter 深化，而不是把 DOM 选择器放进 `bridge/app/`。

### 视频内容边界

B 站、抖音和 YouTube 当前不解析视频画面、音轨、字幕或口播内容。返回中会标记：

```json
{
  "mediaType": "video",
  "videoContentParsed": false
}
```

后续如要支持视频文案/对话脚本提取，应单独接入下载或缓存、`ffmpeg` 音频提取、ASR 转写和 LLM 摘要链路，不放进当前轻量 adapter。

### 登录状态边界

所有已注册站点都提供 `account_status` workflow 和 `/login/status` 运维入口。返回只包含是否登录、是否需要人工登录、可见账号昵称/主页等业务语义字段，不返回 cookie、token、密码或浏览器内部状态。

## 当前能力边界

- 当前核心路线是“站点语义读取 + 固定 workflow + Agent 编排”
- 不是所有站点都已支持状态变更动作
- 小红书发帖当前是“准备发布”，不是自动点击最终发布
- 新增知乎 / B 站 / 抖音 / Reddit / YouTube / 微信公众号 / 豆瓣 / HackerNews / Instagram / 雪球 / 东方财富 属于基础设施第一版，优先保证能力发现和轻量元信息采集
- 真实浏览器、真实登录态、扩展状态和宿主服务环境会直接影响可用性

如果你准备新增站点，不要从这份文档开始扩写实现细节，直接读：

- [new-site-adaptation-guide.md](new-site-adaptation-guide.md)
