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
- [Project Manifest contract](project_manifest_contract.md)
- [Production Memory 架构](architecture/production_memory_architecture.md)
- [Production Memory Asset Profile](architecture/production_memory_asset_profiles.md)
- [Skill contract](agentflow_skill_contract.md)
- [Router contract](agentflow_router_contract.md)

## 本地内测与前端

- [本地内测 runbook](local_internal_test_runbook.md)
- [前端对接包](frontend_integration/README.md)
- [Runtime Service 前端交接](handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md)
- [本地内测落地交接](handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md)

## 维护与交接

- [低成本维护收口](maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md)
- [维护性重置账本](maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md)
- [Product Spine Reset 账本](maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md)
- [Agent 项目开发规范候选](maintenance/AFS-AGENT-PROJECT-DEVELOPMENT-STANDARD-001.zh-CN.md)

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

历史 phase、alpha、golden path、旧 demo 和旧 smoke 文档不再作为当前任务入口。当前仓库优先保留能直接支撑代码、contract、runbook、Runtime Service、deterministic harness 和维护门禁的文档。

仍需保留历史信息时，优先写入中文摘要：

- 做了什么。
- 当前是否仍有效。
- 替代路径。
- 证据路径。
- 非声明边界。

机器契约、JSON key、API path、CLI command、artifact_type 和 schema_version 保留英文。
