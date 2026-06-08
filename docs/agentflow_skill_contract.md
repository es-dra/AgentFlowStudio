# AgentFlow Skill Contract

本文记录当前 skill invocation/result replay 的最小契约边界。

## 当前对象

- `agentflow_skill_invocation`
- `agentflow_skill_result`
- `agentflow_skill_replay_validation`

## 验证边界

`agentflow_skill_replay_validation` 只验证已提交或显式提供的 invocation/result 是否结构一致：

- `invocation_id` 一致。
- `skill_id` 一致。
- expected outputs 已产出。
- quality gates 通过。
- 不写 long-term memory。
- 不包含私有路径或 secret。

它 does not implement a skill runtime。

## 非目标

- 不选择 skill。
- 不执行 skill。
- 不调用 provider。
- 不写 durable memory。
- 不声明 human acceptance 或 business validation。

## 证据入口

```text
examples/agentflow/skill_invocation.example.json
examples/agentflow/skill_result.example.json
agentflow/harness/agentflow_skill.py
tests/test_agentflow_skill_replay_validator.py
```
