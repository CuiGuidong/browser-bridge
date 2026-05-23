# Quality Gates

只运行与本次改动相关的检查；不要为了简单文档改动强行跑真实浏览器长流程。

## Python 代码改动

优先使用临时 pycache，避免本地权限问题：

```bash
env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile bridge/app/server.py bridge/app/cdp_service.py bridge/app/browser/cdp_runtime.py
```

如果本次改动涉及站点 workflow 或服务启动：

```bash
sudo systemctl restart browser-bridge.service
curl --noproxy '*' -sS http://127.0.0.1:17777/health
```

## Extension 改动

```bash
./scripts/dev_reload_extension.sh
```

然后至少验证一个站点语义读取：

```bash
python3 skills/weibo-assistant/scripts/read_post.py 'https://weibo.com/6105713761/Qy80W8wXc'
```

## 文档改动

```bash
git diff --check
```

如果文档涉及合同或 API，检查对应文件：

```bash
sed -n '1,260p' docs/interfaces.md
sed -n '1,260p' temp/media-agent-suite-contract.md
```

## 架构边界检查

Bridge 侧不应新增站点 DOM 选择器：

```bash
grep -R "querySelector\\|getElementsBy\\|xpath\\|selector" -n bridge/app || true
```

Skill 层不应重新接管固定 workflow 的页面生命周期：

```bash
grep -R "\"/open\"\\|\"/wait\"\\|\"/site/read\"\\|\"/site/action\"" -n skills || true
```

这些命令可能有历史结果；出现输出时按本次 diff 判断是否新增违规。

## 跨项目合同检查

涉及 `media-agent-suite` 合同时，检查两边文档：

```bash
sed -n '1,260p' temp/media-agent-suite-contract.md
sed -n '1,260p' /home/cuiguidong/workspace/personal/projects/Python/media-agent-suite/docs/12-browser-bridge-adaptation-needs.md
```
