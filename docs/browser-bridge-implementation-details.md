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