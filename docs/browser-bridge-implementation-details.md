# Browser Bridge 关键实现细节与避坑指南

_本文档记录了开发过程中发现的关键实现细节、技术坑点（Gotchas）以及架构决策。它作为未来 Agent 和开发者的参考指南，以避免重复踩相同的坑。_

## 1. 抓取 X (Twitter) 上的长文章 (Long Articles / Notes)

**问题现象：**
最初，X 上的长文章（例如超过 4000 字符的 "Notes" 或长推文）在抓取时总是被截断。

**根本原因与解决方案：**

1.  **硬编码的字符长度限制（“隐形杀手”）：**
    *   **坑点：** 浏览器扩展的 `content.js` 在生成快照 payload 时，写死了 `.slice(0, 4000)`。即使 Bridge 后端请求了更长的数据，扩展端也会先一步把数据切断。
    *   **坑点：** FastAPI 后端 `server.py` 中，`ReadPageRequest` Pydantic 模型的默认值是 `maxChars: int = 4000`。如果客户端（curl/agent）没有显式覆盖这个值，后端拿到数据后会再次进行切片截断。
    *   **解决方案：** 移除了 `content.js` 中所有的 `.slice()` 调用（将完整字符串发给后端），并将后端默认的 `maxChars` 增加到 `40000`（或更高），以轻松容纳长文。

2.  **模块化 DOM 渲染与虚拟列表（Virtual Lists）：**
    *   **坑点：** X 使用模块化的平级 `div` 块来渲染长文章。如果只是简单地调用 `document.querySelector('article').innerText` 或查询特定的 CSS 类，经常会漏掉后续的段落。因为这些段落可能并不是目标容器的直接子文本节点，或者它们被深层嵌套在极其复杂的 React 组件结构中。
    *   **解决方案：** 放弃了针对特定 `div`/`span` 的定向查询，改用 **`TreeWalker` 降维打击策略**。通过使用 `document.createTreeWalker(container, NodeFilter.SHOW_TEXT)`，适配器可以直接按物理顺序遍历文章容器内的每一个**纯文本节点**，彻底绕过了所有复杂的嵌套结构。

3.  **懒加载与“显示更多”按钮：**
    *   **坑点：** 部分长篇内容被隐藏在“显示更多 (Show more)”按钮之后，或者需要页面滚动才能触发 React 的虚拟 DOM 去挂载后续节点。
    *   **解决方案：** 在 `cdp_service.py` 的读取流程（`read_page`）中加入了前置处理逻辑：专门寻找“显示更多”按钮（`div[role="button"]`），将其滚动到视口内，模拟点击，并强制**等待 3 秒钟**，让异步内容完全挂载到 DOM 树之后，再执行快照抓取。

## 2. 通过 CDP 读取复杂网页内容 (Shadow DOMs & 框架)

**问题现象：**
现代 Web 应用大量使用 Web Components (Shadow DOM，影子 DOM)，这会导致标准的原生调用 `document.body.innerText` 无法读取到被隐藏的文本。

**解决方案：**
在 `cdp_service.py` 的 `get_page_content` 兜底方法（Path B）中，我们注入并执行了一个递归的 JS 函数。该函数会显式地检查元素是否存在 `.shadowRoot` 属性，如果存在则穿透进去继续遍历。这确保了即使在没有扩展适配器（Path A）帮忙的情况下，纯 CDP 的原始抓取也能尽可能做到最全面、无死角。

## 3. VM -> Bridge -> Host Edge 链路常见误判（高频坑）

这部分是本项目后续接手最容易反复绕圈的地方。

### 坑 1：全局代理变量导致“本地服务假离线”

**现象：**
- `curl http://127.0.0.1:17777/health` 报错
- 明明 bridge 已启动，却提示代理/DNS相关错误

**原因：**
- VM 环境里存在 `http_proxy/https_proxy/all_proxy`
- 请求被错误转发到代理（例如 `host.orb.internal:7897`）

**做法：**
- 对本地链路请求统一禁用代理：
  - `curl --noproxy '*' ...`
  - Python `urllib` 使用 `ProxyHandler({})`

---

### 坑 2：CDP 对 Host 头严格校验

**现象：**
- 访问 `http://host.orb.internal:9333/json/version` 失败

**原因：**
- Edge CDP 在该路径下要求 Host 头匹配本地语义

**做法：**
- 显式发送：
  - `Host: 127.0.0.1:9333`
- 示例：
  - `curl -H 'Host: 127.0.0.1:9333' http://host.orb.internal:9333/json/version`

---

### 坑 3：`read-page` 首次读取与扩展上报存在时序竞争

**现象：**
- 第一次 `read-page` 可能返回 `preferredContentSource=cdp` 且内容为空
- 同一 tab 稍后再读又恢复 `preferredContentSource=extension`

**原因：**
- 新开页后，Bridge 读取发生在 extension report 到达之前
- Bridge 里 `_get_extension_hint` 依赖最近上报并做 URL 精确匹配

**做法：**
- `open` 后先 `activate`
- 给扩展 1-3 秒上报窗口，再 `read-page`
- 验证 `GET /extension/state` 的 `lastReport.page.url` 是否与目标页一致

---

### 坑 4：调试环境限制会伪装成“连通问题”

**说明：**
- 某些 agent 执行沙箱会限制 socket/端口探测
- 这会让“本机起服务/端口探测命令”在工具侧失败，但不代表业务链路本身不可用

**做法：**
- 优先以 bridge API 实测为准（`/health`, `/tabs`, `/read-page`）
- 不要仅凭单次端口命令就判定服务不可达

## 4. 推荐最小验收顺序（先排除连通性假故障）

1. `curl --noproxy '*' http://127.0.0.1:17777/health`
2. `curl --noproxy '*' -H 'Host: 127.0.0.1:9333' http://host.orb.internal:9333/json/version`
3. `GET /tabs` 确认能看到真实 Edge tabs
4. 用固定推文 URL 做单帖读取验收
5. 若失败，先看 `GET /extension/state`，再判断是否功能层问题

## 5. X Home Feed 封装策略（当前实现）

### 目标
- 尽量在单个 X tab 内完成任务，减少标签页和内存增长
- 在“为你推荐/正在关注”两种流之间可稳定切换并识别
- 支持读取更多推文，但严格限制频率，优先账号安全

### 已落地机制
1. **Tab 复用优先**
   - `POST /open` 支持 `reuseExistingTab` 与 `reuseDomain`
   - 先复用同域 tab 并导航，找不到才新开

2. **流模式识别（中英文兼容）**
   - 扩展在 `signals` 中上报：
     - `feedMode` (`for_you` / `following`)
     - `activeFeedTabText`
     - `feedTabTexts`
   - 识别规则兼容 `For you/Following` 与 `为你推荐/正在关注`

3. **读取与切换对齐循环**
   - 不再“点击一次就读”
   - 读取后校验 `feedMode`，不匹配则再次切换
   - 匹配后才持续滚动补量

4. **风控节流参数（保守默认）**
   - 读取间隔约 `1.6s`
   - 滚动间隔约 `2.8s`
   - 最大滚动轮次默认 `12`，连续模式 `30`
   - 用户请求条数有上限（当前 clamp 到 `200`）

### 默认行为（feed.py）
- 默认读取双流：`for_you` + `following`，各 20 条
- 支持自定义条数和连续读取（`--continuous`），但受上述节流与轮次限制
