# Production Memory 架构

本文是 Production Memory 遗产层的短索引。它不再是当前 Studio MVP 主线，也不再提供默认可见 CLI 产品入口；详细事实以代码、contract example、测试和本地内测 runbook 为准。

## 目标

把一次内容生产 run 中的证据、反馈、候选、晋升决策和上下文投影组织成可审计闭环：

```text
Round 1 package
  -> tester feedback
  -> update candidate
  -> promotion decision / profile version
  -> context projection
  -> Round 2 package
  -> consistency review
  -> before/after report
```

## 遗产实现入口

```text
agentflow/memory/
apps/cli/production_memory_command_registry.py  # hidden compatibility only
examples/agentflow/production_memory_loop.example.json
docs/local_internal_test_runbook.md
```

## 关键对象

- `agentflow_production_memory_loop`
- `agentflow_production_memory_asset_profile`
- `agentflow_production_memory_asset_feedback_event`
- `agentflow_production_memory_asset_profile_update_candidate`
- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`
- `agentflow_production_memory_asset_profile_context_projection`
- `agentflow_production_memory_asset_consistency_review`
- `agentflow_project_manifest`

## 强边界

- feedback 是 raw evidence，不是 memory。
- candidate 不是 durable memory。
- blocked refs 必须保留原因，并且不能进入下一轮 context。
- provider 默认关闭，必须显式 gate。
- 运行验证不是 human acceptance。
- provider smoke 不是 business validation。
- AFS 不写 `10-Startup` / Company KB active rule。

## 相关文档

- `docs/architecture/production_memory_asset_profiles.md`
- `docs/local_internal_test_runbook.md`
- `docs/project_manifest_contract.md`
- `docs/architecture/AFS_STUDIO_FRONTEND_ARCHITECTURE_V1.zh-CN.md`
