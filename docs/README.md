# AgentFlow Studio 文档入口

这页是当前文档导航。新任务优先从当前产品状态、contract、runbook、维护账本进入，不要从历史 phase 长文重新开始。

## 当前必读

- [项目规则投影](company_operating_model.md)
- [本地内测 runbook](local_internal_test_runbook.md)
- [Project Manifest contract](project_manifest_contract.md)
- [前端对接包](frontend_integration/README.md)
- [维护性重置账本](maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md)
- [Agent 项目开发规范候选](maintenance/AFS-AGENT-PROJECT-DEVELOPMENT-STANDARD-001.zh-CN.md)
- [任务追踪](../TASK_TRACKER.md)
- [开发日志](../DEVLOG.md)

## 产品与架构

- [当前架构](current_architecture.md)
- [产品路线](product_roadmap.md)
- [Artifact 对照表](agentflow_artifact_map.md)
- [Phase 15 路线旧稿](agentflow_phase15_roadmap.md)
- [Runtime readiness 旧稿](agentflow_runtime_readiness.md)
- [架构重构计划旧稿](agentflow_architecture_refactor_plan.md)
- [PR 审查清单旧稿](agentflow_pr_review_checklist.md)
- [Production Memory 架构旧稿](architecture/production_memory_architecture.md)
- [Project Manifest contract](project_manifest_contract.md)
- [Memory contract](agentflow_memory_contract.md)
- [Skill contract](agentflow_skill_contract.md)
- [Router contract](agentflow_router_contract.md)

## 本地内测与前端

- [本地内测 runbook](local_internal_test_runbook.md)
- [Local Alpha 0.3 验证目标旧稿](local_alpha_0_3_validation_goals.md)
- [Local Alpha 0.4 产品闭环旧稿](local_alpha_0_4_product_loop_goals.md)
- [Local Alpha 0.4 场景包旧稿](local_alpha_0_4_scenario_package.md)
- [Local Alpha 0.4 验收对齐旧稿](local_alpha_0_4_acceptance_reconciliation.md)
- [Memory Workbench 重设计旧稿](workbench/AFS-WORKBENCH-REDESIGN-001.md)
- [前端对接包](frontend_integration/README.md)
- [Runtime Service 前端交接](handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md)
- [本地内测落地交接](handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md)

## 维护与交接

- [维护性重置账本](maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md)
- [维护重置历史](maintenance/AFS-MAINTENANCE-RESET-001.md)
- [CLI 帮助清理](maintenance/AFS-CLI-HELP-CLEANUP-001.md)
- [主线基础清理](maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md)

## 开发命令

基础验证：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

维护审计：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

Runtime Service：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

OpenAPI：

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
```

## 历史文档处理原则

历史 phase 文档仍可作为实现背景，但不应成为新任务入口。后续清理时优先做中文摘要归档：

- 做了什么。
- 当前是否仍有效。
- 替代路径。
- 证据路径。
- 非声明边界。

机器契约、JSON key、API path、CLI command、artifact_type 和 schema_version 保留英文。
