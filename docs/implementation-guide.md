# Browser Bridge 关键实现细节与避坑指南

_本文档记录了开发过程中发现的关键实现细节、技术坑点（Gotchas）以及架构决策。它作为未来 Agent 和开发者的参考指南，以避免重复踩相同的坑。_

## 1. 抓取 X (Twitter) 上的长文章 (Long Articles / Notes)

**问题现象：**
最初，X 上的长文章（例如超过 4000 字符的 "Notes" 或长推文）在抓取时总是被截断，且**纯文字长文和图文混排的长文在容器结构上完全不同**。

**根本原因与解决方案：**

1.  **硬编码的字符长度限制（“隐形杀手”）：**
    *   **坑点：** 浏览器扩展的 `content.js` 在生成快照 payload 时，曾写死了 `.slice(0, 4000)`。如果客户端（curl/agent）没有显式覆盖后端默认值，后端也会进行切片截断。
    *   **解决方案：** 移除了 `content.js` 中所有的 `.slice()` 调用，并将后端默认的 `maxChars` 增加到极大值，客户端统一传入 `100000`。

2.  **模块化 DOM 渲染与极其隐蔽的长文容器：**
    *   **坑点：** 普通推文的内容放在 `[data-testid="tweetText"]` 里。但对于 X 的长文章 (Article)，标题和头图以及正文是被分别放在不同的平行块（例如 `<div class="DraftEditor-root">` 或 `<section data-block="true">`）中的。如果只用 `tweetText` 去定位，不仅抓不到配图，甚至可能抓到外层的左侧导航栏导致内容彻底错乱。
    *   **解决方案：** 提取入口必须具有极强的针对性，优先查找 `[data-testid="twitter-article-title"]` 的父级 `article` 容器，其次找 `[data-testid="twitterArticleRichTextView"]`，最后再 fallback 到普通的 `tweetText`。

3.  **提取图文交叉顺序时的可见性陷阱：**
    *   **坑点：** 当尝试在遍历 DOM 树时同时提取 `<img>` 标签的 src 时，如果使用了标准的可见性检查 `window.getComputedStyle(node).display === 'none'`，会**导致大量刚渲染出来的配图被误杀**。原因是 X 的复杂页面可能在某些瞬间、或者由于某种懒加载的 CSS hack，使得扩展沙箱获取到的 display 状态并不准确。
    *   **解决方案：** 彻底移除了 `walk(node)` 递归函数中对 `getComputedStyle` 的检查，只要是在确定的 `article` 容器内出现的 `<img>` 或 `<video>`，只要排除了特定的头像和图标 class，就无条件抓取并插入 `[Image: URL]` 标记。

## 2. 单页应用 (SPA) 下的时序竞争与缓存残留

**问题现象：**
Agent 执行了 `/open` 之后立刻调用 `/read-page`，明明浏览器扩展已经写好了高级的富文本提取逻辑，但最后返回的却总是没有图片的“CDP兜底纯文本”，甚至返回了上一页的数据。

**根本原因与解决方案：**

1.  **时序竞争：** 
    *   **坑点：** Python 脚本发送请求太快，而 X 页面需要加载网络资源、执行 JS，扩展层 (`content.js`) 的 MutationObserver 还需要时间去拼装 DOM 树并上报给 Bridge 后端。如果脚本不等扩展，Bridge 只能拿底层 CDP 去硬抠字，导致结构化信息丢失。
    *   **解决方案：** 在 `read_post.py` 和 `search.py` 中，**强制增加 `time.sleep(1.5)` 的初始等待**，并利用 `for _ in range(3):` 循环调用 `/read-page`。只有确认后端返回的 `preferredContentSource == "extension"` 才结束循环，否则持续等待。

2.  **扩展缓存未更新 (SPA 刷新问题)：**
    *   **坑点：** 修改了扩展代码并在浏览器管理页点击“重新加载”后，由于 X 是单页应用，已经打开的标签页**依然在运行旧版的扩展内存代码**，导致调试始终不生效。
    *   **解决方案：** 任何扩展更新后，必须**按 F5 彻底刷新当前的 X 页面**，让新的 `content.js` 被重新注入。

## 3. 通过 CDP 读取复杂网页内容 (Shadow DOMs & 框架)

**问题现象：**
现代 Web 应用大量使用 Web Components (Shadow DOM，影子 DOM)，这会导致标准的原生调用 `document.body.innerText` 无法读取到被隐藏的文本。

**解决方案：**
在 `cdp_service.py` 的 `get_page_content` 兜底方法（Path B）中，我们注入并执行了一个递归的 JS 函数。该函数会显式地检查元素是否存在 `.shadowRoot` 属性，如果存在则穿透进去继续遍历。这确保了即使在没有扩展适配器（Path A）帮忙的情况下，纯 CDP 的原始抓取也能尽可能做到最全面、无死角。

## 4. ⚠️ 严禁盲目测试 (致未来负责维护扩展的 AI Agent)

**如果你修改了 `extension/` 目录下的任何 JS/HTML 文件，请遵守以下铁律：**

执行代码写入后，**严禁立即调用任何 Python 脚本或 curl 命令进行验证测试！**
你必须先暂停你的执行循环，向人类用户输出明确的提示：
1. 请求用户在浏览器中打开 `chrome://extensions` 并点击 Browser Bridge Extension 的 **“重新加载” (Reload)**。
2. 请求用户**强制刷新 (F5) 正在被测试的目标网页**。

只有在人类用户回复“已重载并刷新”后，你才可以发起 API 请求测试。否则，你将读到旧版的缓存代码，陷入无止境的“修改->测试失败->修改正确代码为错误代码”的死亡螺旋。

## 5. VM -> Bridge -> Host Edge 链路常见误判（高频坑）

这部分是本项目后续接手最容易反复绕圈的地方。

### 坑 1：服务连通性报错 / Connection Refused (HTTP 500)
**现象：**
- Agent 调用 `read_post.py` 等脚本时，抛出 `Connection refused` 500 错误。
**原因：**
- 宿主机的浏览器**根本没有启动**，或者启动时**忘记加 CDP 参数**。
**做法：**
- 立即在宿主机终端执行：`open -a "Microsoft Edge" --args --remote-debugging-port=9333`

### 坑 2：全局代理变量导致“本地服务假离线”
**现象：**
- `curl http://127.0.0.1:17777/health` 报错
- 明明 bridge 已启动，却提示代理/DNS相关错误
**原因：**
- VM 环境里存在 `http_proxy/https_proxy/all_proxy`，请求被错误转发到代理。
**做法：**
- 对本地链路请求统一禁用代理：`curl --noproxy '*' ...`；Python `urllib` 使用 `ProxyHandler({})`。

### 坑 3：CDP 对 Host 头严格校验
**现象：**
- 访问 `http://host.orb.internal:9333/json/version` 失败
**原因：**
- Edge CDP 在该路径下要求 Host 头匹配本地语义。
**做法：**
- 在代码中显式发送 `Host: 127.0.0.1:9333`。

## 6. AI Agent 开发范式 (SOP: 临时文档驱动重构)

为了保障系统架构的稳定演进，**未来任何复杂功能的开发与架构重构，必须遵循以下“临时文档驱动”的推进模式**：

1. **落地方案 (Plan)**：在 `docs/temp/` 下创建 `<feature>-plan.md`，写明重构背景、设计机制、预期成果。
2. **制定清单 (Task)**：在 `docs/temp/` 下创建 `<feature>-task.md`，将 Plan 拆解为可执行的 Checklist（精确到文件修改与测试步骤）。
3. **严格执行**：AI Agent 必须严格按照 Task 逐条执行，尤其在涉及需要人类干预的步骤（如重载扩展）时，必须停下等待。
4. **收敛闭环**：功能测试通过后，将 Plan 中的架构设计提炼并合并到主文档 (`docs/architecture-spec.md` 或 `README.md`) 中。然后**彻底删除** `docs/temp/` 下的相关临时文档，并提交 Git。
5. **严禁越级**：未得到人类确认方案前，严禁直接对生产代码进行大面积重构。

## 7. 异步图片预载系统 (Async Image Preloader)

**实现逻辑：**
为了解决大模型查看多模态图片需要消耗大量时间同步下载或挤占 Token (Base64) 的问题，系统采用了**“文件系统级别的异步 Promise”**模式：

1. **确定性占位 (Deterministic Paths)**：Python 主脚本在返回数据前，基于计算决定论，对在线图片 URL 进行 MD5 哈希推算出确定性的本地绝对路径。它瞬间将原文的 `[Image: URL]` 替换为 `[Image Local: <path> | Remote: <url>]` 并立即返回 JSON 给大模型，耗时为 0。
2. **即用即毁的幽灵进程 (Fire-and-Forget Ephemeral Worker)**：
   - 主脚本通过 `subprocess.Popen(..., start_new_session=True)` 无阻塞地“撕裂”出一个独立的后台子进程 `async_image_downloader.py`。
   - **零空闲开销**：该下载器不是常驻服务。它被唤醒后只做三件事：(1) 清理 >24 小时的旧缓存避免硬盘撑爆；(2) 开启并发线程池极速下载本次需要的图片；(3) **任务完成后立刻退出、销毁自身**。
   - **绝对免维护**：无需 `systemctl` 管理，没有内存泄漏风险，多次调用互不干扰。
3. **时间差互补**：当大模型花几秒钟阅读完 JSON 文本并决定调用 `read_file` 工具查看某张本地图片时，后台幽灵进程必定已经下载完毕并自行退出了。这实现了对 Agent 完全透明、零等待、零维护负担的多模态极速闭环。
