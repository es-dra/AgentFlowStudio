# Production Memory Asset Profile

本文记录资产 profile 闭环的当前工程边界。详细 contract 以代码、examples 和测试为准。

## 目标

让测试人员能看清：

- 当前测哪个人物、场景和 profile version。
- 哪些 refs included。
- 哪些 refs blocked，以及 blocked 原因。
- tester feedback 中哪些 kept、partial、failed、unknown。
- 下一步建议是 `no_change`、`candidate`、`blocked`、`retired` 或 `promoted`。

## 最小链路

```text
asset profile seed
  -> asset profiles
  -> readiness
  -> test package
  -> feedback event
  -> update candidate
  -> promotion decision
  -> profile version
  -> context projection
  -> consistency review
```

## 关键对象

- `agentflow_production_memory_asset_profile_seed`
- `agentflow_production_memory_asset_profile`
- `agentflow_production_memory_asset_profile_readiness`
- `agentflow_production_memory_asset_test_package`
- `agentflow_production_memory_asset_feedback_event`
- `agentflow_production_memory_asset_profile_update_candidate`
- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`
- `agentflow_production_memory_asset_profile_context_projection`
- `agentflow_production_memory_asset_consistency_review`

## 边界

- 人物和场景共用统一 profile contract，通过 `profile_kind` 区分。
- 真实素材路径只允许进入 ignored runtime evidence。
- blocked refs 不进入下一轮 context。
- promotion/version 必须由显式 decision 生成。
- 不声明 human acceptance、business validation 或 durable memory。
