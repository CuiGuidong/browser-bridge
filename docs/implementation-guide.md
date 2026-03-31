# Browser Bridge 实现指南与避坑手册

_最后更新：2026-03-31_  
_状态：正式指南_

本文档不是架构规范的重复版，而是：

- 记录真实实现里的关键坑点
- 规定开发时应该遵循的操作顺序
- 帮助未来新会话快速判断“是代码问题，还是宿主环境问题”

读者对象：

- 需要接手 X、小红书、微博现有实现的人
- 未来负责继续扩展新站点的 Agent
- 需要接手 bridge / extension / skill 三层实现的人

## 1. 开发前必须先建立的心智模型

### 1.1 这不是纯代码项目

这个项目的真实运行链路是：

```text
Agent / skill
  -> Bridge
    -> Extension
      -> 真实浏览器页面
```

所以任何一次调试都可能同时涉及：

- Python 代码
- 扩展代码
- 浏览器标签页状态
- 宿主机系统服务
- 登录态

如果只盯着当前脚本看，很容易误判。

### 1.2 先怀疑宿主边界，再怀疑代码

当你看到下面这些现象时，应优先怀疑宿主边界，而不是立即修改代码：

- `Failed to open post page`
- 明明成功打开了页面，但拿到的是骨架页或上一页内容
- `extension command timed out`
- 本地服务看起来“离线”
- 沙箱里失败，但用户说同一条命令在宿主机成功

这类情况高频原因是：

- 浏览器没开
- 浏览器没开 CDP
- 扩展没重载
- 页面没刷新
- 你在沙箱里看不到宿主浏览器和扩展

## 2. 宿主侧测试原则

### 2.1 什么情况下必须用宿主侧验证

只要测试涉及以下对象，就应优先使用宿主侧验证：

- 本地浏览器
- 浏览器扩展
- `localhost` bridge
- CDP
- 登录态
- 系统服务

### 2.2 一个实际结论

如果用户说“这条命令我本机能跑通”，而你这里跑不通，应优先：

- 用同一条命令做宿主侧验证

不要在沙箱里反复绕次级诊断。

## 3. 扩展改动后的铁律

只要你改了 `extension/` 下任何代码：

1. 必须重载扩展
2. 必须刷新目标页面
3. 没有这两个动作前，不要相信任何测试结果

这是本项目最重要的操作纪律之一。

### 3.1 为什么

因为扩展是注入到页面里的：

- 重载扩展，不等于旧标签页里的页面脚本自动换新
- 旧页面可能仍在运行旧版 `content.js`
- 这会制造大量“明明改对了，测试还失败”的假象

### 3.2 正确顺序

- 改扩展代码
- 请求人类重载扩展
- 请求人类刷新目标页面
- 人类回复“已重载并刷新”
- 再开始测试

## 4. Bridge 重启原则

只要你改了 `bridge/app/` 下会参与服务运行的 Python 代码，就应该重启 bridge。

当前项目推荐的服务方式：

```bash
sudo systemctl restart browser-bridge.service
```

如果不重启，很容易出现：

- 文档和代码都对了
- curl 还在打旧版本逻辑

## 5. 当前实现中的核心链路

### 5.1 读取链路

当前站点语义读取的主链路是：

```text
/site/read
  -> ReadService
  -> ExtensionRuntime.invoke("probe_ready")
  -> ExtensionRuntime.invoke("read")
  -> x-adapter.js
```

注意：

- 当前新架构下，X 语义读取不再默认走 CDP fallback
- 扩展失败时，应优先返回错误与诊断，而不是伪装成“CDP 语义成功”
- 对外暴露固定流程时，优先提供 `/workflow/run`，不要让 skill 脚本重新接管页面生命周期

如果接手者在看固定流程的具体参数：

- X：
  - `read_post` 需要 `url`
  - `search` 需要 `keyword`
  - `list_bookmarks` 不要求业务参数
  - `read_home` 常用 `mode/targetCount/continuous`
  - `follow_user/unfollow_user` 需要 `handle`
  - `add_bookmark/remove_bookmark` 需要 `url`
- 小红书：
  - `read_post` 需要 `url` 或 `noteId`
  - `search` 需要 `keyword`
  - `read_home` 不要求业务参数
- 微博：
  - `read_post` 需要 `url`
  - `search` 需要 `keyword`
  - `read_home` 常用 `targetCount/scrollRounds`
  - `read_hot_feed` 常用 `targetCount/scrollRounds`
  - `read_hot_search` 常用 `targetCount`

### 5.2 操作链路

当前站点语义操作的主链路是：

```text
/site/action
  -> ActionService
  -> ExtensionRuntime.invoke("act")
  -> ExtensionRuntime.invoke("verify")
  -> x-adapter.js
```

状态变更动作当前包括：

- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`

### 5.3 workflow 链路

当前已正式落地的 workflow 分三组：

X：

- `read_post`
- `search`
- `list_bookmarks`
- `read_home`
- `follow_user`
- `unfollow_user`
- `add_bookmark`
- `remove_bookmark`

小红书：

- `read_post`
- `read_home`
- `search`

微博：

- `read_home`
- `read_hot_feed`
- `read_hot_search`
- `read_post`
- `search`

其它高层任务，例如“整理书签”，仍不建议贸然做成 workflow，应优先保留给 skill 编排。

当前实现上，`/workflow/run` 已经是固定流程的一等入口。  
skill 脚本如果面对的是固定流程，应优先直接调用 workflow，而不是自己重复：

- 打开页面
- 等待页面稳定
- 读或执行动作
- 关闭临时标签页

### 5.4 固定流程的标签页策略

当前固定 workflow 默认遵循：

- 默认允许新开临时标签页
- 浏览器标签页达到上限时，强制复用同站点标签页
- workflow 结束后关闭本次新开的临时标签页

调用层需要理解：

- 如果 workflow 返回的 `targetId` 为 `null`，通常表示临时页已在 workflow 内关闭
- 不应假设 workflow 一定会留下一个可继续操作的标签页句柄
- `targetId` 当前主要保留给底层调试和特殊场景，固定 workflow 默认不建议依赖它
- 如果 workflow 接收 `targetId`，应把它理解成“指定执行容器”，而不是“保持当前页内容不变”

实现细节：

- 当前默认标签页上限是 `30`
- 只关闭“本次 workflow 新开出来的临时页”
- 如果 workflow 复用了既有标签页，则不会关闭该页
- 传入 `targetId` 时，workflow 仍会把该 tab 导航到目标 URL

## 6. 扩展 RPC 的关键实现约束

### 6.1 命令必须带目标页约束

扩展主动 RPC 的命令不能做成“任意 tab 抢单”。

必须：

- enqueue 时带 `targetUrl`
- pull 时按当前页面 URL 匹配

否则会出现：

- `site/action` 明明指定了 X 页
- 却被另一个 tab 抢走执行

这是已经踩过的真实坑。

补充说明：

- 当前 Bridge 里的真实匹配规则不是泛化的“所有站点都做复杂匹配”
- 目前只实现了：
  - 规范化后的 `exact_url`
  - 仅 X 额外支持 `x_status_id`
- 所以像小红书短链这种场景，正确做法不是扩展命令去匹配短链，而是先让浏览器跳到最终长链接页，再进入读取

### 6.2 content.js 是当前实际执行者

当前模式下：

- `background.js` 负责桥接转发
- `content.js` 是页面内轮询拉命令并实际执行 adapter 的一侧

因此：

- 页面没刷新
- 旧 content script 还在

就会直接导致：

- `extension command timed out`

## 7. X 适配器开发注意事项

### 7.1 长文与普通推文不是同一种容器

X 的长文（Notes / 长文章）与普通推文在 DOM 结构上不同。

推荐顺序：

1. 先找长文容器
2. 再找普通推文正文容器
3. 最后才做更弱的 fallback

### 7.2 不要轻易信任通用可见性检查

在复杂 SPA 中，过于激进的可见性过滤可能误杀真实内容。

尤其在 X 里：

- 图片
- 长文块
- 懒加载内容

都可能在某些瞬间被 `getComputedStyle` 误判。

### 7.3 ready 判断必须压住“假 ready”

X 的 shell 渲染很快：

- 左侧导航先出来
- 页面文字长度也可能先达到阈值

但核心正文或时间线可能还没真正到位。

所以 X 的 `ready` 不应只看：

- `document.readyState`
- 正文字数

还应看：

- 目标正文容器是否出现
- timeline 是否真的有卡片
- 是否进入 network quiet

## 8. 状态变更动作的开发规则

### 8.1 一定要有前后状态

所有状态变更动作至少要有：

- `before`
- `changed`
- `verified`
- `after`

### 8.2 一定要有节流

Bridge 当前对状态变更动作做了低频节流。  
未来新增类似动作时，应保持这个原则。

### 8.3 一定要写日志

当前状态变更动作会写入：

- `temp/x-state-actions.jsonl`

日志不是装饰，而是为了：

- 知道刚才到底做了什么
- 发生误操作后能恢复
- 让 skill 后续能利用这些记录做补救

### 8.4 失败时宁可报错，不要猜

对于状态变更动作：

- 找不到目标，就报错
- 找不到按钮，就报错
- 不要用“页面上第一个像按钮的元素”顶上

这个原则比“尽量成功率高”更重要。

## 9. 当前 skill 层实现原则

当前 skill 层已落地三组站点脚本：

- `skills/x-assistant/`
- `skills/xiaohongshu-assistant/`
- `skills/weibo-assistant/`

其中 `skills/x-assistant/` 的重构方向已经明确：

- 公共 bridge 访问走 `bridge_client.py`
- X URL / handle 解析走 `x_targets.py`
- timeline/bookmark item 打分走 `x_item_utils.py`
- 固定流程优先走 `workflow_run()`

动作脚本：

- `follow_user.py`
- `unfollow_user.py`
- `add_bookmark.py`
- `remove_bookmark.py`

这些脚本当前应尽量只负责：

- 参数解析
- 调 workflow
- 整理输出 JSON

不要再把固定流程里的：

- 打开页面
- 激活标签
- 等待页面
- 关闭临时标签

重新放回 skill 脚本里。

另外，图片缓存当前已经提到公共模块：

- `bridge/app/media/image_cache.py`
- `bridge/app/media/async_image_downloader.py`

X、小红书和微博当前共用这套媒体后处理入口，不要再各自复制一份下载逻辑。

补充一个已经踩过的真实坑：

- 不同站点的媒体 CDN 对 bridge 侧下载器的要求并不一致
- 不能因为某个站点主站页面能正常打开，就假设该站点图片直连下载也一定稳定
- 微博图片缓存的实际结论是：
  - `urllib` 可能返回 `403`
  - 过重的 `curl` 参数组合也可能失败
  - 更稳的做法是让下载器走宿主侧可用的最小 `curl` 路径
- 如果 bridge 服务为了保护本地流量而清空了代理环境，要额外确认这不会把外网媒体下载能力一起清掉
- 更稳妥的原则是：
  - 本地 `127.0.0.1` / `localhost` 流量依赖 `NO_PROXY`
  - 外网媒体下载是否需要代理，应由宿主服务环境决定

因此以后扩新站点时，图片缓存问题应单独验证：

1. 返回里是否已经生成 `Image Local`
2. 对应本地文件是否真的落盘
3. 下载器在 bridge 服务环境下是否与交互 shell 环境表现一致
4. 如 shell 可下载而 bridge 不可下载，优先检查服务环境变量而不是先改站点 DOM 逻辑

当前接手者如果要新增站点，最好直接把 X、小红书和微博当作“参考模板”理解：

- adapter 里放站点 DOM 语义
- workflow 里放固定流程与标签页生命周期
- skill 里只做输入归一化、调用 workflow、整理输出

只要守住这三层边界，后续扩微博、知乎等站点时就不容易重新滑回“脚本层补丁编排”。

小红书 skill 还有一个边界需要守住：

- 可以在 `read_post.py` 里做输入判型和链接提取
- 不要在 skill 里自己请求短链去做最终 URL 解析
- `xhslink.com` 这类跳转链路应交给真实浏览器打开，再由 workflow 等待最终页落地

### 9.1 搜索 URL 的实现约定

对于像 X、小红书、微博这样已经存在稳定搜索结果页 URL 的站点，当前更推荐：

- 直接构造搜索结果页 URL
- 交给真实浏览器打开
- 让真实浏览器自行完成参数规范化

不建议默认走：

- 先打开首页
- 再模拟往搜索框里输入
- 再模拟点击搜索

这样做的原因是：

- 结果页 URL 更稳定，更容易调试
- 页面生命周期更清晰
- 可以减少对输入框交互、焦点、按钮状态的依赖

当前已验证的一个实现经验是：

- 中文关键词、带空格关键词，在 X / 小红书 / 微博这三类站点上，未编码与已编码的结果页 URL 都可能被浏览器规范化到正确搜索页
- 因此“是否手工编码 keyword”不应先入为主地下结论
- 当前更简单的默认策略是：优先直接把原始关键词拼到结果页 URL，让浏览器自己规范化

补充说明：

- 当前代码里，X 和小红书的搜索 workflow 仍然使用了 `quote()` 做编码
- 这在当前实现里是可工作的
- 但后续扩新站点时，不要因为习惯就机械地先做手工编码，更不要一上来就退化成输入框自动化
- 先验证“结果页 URL + 真实浏览器规范化”是否已经足够

另外，如果要修改当前标签页策略，落点在：

- `bridge/app/cdp_service.py`

## 10. 新站点扩展的开发 SOP

未来做微博、小红书、知乎等站点时，推荐严格按下面顺序推进。

### 步骤 1：先写文档

先在临时文档里写清：

- 要做哪些页面类型
- 要做哪些读取类能力
- 要做哪些操作类能力
- 哪些属于 skill，不属于 workflow

临时文档位置与命名建议：

- 位置：项目根目录下的 `temp/`
- 命名：
  - `<feature>-architecture.md`
  - `<feature>-plan.md`
  - `<feature>-task.md`

例如：

- `temp/weibo-architecture.md`
- `temp/weibo-plan.md`
- `temp/weibo-task.md`

使用原则：

- 复杂改造先写临时文档
- 完成后把结论并入正式文档
- 临时文档只服务当前重构周期，不长期保留

### 步骤 2：先做页面识别和 ready

不要上来就写操作。

先做：

- `match()`
- `getPageType()`
- `probeReady()`

### 步骤 3：先做只读能力

例如：

- `read_post`
- `read_timeline`
- `list_bookmarks`

### 步骤 4：再做低风险动作

例如：

- 展开正文
- 切换 feed

### 步骤 5：最后做状态变更动作

例如：

- 关注/取关
- 收藏/取消收藏

并且必须同时补：

- verify
- 节流
- 审计日志

### 步骤 6：最后再决定是否需要 workflow

判断标准：

- 如果任务步骤固定、规则明确，可以做 workflow
- 如果任务规则开放、依赖上下文，就应该交给 skill

## 11. 什么时候不应该做 Bridge workflow

以下类型的任务，不建议直接做成 Bridge workflow：

- “整理我的书签”
- “根据内容质量帮我清理关注列表”
- “看完这条帖子后，如果作者值得关注就关注”

原因：

- 决策规则开放
- 强依赖上下文
- 更适合由 skill 组合原子能力

这类任务应让：

- Bridge 提供原子能力
- skill 负责编排

## 12. 当前推荐的调试顺序

如果一条链路失败，优先按这个顺序定位：

1. 浏览器是否开着
2. CDP 是否通
3. bridge 是否是新版本并已重启
4. 扩展是否已重载
5. 页面是否已刷新
6. `/extension/state` 是否有最近上报
7. `/site/capabilities` 是否能返回扩展能力
8. `/site/read` 或 `/site/action` 是否命中目标页

不要一开始就改业务代码。

### 12.1 固定诊断清单

以后接手者排障时，建议固定输出这张诊断清单：

1. 宿主浏览器状态
   - 浏览器是否启动
   - CDP 端口是否可访问

2. Bridge 状态
   - `/health` 是否正常
   - 是否是最新代码并已重启

3. 扩展状态
   - 扩展是否已重载
   - 目标页面是否已刷新
   - `/extension/state` 是否有最近上报

4. 目标页状态
   - `/tabs` 是否能看到目标页
   - `targetId` 是否正确
   - `/site/capabilities` 是否命中正确页面

5. 语义能力状态
   - `/site/read` 或 `/site/action` 是否返回扩展结果
   - 如果失败，错误是在 Bridge、扩展、还是目标页匹配阶段

建议后续如果再扩微博、小红书，也沿用这张诊断清单，而不是每次重新发明排障顺序。

## 13. 当前已知残余风险

- `follow_user / unfollow_user` 仍然依赖 DOM 启发式按钮定位，不是绝对刚性定位
- 小红书视频笔记当前只保留视频存在标记，不缓存视频文件
- 小红书媒体提取仍然依赖页面结构启发式，后续页面改版时可能需要调整
- 部分站点的媒体缓存能力可能依赖 bridge 服务环境中的代理可达性；如微博图片缓存异常，应优先检查下载器请求路径和服务环境，而不是直接判断站点适配失效
- 真实浏览器页面状态偶尔会有时序波动，因此 skill 层仍需要少量、明确目的的等待与重试
- 旧接口还在保留，未来继续扩功能时要防止回流到旧接口上继续加站点特判

## 14. 最后原则

未来继续开发时，始终优先这三条：

1. 不把 `CDP` 拉回站点语义层
2. 不让 skill 脚本重新长成一堆补丁
3. 不让状态变更动作靠“猜测目标”完成

只要守住这三条，后面扩微博、小红书时就不会重新滑回旧架构。
