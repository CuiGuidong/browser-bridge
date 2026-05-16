# Task Template

## Task ID

BBHXXX

## Goal

写清一个小而具体的目标。

## Context

相关文档和代码：

- `docs/architecture-spec.md`
- `docs/implementation-guide.md`
- `harness/invariants.yaml`
- ...

## Plan

1. ...
2. ...
3. ...

## Files to change

- ...

## Validation

- `env PYTHONPYCACHEPREFIX=/tmp/browser-bridge-pycache python3 -m py_compile ...`
- `./scripts/dev_reload_extension.sh` if extension changed
- `sudo systemctl restart browser-bridge.service` if bridge/app changed
- Browser baseline if real browser path changed

## Invariant check

确认：

- CDP 未承载站点语义。
- DOM 语义仍在 extension adapter。
- 固定流程仍在 workflow。
- skill 没有重新接管页面生命周期。
- 高风险动作仍默认人工确认。
- 外部业务系统合同没有暴露内部实现细节。
