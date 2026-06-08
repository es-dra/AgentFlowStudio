# AgentFlow Router Contract

本文记录当前 router dry-run decision validation 的最小契约边界。

## 当前对象

- `agentflow_router_decision`
- `agentflow_router_dry_run_validation`

## 验证边界

`agentflow_router_dry_run_validation` 只验证 router decision 是否可审计：

- selected skill 已知。
- rejected candidates 有原因。
- selected skill 不在 rejected candidates 中。
- decision 不能声称已经执行。
- request summary 存在。
- 不包含私有路径或 secret。

它 does not implement Router runtime。

## 非目标

- 不选择真实模型。
- 不执行 skill。
- 不调用 provider。
- 不写 memory。
- 不声明 human acceptance 或 business validation。

## 证据入口

```text
examples/agentflow/router_decision.example.json
agentflow/harness/agentflow_router.py
tests/test_agentflow_router_dry_run_validator.py
```
