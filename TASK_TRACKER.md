# AgentFlow Studio 任务账本

最后更新：2026-06-08 by Codex

本文件是 AFS 的活任务账本，只保留当前工作、下一步队列、阻塞项和证据入口。历史记录放到 `docs/archive/`、`docs/handoff/` 或 `docs/maintenance/`。

公司源头知识库：

```text
D:\Learning materials\Learning_notes\10-Startup
```

AFS 仓库只保存执行投影。历史文档如仍出现 `Company` 旧称，一律按 `10-Startup` 理解，后续通过 docs-only 切片继续修正。

项目内规则投影：`docs/company_operating_model.md`。

## 当前操作规则

- AgentFlow Studio 是当前主项目。
- Loulan 只是生产压力样本，不是独立产品分支。
- 不再新增编号式 memory advantage demo 模块。
- provider smoke、deterministic tests、human acceptance、business validation、durable memory 必须分开。
- 不提交 secret、provider key、signed URL、cookie、本地媒体、模型缓存、生成 runtime artifact 或公司私密资料。
- 远程 provider 调用必须按能力显式 gate。
- 正常或较大开发使用 `codex/*` 分支和隔离 worktree。
- subagent 只能用于有边界、有独立写入范围、有验证命令、有关闭条件的任务。

## 当前工作

| ID | Owner role | 范围 | 状态 | 验证 / 证据 |
|---|---|---|---|---|
| AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001 | Release Integrator + Maintainability Steward | 维护性重置、活文档中文化、`10-Startup` candidate 规则投影、本地 AgentOps artifact、维护审计脚本、逐文件保留性审查、Runtime Service trace 输出 | 已合入 master | 证据：PR #83 squash merge `aa9b1a4`；`docs/maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`；`docs/maintenance/AFS-REPOSITORY-RETENTION-REVIEW-001.zh-CN.md`；`docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`；`docs/handoff/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.md`；full pytest `1023 passed, 1 warning`；保留性审查覆盖 83 个目录和 1004 个文件，`delete_candidate_count=0`、`manual_review_required_count=0`；`maintenance_audit` 为 `failed=0, passed=4, warning=2`，人类 Markdown 中文覆盖已通过；旧 `Company` 路径扫描无命中；未调用 provider，未写 secret，未声明 human acceptance、business validation 或 durable memory |
| AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001 | Runtime/API Integrator + Product Integration Steward | Runtime Service v0.1、safe job/artifact refs、前端对接包、request fixture | 已本地验证，已并入当前维护分支脏工作树 | 证据：`docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`；`docs/frontend_integration/`；`examples/frontend_runtime_service/`；前端不接触 CLI 内部、secret、私有路径、signed URL 或媒体字节 |
| AFS-FRONTEND-ZH-HANDOFF-AND-MAINTAINABILITY-STANDARD-001 | Product Integration Steward + Maintainability Steward | 中文前端交接材料和 AFS/COS Agent 项目开发规范候选 | 已本地记录，作为 candidate guidance | 证据：`docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md`；`docs/maintenance/AFS-AGENT-PROJECT-DEVELOPMENT-STANDARD-001.zh-CN.md`；不代表 COS active-rule promotion |
| AFS-DEEP-CLEANUP-AUDIT-001 | Maintainability Steward + Full-stack Reviewer | 深度目录/调用关系/入口/文档瘦身审查，删除已被归档摘要覆盖的重复 handoff | 已执行低风险删除，待验证 | 证据：`docs/maintenance/AFS-DEEP-CLEANUP-AUDIT-001.zh-CN.md`；删除 `docs/handoff/AFS-MEM-002.md`、`docs/handoff/AFS-QA-001.md`；编号 demo、旧 Web、旧 bridge 均保留为有条件后续删除候选 |
| AFS-ARCHITECTURE-AUDIT-GATES-001 | Maintainability Steward | import boundary、hidden CLI surface、禁止新增编号 demo 的自动化门禁；减少旧 bridge 顶层依赖；下沉核心 JSON helper；拆出 provider adapter 边界；清除 `apps.cli` / `apps.web_bridge` 循环依赖 | 已合入 master | 证据：PR #83 squash merge `aa9b1a4`；`tests/test_architecture_audit_gates.py`；`docs/maintenance/AFS-ARCHITECTURE-AUDIT-GATES-001.zh-CN.md`；`apps/cli/command_registry.py` lazy import 旧 bridge；`apps.reporting.run_reports` 接管 report helper；`agentflow.harness.json_io` 接管 `write_json`；`agentflow.memory`、`apps/api`、`apps/cli` 已无 `agentflow_studio.utils` 依赖；`agentflow` 对 `agentflow_studio` 反向依赖已清零；`agentflow_studio.model_gateway.asset_profile_provider_adapter` 承接 live provider smoke；`pytest tests/test_architecture_audit_gates.py -q` 为 `6 passed`；full pytest `1023 passed, 1 warning` |
| AFS-RUNTIME-SERVICE-V0-2-001 | Runtime/API Integrator + Frontend Contract Steward | project list/import/export、job progress、OpenAPI 固定导出、前端 request fixture | focused regression 通过，待综合验证/PR | 证据：`docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md`；`docs/frontend_integration/openapi/afs-runtime-service.openapi.json`；`examples/frontend_runtime_service/project_import.request.example.json`；`pytest tests/test_api_runtime_service.py tests/test_cli_command_registry_boundaries.py -q` 为 `15 passed, 1 warning`；未调用 provider，未写 secret，未声明 human acceptance、business validation 或 durable memory |

## 当前主线基线

| 模块 | 状态 | 证据 |
|---|---|---|
| Git 主线 | `master` 停在 `98ac418`，当前维护工作在 `codex/afs-maintenance-localization-cleanup-001` | `git branch -vv` |
| Production Memory Asset Loop | deterministic 本地 contract chain 已具备 read-only Web cockpit | `docs/handoff/AFS-PRODUCTION-MEMORY-ASSET-COCKPIT-WEB-001.md` |
| 本地内测闭环 | Asset Review Screen、真实素材 harness、两轮上下文验证、Project Manifest、Provider Gate 均已实现为本地切片 | `docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md` |
| Loulan 压力样本 | Round 1 / Round 2 / provider smoke 已产生 runtime evidence | ignored runtime path：`data/processed/runs/local_internal_test/` |
| Runtime Service v0.1 | FastAPI 后端基线可为前端画布工作台提供 safe refs 和 artifact payload | `docs/frontend_integration/` |
| 维护审计 | 已有本地审计脚本和保留性审查脚本 | `tools/maintenance_audit.py`；`tools/repository_retention_review.py` |

## 下一步队列

| ID | 范围 | 依赖 | 状态 |
|---|---|---|---|
| AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001-FINALIZE | 完成活文档中文化、复跑 focused tests、`maintenance_audit`、`repository_retention_review`、`git diff --check`，更新 handoff | 当前维护分支 | 本地验证完成；正在 staging/commit/PR |
| AFS-RUNTIME-SERVICE-V0-2-QUEUE | 增加 project list/import/export、job progress、OpenAPI 固定导出、前端 client 生成说明、显式 live provider endpoint gate | 维护 PR 已合入 | 进行中：本切片先完成只读/导入导出/OpenAPI；live provider endpoint gate 仍保持后续独立切片 |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | 外部画布前端接 Runtime Service，首屏只做项目、run、artifact、review safe view | Runtime Service v0.2 和前端团队对齐 | 排队 |
| AFS-10-STARTUP-DOCS-PROJECTION-001 | 将旧 `Company` 文案统一投影为 `10-Startup` | docs-only，不与 runtime 代码混做 | 排队 |
| AFS-ARCHITECTURE-SPLIT-001 | 按维护审计结果拆分超 300 行文件，优先 Runtime Service、provider smoke、Web 过渡模块 | 维护 PR 完成后 | 排队 |
| AFS-CI-MAINTENANCE-GATE-001 | 加入 `maintenance_audit`、secret scan、focused pytest、`git diff --check` 到 CI | GitHub push/PR 后 | 排队 |

## 当前阻塞和残留

- `data/processed/pytest-basetemp/` 下多个 ignored 历史目录因 Windows 权限拒绝暂未删除，不影响 git tracked 内容。
- `maintenance_audit` 不再把历史英文长文作为当前中文化 warning；这些文档已由 `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 统一摘要归档。剩余 warning 是低置信 secret-like 字段名/测试假值和超 300 行文件。
- 旧测试 worktree 已在维护分支提交/PR 后清理；后续如再开清理或架构切片，应使用新的 `codex/*` 分支或明确复用当前维护分支。

## 归档入口

- 旧任务历史：`docs/archive/task_history_2026_06_03_pre_slimming.md`。
- 旧开发日志：`docs/archive/devlog_history_2026_06_03_pre_slimming.md`。
- 更早 2026-05 历史：`docs/archive/task_history_2026_05.md`、`docs/archive/devlog_history_2026_05.md`。
