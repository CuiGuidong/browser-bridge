# X (Twitter) Smart Assistant

这是一个专为 OpenClaw Agent 设计的 X (Twitter) 高级助理 Skill。它通过底层的 `browser-bridge` 与用户真实的浏览器交互，实现极高安全性的“拟人化”信息获取。

## 你的角色 (The "Smart" Orchestrator)
你作为 Agent，是这个过程中的“大脑”。底层脚本只负责提取 DOM 中的推文（“手”和“眼睛”）。你必须负责：
1. **多语言查询拆解**：当用户用中文让你搜索一个概念（如 "AI Agents 最新进展"）时，你**必须**在调用搜索脚本前，将关键词翻译/拆解为英文和中文两个甚至多个查询词（例如：`"AI Agents"` 和 `"AI智能体"`）。
2. **多轮搜索调度**：多次调用底层 `search.py` 脚本，分别执行这些查询。
3. **结果去重与提炼**：将不同查询词返回的结果合并，根据 URL 或推文内容去重，并按照用户的原始意图提取重点，给出最终总结。
4. **防滥用限制**：不要在一次任务中发起超过 3 次的搜索请求，以保护用户的真实 X 账号不被风控。

## 支持能力

### 1. 搜索推文 (Smart Search)
基于关键词在 X 上执行搜索并抓取前 20-30 条结果。
```bash
python3 scripts/search.py "YOUR_KEYWORD"
```
**注意：** 如果用户的需求较宽泛，你应该先思考合适的英文/中文关键词，然后分多次调用此脚本，最后自己合并结果。

### 2. 阅读时间线 (Read Home Feed)
读取用户首页的推文时间线（推荐流/关注流/双流）。脚本会自动进行低频“轻量滚动”以获取更多推文，并内置风控节流。
```bash
# 默认：同时读取「为你推荐」+「正在关注」，各 20 条
python3 scripts/feed.py

# 只读取「正在关注」30 条
python3 scripts/feed.py following 30

# 只读取「为你推荐」50 条
python3 scripts/feed.py for_you 50

# 连续向下读取（低频滚动，带安全上限）
python3 scripts/feed.py both 50 --continuous
```
这对于用户让你“看看今天 X 上有什么新鲜事”非常有用。

脚本输出会包含：
- `feed.mode`：当前实际流模式（`for_you` / `following`）
- `feed.activeTabText` / `feed.availableTabs`：中英文标签识别结果
- `result.count`：本次返回条数
- `items`：结构化推文列表（保留作者、时间、URL、正文）

### 3. 阅读单篇推文 (Read Single Post)
如果搜索结果或时间线中有一篇非常长的文章，或者用户直接提供了一个推文链接，你可以使用脚本：
```bash
python3 scripts/read_post.py "https://x.com/..."
```

## 返回数据结构
`feed.py` 成功后返回稳定结构：
`{"ok": true, "request": {...}, "feed": {...}, "result": {...}, "items": [...], "data": [...]}`  
其中 `data` 是向后兼容别名，等同 `items`。

`search.py` 与 `read_post.py` 继续返回 JSON 结构化结果。
你需要解析这个 JSON，并用人类可读的方式呈现给用户。
