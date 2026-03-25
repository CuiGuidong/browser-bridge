# Browser Bridge

让 Agent / skill 通过 HTTP API 操作**真实浏览器**的本地桥。

## 项目定位

Browser Bridge 的目标不是做一个平台化浏览器自动化系统，而是提供一套适合个人项目长期维护的本地桥接能力：

- 使用真实 Chrome / Edge
- 复用真实登录态
- 通过结构化 HTTP API 提供读取与操作能力
- 把浏览器控制、站点语义、任务编排明确分层

当前项目已经从“CDP + 扩展混合堆逻辑”逐步收敛为：

- `CDP`：浏览器控制与诊断
- `Extension + Adapter`：站点语义
- `Bridge`：统一编排
- `Skill`：开放式高层任务

## 核心原则

- 账号安全优先于效率
- 高风险动作必须低频并可审计
- `CDP` 和扩展是协作关系，不是默认主备 fallback 关系
- 新站点能力优先沉到 adapter，不要把站点逻辑散落在 bridge/CDP 层

## 当前架构

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

### 角色划分

`CDP`
- 打开页面
- 复用 tab
- 激活 tab
- 获取页面基础信息
- 截图
- 执行基础 JS
- 提供浏览器状态与页面基础状态诊断

`Extension + Adapter`
- 页面 `ready` 判断
- 站点语义读取
- 站点语义动作
- 动作结果校验

`Bridge`
- 路由
- 目标页定位
- source 标记
- timeout / retry
- 统一结果结构

`Skill`
- 阅读后决策
- 基于上下文调用关注/书签等动作
- 书签整理等开放式任务编排

## 当前已落地能力

### 基础 Bridge API

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /version` | 浏览器 / CDP 版本信息 |
| `GET /tabs` | 列出浏览器 tab |
| `POST /open` | 打开或复用页面 |
| `POST /activate` | 激活 tab |
| `GET /wait` | 等待页面稳定 |
| `GET /page-info` | 获取页面信息 |
| `GET /page-content` | 获取基础文本内容 |
| `GET /probe-readiness` | 通用页面就绪探针（浏览器级诊断） |
| `POST /screenshot` | 截图 |
| `GET /query` | 基础 DOM 查询（浏览器级工具） |
| `POST /evaluate` | 执行 JS（浏览器级工具） |

### 新架构 API

| 端点 | 功能 |
|------|------|
| `GET /site/capabilities` | 查询站点能力 |
| `POST /site/read` | 调用站点读取能力 |
| `POST /site/action` | 调用站点动作能力 |
| `POST /workflow/run` | 调用固定流程 workflow |

补充说明：

- 新增站点语义能力时，优先接入 `/site/read` / `/site/action`
- 不要再把新站点逻辑接到浏览器级工具接口上
- `/query` / `/evaluate` 属于浏览器级工具接口，不是站点语义接口

### 扩展集成 API

| 端点 | 功能 |
|------|------|
| `POST /extension/report` | 扩展被动上报页面状态 |
| `GET /extension/state` | 查看最近扩展状态 |
| `GET /extension/pull` | 扩展主动拉取桥端命令 |
| `POST /extension/result` | 扩展回传主动命令结果 |

### Playwright API

复杂页面附加控制仍保留：

- `POST /playwright/connect`
- `POST /playwright/disconnect`
- `GET /playwright/pages`
- `POST /playwright/click`
- `POST /playwright/fill`
- `POST /playwright/evaluate`
- `GET /playwright/wait-selector`

## 当前 X 站点能力

### 读取类

- `read_post`
- `read_timeline`
- `list_bookmarks`

### 操作类

- `expand_post`
- `switch_feed`
- `add_bookmark`
- `remove_bookmark`
- `follow_user`
- `unfollow_user`

### workflow

- `read_post`

### 已重构的 x-assistant skill

`skills/x-assistant/` 目前已提供：

- `read_post.py`
- `search.py`
- `feed.py`
- `bookmarks.py`
- `follow_user.py`
- `unfollow_user.py`
- `add_bookmark.py`
- `remove_bookmark.py`

这意味着当前系统已经能直接支撑：

- 阅读单条推文
- X 搜索
- 查看首页时间线
- 查看书签
- 加书签 / 移除书签
- 关注 / 取消关注

## 快速开始

### 1. 启动带 CDP 的浏览器

**非常重要：Bridge 必须依赖宿主机浏览器开启 CDP。**

```bash
# Edge (macOS)
open -a "Microsoft Edge" --args --remote-debugging-port=9333

# Chrome (macOS)
open -a "Google Chrome" --args --remote-debugging-port=9333

# Chrome (Linux)
google-chrome --remote-debugging-port=9333
```

### 2. 启动 Bridge

```bash
cd bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python -m app.server
```

Bridge 默认监听：

- `http://127.0.0.1:17777`

API 文档：

- `http://127.0.0.1:17777/docs`

### 3. 可选：注册 systemd 服务

```bash
cd bridge/systemd
bash install-system-service.sh
```

常用命令：

```bash
# 查看状态
bash bridge/systemd/browser-bridgectl.sh status

# 重启
bash bridge/systemd/browser-bridgectl.sh restart

# 查看最近日志
bash bridge/systemd/browser-bridgectl.sh logs 120
```

## 扩展加载

```bash
cd extension
# 在 chrome://extensions 或 edge://extensions 加载此目录
```

扩展当前负责：

- 页面探针
- 页面状态上报
- 主动 RPC 执行
- X 站点语义读取和动作

## 开发时最重要的操作纪律

### 改了扩展代码之后

必须：

1. 重载扩展
2. 刷新目标页面

否则测试结果不可信。

### 改了 bridge 代码之后

必须重启 bridge：

```bash
sudo systemctl restart browser-bridge.service
```

### 测试真实浏览器链路时

优先使用宿主侧验证，不要在沙箱里反复猜。

## 新站点扩展建议

以后扩微博、小红书等站点时，建议严格按这个顺序：

1. 先定义页面类型
2. 先做 `match()` / `getPageType()` / `probeReady()`
3. 先做读取类能力
4. 再做低风险动作
5. 再做状态变更动作
6. 最后再判断是否需要 workflow

重要判断：

- 固定流程 -> workflow
- 开放式高层任务 -> skill

所以像“整理书签”这种任务，推荐：

- Bridge 提供原子能力
- skill 负责决策与编排

## 文档入口

如果要继续接手开发，优先读这三份：

- [README.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/README.md)
- [architecture-spec.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/architecture-spec.md)
- [implementation-guide.md](/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/docs/implementation-guide.md)

建议阅读顺序：

1. 先读 README，建立项目全貌
2. 再读 architecture-spec，理解正式分层与扩展规范
3. 最后读 implementation-guide，避免重复踩坑

## 安全边界

以下动作必须保持谨慎，必要时要求人工明确确认：

- 登录 / 登出
- 2FA / MFA
- 验证码
- 改密码 / 改邮箱 / 改手机号
- 支付 / 转账
- 发布内容 / 删除内容
- 第三方授权

## 当前已知残余风险

- `follow_user / unfollow_user` 的按钮定位仍然依赖 DOM 启发式，不是绝对刚性定位
- 真实浏览器页面状态偶尔会有时序波动，因此少量明确目的的等待 / 重试仍然存在
- 旧接口还在保留，后续继续扩功能时不要回流到旧接口上堆站点特判

## License

MIT
