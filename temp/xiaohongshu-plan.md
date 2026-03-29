# 小红书一期接手计划

## 目标

在现有 Browser Bridge 架构下，新增小红书网页端只读能力，覆盖：

- 单篇笔记读取 `read_post`
- 首页推荐流读取 `read_home`
- 搜索综合结果读取 `search`

一期不做：

- 点赞、收藏、关注、评论、发帖等状态变更动作
- 登录相关流程
- 抓包、逆向、接口模拟
- skill 封装

## 固定前提

- 只支持真实浏览器网页端
- 默认依赖宿主机已登录状态
- 继续遵守本项目分层：
  - `CDP` 只做浏览器控制
  - `Extension + Adapter` 做站点语义
  - `Bridge` 做统一编排

## 一期页面范围

### 1. 笔记详情页

- 目标：稳定读回正文内容
- URL 形态：待以宿主侧真实页面为准

### 2. 首页推荐流

- 目标地址：`https://www.xiaohongshu.com/explore`
- 一期只做推荐流，不区分关注流

### 3. 搜索综合结果页

- 输入：关键词
- 一期只做综合结果，不拆分笔记/用户/商品等 tab

## 实现策略

### 阶段 1：骨架接入

- Bridge 新增 `xiaohongshu` 站点注册
- 扩展新增 `xh-adapter.js`
- manifest 增加小红书页面注入

### 阶段 2：页面识别与 ready

- `match()`
- `getPageType()`
- `probeReady()`

重点先解决：

- SPA 页面壳先出来、内容未就绪的假 ready
- 首页流和搜索页卡片是否真的已出现
- 详情页正文容器是否真的出现

### 阶段 3：只读能力

- `read_post`
- `read_home`
- `search`

一期先以“能稳定取回内容”为先，字段先保持最小够用。

## 建议最小返回结构

### read_post

- `page`
- `signals`
- `content.title`
- `content.text`
- `content.author`
- `content.images`

### read_home / search

- `page`
- `signals`
- `content.items`

每个 item 初版最少包含：

- `title`
- `author`
- `excerpt`
- `cover`
- `url`

## 验收标准

### 宿主侧真实环境验收

至少验证：

- `/site/capabilities`
- `read_post`
- `read_home`
- `search`

### 页面覆盖

- 至少 1 个笔记详情页
- 首页推荐流
- 至少 1 个搜索关键词结果页

## 操作纪律

- 改扩展代码后，必须人工重载扩展并刷新目标页面
- 改 Bridge 运行代码后，必须重启 Bridge
- 需要这些操作时，开发中途暂停并明确告知用户
