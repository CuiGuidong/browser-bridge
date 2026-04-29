# Browser Bridge 站点能力矩阵

_最后更新：2026-04-28_  
_状态：公开能力说明_

本文档回答两个问题：

- 当前到底支持哪些站点、哪些能力
- 每个站点的输入形态、能力边界和当前限制是什么

更底层的架构约束见：

- [architecture-spec.md](architecture-spec.md)

更偏实现与踩坑的说明见：

- [implementation-guide.md](implementation-guide.md)

## 总览

| 站点 | 读取 | 搜索 | 动作 | 发布 |
|------|------|------|------|------|
| X | 单帖、首页流、书签 | 支持 | 关注/取关、书签增删 | 暂不支持 |
| 小红书 | 单篇笔记、首页推荐流 | 支持 | 暂无账号状态变更动作 | 图文发帖准备 |
| 微博 | 单帖、首页流、热门微博流、热搜榜 | 支持 | 暂无账号状态变更动作 | 暂不支持 |

## X

### 当前能力

- `read_post`
- `read_timeline`
- `list_bookmarks`
- `expand_post`
- `switch_feed`
- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`

### 当前 workflow

- `read_post`
- `search`
- `list_bookmarks`
- `read_home`
- `follow_user`
- `unfollow_user`
- `add_bookmark`
- `remove_bookmark`

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
- 查看书签
- 基于 Agent 判断执行关注或书签动作

## 小红书

### 当前能力

- `read_post`
- `read_home`
- `search`
- `prepare_publish_post`

### 当前 workflow

- `read_post`
- `read_home`
- `search`
- `prepare_publish_post`

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

## 微博

### 当前能力

- `read_home`
- `read_hot_feed`
- `read_hot_search`
- `read_post`
- `search`

### 当前 workflow

- `read_home`
- `read_hot_feed`
- `read_hot_search`
- `read_post`
- `search`

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

## 当前能力边界

- 当前核心路线是“站点语义读取 + 固定 workflow + Agent 编排”
- 不是所有站点都已支持状态变更动作
- 小红书发帖当前是“准备发布”，不是自动点击最终发布
- 真实浏览器、真实登录态、扩展状态和宿主服务环境会直接影响可用性

如果你准备新增站点，不要从这份文档开始扩写实现细节，直接读：

- [new-site-adaptation-guide.md](new-site-adaptation-guide.md)
