# Browser Bridge 架构规范

_最后更新：2026-03-31_  
_状态：正式规范_

## 1. 文档目的

本文档是本项目的**正式架构约束**。目标不是解释某一次临时实现，而是给未来的新会话、新开发者、新 Agent 提供一份可直接遵循的设计基线。

读完本文档后，应该能够直接回答这些问题：

- 这个项目的控制边界是什么
- `CDP`、浏览器扩展、Bridge、skill 各自负责什么
- 新站点能力应该落在哪一层
- 哪些能力应该做成 bridge workflow，哪些应该保留给 skill 编排
- 以后扩展微博、小红书等站点时，应该按什么方式组织代码

本文档是规范，不是 brainstorming。若实现与本文档冲突，应优先把实现收敛到本文档，而不是继续扩散新的局部特判。

## 2. 项目定位

Browser Bridge 是一个本地优先的浏览器桥，允许 Agent / skill 通过结构化 HTTP API 操作**用户真实浏览器**，并复用用户真实登录态、Cookie、用户资料和浏览环境。

本项目不是通用浏览器自动化平台，也不是云端控制面板，而是一个**面向真实浏览器、面向站点语义、面向个人项目维护成本**的轻量桥接系统。

## 3. 目标与非目标

### 3.1 目标

- 本地优先，真实浏览器优先
- 支持真实登录态下的低频页面读取与页面操作
- 把浏览器控制、站点语义、任务编排三者分层清楚
- 支持逐步新增站点，而不是只服务 X
- 保持个人项目可控，不滑向平台化复杂度

### 3.2 非目标

- 大规模批量爬虫
- 反爬虫攻防
- 绕过验证码、2FA、MFA
- 大规模自动化发布、删除、支付等高风险动作
- 复刻 bb-browser 那样的多入口平台架构
- 做一套“扩展和 CDP 双端重复实现同一站点语义”的系统

## 4. 架构总览

```text
Skill / Script / Agent
  -> Browser Bridge HTTP API
    -> Application Layer
      -> Browser Runtime (CDP)
      -> Extension Runtime (RPC + State)
      -> Site Registry
      -> Site Adapter
      -> Site Workflow
```

### 4.1 核心原则

- `CDP` 只负责浏览器级能力
- `Extension + Adapter` 只负责页面内能力和站点语义
- `Bridge` 只做编排，不直接写站点 DOM 规则
- `Workflow` 只负责步骤固定、确定性强的任务
- `Skill` 负责开放式、高语义、高上下文决策的任务

### 4.2 一个必须明确的原则

`CDP` 和 `Extension` 是**协作关系**，不是默认主备关系。

这句话的含义很重要：

- 不能把 `CDP` 定义成“站点语义 fallback”
- 不能要求“扩展做一份 X 逻辑，CDP 再做一份 X 逻辑兜底”
- 不能在架构上默认所有站点能力都要“双实现”

更合理的原则是：

- 浏览器控制能力天然属于 `CDP`
- 站点语义能力天然属于 `Extension + Adapter`
- 如果未来某一项页面能力用 `CDP` 更简单，那就**直接把该能力定义在 `CDP` 侧**
- 但这不叫 fallback，而是这项能力本来就属于 `CDP`

换句话说：

- `CDP` 负责浏览器控制与诊断
- `Extension` 负责站点语义
- 不是“扩展失败了就让 CDP 模拟一遍整个站点语义”

## 5. 分层职责

### 5.1 Browser Runtime（CDP）

职责：

- 打开页面
- 复用 tab
- 激活 tab
- 导航
- 获取 tab 列表
- 获取页面基础信息
- 截图
- 执行基础 JS
- 提供浏览器状态、页面基础状态、通用文本抓取等诊断能力

明确不负责：

- 不判断“X 推文 ready 了没有”
- 不判断“当前按钮是不是已关注”
- 不展开某站点的“显示更多”
- 不负责结构化时间线、结构化书签、结构化关注列表

Browser Runtime 是**浏览器控制层**，不是站点语义层。

### 5.2 Extension Runtime

职责：

- Bridge 与浏览器扩展的双向通信
- 主动调用当前页面 adapter 的能力
- 接收扩展侧页面状态上报
- 维护当前 tab 对应的扩展状态缓存
- 把 Bridge 的语义命令路由到正确的页面实例

当前约束：

- 扩展通信采用“被动上报 + 主动 RPC”双通道
- `content.js` 是页面内常驻执行者
- `background.js` 负责和 Bridge 转发消息
- 主动命令必须带目标页约束，避免跨 tab 串命令
- 当前目标页匹配规则不是抽象的“任意精确匹配”，而是：
  - 规范化后的 `exact_url`
  - 仅 X 额外支持 `x_status_id`

### 5.3 Site Adapter

职责：

- 单站点原子能力
- 判断当前页面是否匹配该站点
- 判断当前页面类型
- 提供站点级 `ready` 判断
- 提供语义级读取
- 提供语义级操作
- 对动作结果做页面内校验

Site Adapter 的主实现位置：

- 应在浏览器扩展 JS 中
- 延续 `content.js + adapters/*.js` 模式

不建议在 Python 中复制一份 DOM 适配逻辑。否则就会回到“扩展/CDP 双端重复实现”的旧问题。

#### 5.3.1 adapter 负责什么

- “这个页面是不是微博主页”
- “这个卡片是不是一条帖子”
- “关注按钮在哪里”
- “书签是否真的消失了”

#### 5.3.2 adapter 不负责什么

- 开新 tab
- 复用 tab
- 全局重试策略
- checkpoint
- 长流程决策
- 开放式规则筛选

### 5.4 Site Workflow

Workflow 的职责是处理**步骤固定、目标明确、流程稳定**的任务。

例如：

- `read_post`
- `search`
- `list_bookmarks`
- `read_home`
- `follow_user`
- `unfollow_user`
- `add_bookmark`
- `remove_bookmark`
- 以后如果有非常固定的“打开某页 -> 读取 -> 验证”流程，也可以放 workflow

当前实现细节：

- 默认允许新开临时标签页
- 浏览器页签总数达到上限时，强制复用同站点标签页
- 当前默认页签上限为 `30`
- workflow 只关闭“本次新开出来的临时标签页”，不关闭复用来的既有标签页
- 如果调用方传入 `targetId`，应把它理解成“指定 workflow 在哪个 tab 容器里执行”
- 这不意味着 workflow 会保留当前页原样执行；workflow 仍会把该 tab 导航到目标 URL

并且当前固定流程默认还负责：

- 打开目标页
- 必要时新开临时标签页
- 读取或执行动作
- 关闭临时标签页

Workflow 不适合做什么：

- “整理书签”
- “按规则批量筛选需要删除的内容”
- “读完一条推文后根据上下文决定要不要关注作者”

这些任务不是流程固定，而是**决策开放**，更适合交给 skill。

### 5.5 Skill

Skill 是**高语义编排层**，适合处理开放式目标。

例如：

- “读这条推文，如果作者值得关注就关注他”
- “整理我的书签，只保留 AI 编程相关内容”
- “帮我看看最近关注的人里谁值得继续保留”

为什么这类任务应该放 skill：

- 筛选规则通常不是写死的
- 决策依赖上下文
- 同一个任务每次的标准可能都不同

因此：

- Bridge workflow 负责固定流程
- skill 负责编排原子能力

### 5.6 已落地参考实现模式

当前 X、小红书和微博已经形成一套统一实现模式，后续扩站应优先照此推进：

当前已落地站点可以概括为：

- X：读取、低风险动作、状态变更动作、固定 workflow、专用 skill 都已落地
- 小红书：只读 workflow、图文发布前准备 workflow 与专用 skill 已落地
- 微博：只读 workflow 与专用 skill 已落地

1. adapter
   - 负责 `collect/getPageType/probeReady/read/act/verify`
   - 负责站点 DOM 语义，不负责页面生命周期

2. workflow
   - 负责固定流程
   - 负责打开目标页、等待最终落地页、关闭临时标签页
   - 负责把原子能力组织成稳定可复用入口

补充：

- 如果业务目标本身要求“停在某个最终确认点前”，workflow 也可以保留当前编辑页不关闭
- 小红书 `prepare_publish_post` 就属于这种情况：workflow 结束时停在最终“发布”按钮前，等待人工确认

3. skill
   - 只做参数解析、输入归一化、调用 workflow、整理输出
   - 不再自己接管页面生命周期

这套模式比“skill 脚本里手写开页/等待/读/关页”更符合当前项目的正式架构。

## 6. 当前推荐的数据模型

### 6.1 ReadResult

```json
{
  "ok": true,
  "source": "extension-semantic",
  "mode": "semantic",
  "site": "x",
  "page": {},
  "signals": {},
  "content": {},
  "debug": {}
}
```

说明：

- `source` 用于说明结果来自哪一层
- `mode` 用于说明是语义结果、原始结果还是别的模式
- `content` 里放结构化结果，不直接把所有结果压平到顶层

### 6.2 ActionResult

```json
{
  "ok": true,
  "source": "extension-semantic",
  "site": "x",
  "action": "follow_user",
  "changed": true,
  "before": {},
  "after": {},
  "verified": true,
  "debug": {}
}
```

状态变更动作最少应该有：

- `changed`
- `verified`
- `before`
- `after`

### 6.3 WorkflowResult

```json
{
  "ok": true,
  "workflow": "read_post",
  "site": "x",
  "targetId": null,
  "summary": {},
  "items": [],
  "checkpoint": {},
  "debug": {}
}
```

注意：本项目不要求所有高层任务都做成 workflow。  
开放式任务优先由 skill 组合原子能力完成。

补充约束：

- 如果 workflow 在执行过程中临时新开了标签页，并在结束前已关闭该页，则 `targetId` 应返回 `null`
- 不应假设 workflow 返回的 `targetId` 一定还能继续被下游调用复用
- `targetId` 当前主要用于底层调试和特殊场景，不建议把它作为固定 workflow 的常规业务参数
- 如果调用方传入 `targetId`，应把它理解成“指定 workflow 在哪个 tab 容器里执行”

## 7. API 设计原则

### 7.1 正式接口与浏览器级工具接口

当前建议把接口分成两类：

- 正式站点能力接口：`/site/read`、`/site/action`、`/workflow/run`
- 浏览器级工具接口：`/query`、`/evaluate`、`/page-info`、`/page-content`、`/screenshot`、`/wait`、`/probe-readiness`

规范方向：

- 固定流程优先走 `/workflow/run`
- 新功能优先走 `/site/*` 和 `/workflow/run`
- 浏览器级工具接口只解决浏览器控制与调试问题
- 浏览器级工具接口不再承载新的站点语义能力

### 7.2 推荐接口形态

- `/site/read`：`site + kind + params`
- `/site/action`：`site + kind + params`
- `/workflow/run`：`site + workflow + params`

这种接口形态的意义是：

- 外部调用面向语义能力
- 不是面向 selector API

当前实现补充：

- `/workflow/run` 是固定流程的一等入口
- `/site/read`、`/site/action` 更多作为 workflow 和调试的原子能力底座

### 7.3 当前已落地 workflow 参数契约

X：

- `read_post`
  - 必填：`url`
  - 可选：`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 可选：`waitForReady`、`intervalSeconds`
- `list_bookmarks`
  - 可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 可选：`mode`(`for_you|following`)、`targetCount`、`continuous`
- `follow_user` / `unfollow_user`
  - 必填：`handle`
- `add_bookmark` / `remove_bookmark`
  - 必填：`url`

小红书：

- `read_post`
  - 必填：`url` 或 `noteId`
  - 可选：`waitForReady`、`intervalSeconds`
- `read_home`
  - 可选：`waitForReady`、`intervalSeconds`
- `search`
  - 必填：`keyword`
  - 可选：`waitForReady`、`intervalSeconds`

## 8. X 作为当前参考站点

### 8.1 当前已落地的 X 原子能力

读取类：

- `read_post`
- `read_timeline`
- `list_bookmarks`

操作类：

- `expand_post`
- `switch_feed`
- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`

当前动作的页面前置条件：

- `follow_user` / `unfollow_user`
  - 只支持用户主页
  - 即 URL 形态应为 `x.com/<handle>`
- `remove_bookmark`
  - 语义上应在书签页执行
- `add_bookmark`
  - 语义上应在目标推文页执行，或能精确定位到目标推文卡片
- `switch_feed`
  - 只在首页 / 时间线页有意义

工作流：

- `read_post`
- `search`
- `list_bookmarks`
- `read_home`
- `follow_user`
- `unfollow_user`
- `add_bookmark`
- `remove_bookmark`

### 8.2 当前已验证的 skill 能力

在 `skills/x-assistant/` 下，已经围绕桥端能力重做了这些脚本入口：

- `read_post.py`
- `search.py`
- `feed.py`
- `bookmarks.py`
- `follow_user.py`
- `unfollow_user.py`
- `add_bookmark.py`
- `remove_bookmark.py`

这说明当前桥端能力已经足以支撑：

- 阅读推文
- 搜索内容
- 查看首页时间线
- 查看书签
- 加书签/移除书签
- 关注/取消关注

### 8.4 小红书作为第二个已落地参考站点

当前已落地的小红书原子能力：

读取类：

- `read_post`
- `read_home`
- `search`

工作流：

- `read_post`
- `read_home`
- `search`

在 `skills/xiaohongshu-assistant/` 下，当前已提供：

- `read_post.py`
- `home.py`
- `search.py`

这说明当前系统已经不再只服务 X，而是已经完成了第二个站点的小规模落地。

当前小红书 `read_post` skill 还负责输入归一化，但这个归一化只处理：

- 从分享文本里提取链接
- 识别 `note_id`
- 识别长链接与短链接

而像 `xhslink.com` 这类短链的最终跳转解析，交由真实浏览器完成，不在 skill 里用独立网络请求提前解析。

### 8.3 关于“整理书签”

“整理书签”不建议做成桥端 workflow。

原因：

- 删除规则通常是开放式的
- 规则经常依赖上下文和用户临时意图
- 这类任务更适合 skill 读取列表后，由 AI 决策要删哪些，再逐条调用原子 action

因此推荐做法是：

- Bridge 提供 `list_bookmarks / add_bookmark / remove_bookmark`
- skill 负责编排“整理书签”

## 9. 新站点扩展指南

这一节是给未来扩展微博、小红书、知乎等站点时用的。

### 9.1 新站点扩展的判断标准

先问自己三个问题：

1. 这个能力是浏览器控制，还是站点语义？
2. 这个能力是原子能力，还是开放式任务？
3. 这项能力更适合放扩展，还是更适合直接放 CDP？

对应规则：

- 浏览器控制 -> Browser Runtime
- 站点语义 -> Extension Adapter
- 固定流程 -> Workflow
- 开放式决策 -> Skill

### 9.2 推荐开发顺序

新增一个站点时，建议顺序固定为：

1. 先定义页面类型
2. 再做 `probeReady`
3. 再做读取类能力
4. 再做低风险动作
5. 再做状态变更动作
6. 最后再决定是否需要 workflow

不要一开始就写 workflow，更不要一开始就写高风险动作。

### 9.3 推荐目录组织

Bridge 侧：

```text
bridge/app/sites/
  weibo/
    models.py
    site.py
    workflows/
```

扩展侧：

```text
extension/adapters/
  weibo-adapter.js
```

个人项目阶段，优先保持“一个站点一个 adapter 文件”。  
只有单文件明显失控时再拆目录。

### 9.4 新站点最少要定义什么

页面识别：

- `match()`
- `getPageType()`

就绪判断：

- `probeReady()`

读取类：

- 至少一个核心读取能力

操作类：

- 先从低风险动作开始

校验类：

- 每个状态变更动作都必须有 `verify()`

### 9.4.1 新站点最小落地 Checklist

如果未来要扩微博、小红书等站点，建议至少按下面清单推进：

1. 扩展侧：
   - 新建 `extension/adapters/<site>-adapter.js`
   - 在扩展加载配置中确保该站点页面会注入该 adapter（当前落点：`extension/manifest.json`）
   - 实现 `match/getPageType/probeReady/read/act/verify`

2. Bridge 侧：
   - 新建 `bridge/app/sites/<site>/models.py`
   - 新建 `bridge/app/sites/<site>/site.py`
   - 在 `bridge/app/server.py` 中注册该站点到 `SiteRegistry`

3. API 侧：
   - 不新增专用散装接口
   - 统一走 `/site/read`、`/site/action`
   - 只有固定流程明确时才新增 workflow

4. Skill 侧：
   - 如果要对用户暴露该站点能力，再新增专用 skill 脚本
   - skill 负责开放式上下文决策，不要把开放式任务硬塞进 bridge workflow
   - skill 脚本应尽量只做参数解析、调用 workflow、结果整理
   - 允许在 skill 层做输入归一化，例如从分享文本里提取链接或识别 `note_id`

5. 验证侧：
   - 至少验证一个读取能力
   - 至少验证一个低风险动作
   - 如果涉及状态变更，必须验证 `before/after/verified`

### 9.4.2 新站点最小验收矩阵

每新增一个站点，最少应完成下面这张验收矩阵：

1. 页面类型验收
   - 至少 2 类核心页面类型能被正确识别
   - 至少 1 类详情页
   - 至少 1 类列表页

2. 只读能力验收
   - 至少 1 个详情页读取能力
   - 至少 1 个列表页读取能力
   - 都必须在宿主侧真实浏览器环境验证

3. 低风险动作验收
   - 至少 1 个不会改变账号状态的动作
   - 动作后必须有 `verified`

4. 状态变更动作验收
   - 如果该站点实现了状态变更动作，必须验证：
     - `before`
     - `changed`
     - `after`
     - `verified`
   - 测试后必须恢复原状态

5. 调试链路验收
   - `/health`
   - `/tabs`
   - `/site/capabilities`
   - `/extension/state`
   至少应能用于区分浏览器、扩展、Bridge 三层问题

### 9.5 微博 / 小红书这类站点的建议

微博与小红书这类站点，当前与后续扩展都推荐先这样拆：

微博：

- 页面类型：帖子详情、搜索、用户主页、收藏/草稿（如果需要）
- 读取：单帖、搜索结果、主页流
- 操作：收藏、取消收藏、关注、取消关注

小红书：

- 页面类型：笔记详情、搜索、用户主页、收藏夹
- 读取：笔记详情、搜索结果、收藏夹
- 操作：收藏、取消收藏、关注、取消关注

注意：

- 不要先做“批量整理收藏夹”这种高层任务
- 先把原子能力做稳
- 先把“页面前置条件”定义清楚，再做状态变更动作

### 9.6 什么时候直接用 CDP

如果某项能力满足以下条件，可以直接定义在 `CDP` 侧：

- 完全是浏览器控制问题
- 不依赖复杂 DOM 语义
- 扩展实现反而更绕

例如：

- 开页
- 切 tab
- 截图
- 页面基础诊断

但如果一项能力的核心难点是：

- 页面 DOM 结构
- 页面语义判断
- 页面内按钮状态
- 页面内卡片关系

那它仍然应该在 adapter 中实现。

## 10. 风险控制

### 10.1 状态变更动作

至少对以下动作做：

- 前置检查
- 执行后校验
- 节流
- 审计日志

当前 X 上已经这么做的动作包括：

- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`

### 10.2 日志与恢复

当前状态变更动作会写入：

- `temp/x-state-actions.jsonl`

日志里应包含：

- 动作时间
- 目标站点
- 动作类型
- 输入参数
- 执行结果
- 恢复提示

这不是 workflow，而是最小审计能力。

## 11. 当前已知残余风险

即使当前方向已经收敛，仍然有几项现实风险需要明确：

- `follow_user / unfollow_user` 的按钮定位仍是 DOM 启发式，不是绝对刚性定位
- 扩展修改后仍然需要人工重载扩展并刷新页面
- 真实浏览器、扩展、Bridge 之间的宿主链路具有明显的权限边界，测试必须优先考虑宿主可见性

## 12. 最终判断

对本项目来说，最佳实践不是继续堆 selector API，也不是让 `CDP` 重复实现站点语义，而是：

- 用 `CDP` 管浏览器
- 用 `Extension + Adapter` 管站点语义
- 用 `Bridge` 管编排
- 用 `Workflow` 管固定流程
- 用 `Skill` 管开放式任务

这是当前最适合：

- X 现有需求
- 后续微博 / 小红书等站点扩展
- 读取与操作并存
- 个人项目可维护性

的最小可行架构。
