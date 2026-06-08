# AgentFlow Studio 任务账本

最后更新：2026-06-08 by Codex

本文件只保留当前工作、下一步队列、阻塞项和证据入口。旧 Alpha、旧 Web
bridge、旧 demo 和旧逐节点 handoff 不再作为当前任务入口。

公司源头知识库：

```text
D:\Learning materials\Learning_notes\10-Startup
```

AFS 仓库只保存执行投影：代码、contract、测试、runbook、维护账本和前端安全对接材料。

## 当前操作规则

- 不再新增编号式 memory advantage demo 模块。
- 不再恢复 `apps/web_bridge` 或 `web-bridge` CLI。
- provider smoke、deterministic tests、human acceptance、business validation、durable memory 必须分开。
- 不提交 secret、provider key、signed URL、cookie、本地媒体、模型缓存、生成 runtime artifact 或公司私密资料。
- 远程 provider 调用必须按能力显式 gate。

## 当前工作

| ID | Owner role | 范围 | 状态 | 证据 |
|---|---|---|---|---|
| AFS-PRODUCT-SPINE-RESET-003 | Maintainability Steward + Architecture Reset Lead | 删除旧入口、压缩历史文档面、强化 retention review、消除旧包/CLI/Web surface | 验证中 | `docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md` |
| AFS-RUNTIME-SERVICE-V0-2-001 | Runtime/API Integrator + Frontend Contract Steward | Runtime Service、OpenAPI、frontend-safe refs、request fixture | 已合入基线 | `docs/frontend_integration/`；`docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md` |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | Product Integration Steward + Runtime/API Integrator | 外部画布前端接 Runtime Service，首屏只做 project、run、artifact、review safe view | 排队 | 前端不接触 CLI 内部、secret、私有路径、signed URL 或媒体字节 |

## 当前基线

| 模块 | 状态 | 证据 |
|---|---|---|
| Git | 当前分支 `codex/afs-product-spine-reset-003` | `git status --short --branch` |
| Production Memory Asset Loop | deterministic 本地 contract chain 已具备 | `agentflow/memory/`；`apps/cli/production_memory_command_registry.py` |
| Runtime Service | 前端主对接面 | `apps/api/`；`apps/cli/runtime_service_command.py` |
| 过渡 Web | 只保留 read-only / local-only artifact viewer | `apps/web/README.md` |
| 维护审计 | 本地维护审计和 retention review 可运行 | `tools/maintenance_audit.py`；`tools/repository_retention_review.py` |

## 下一步队列

| ID | 范围 | 状态 |
|---|---|---|
| AFS-MODEL-GATEWAY-CYCLE-001 | 解除 `agentflow_studio.model_gateway <-> agentflow_studio.production` 循环 | 下一刀 |
| AFS-WORKFLOW-HARNESS-CYCLE-001 | 解除 `agentflow_studio.harness <-> agentflow_studio.workflow_engine` 循环 | 排队 |
| AFS-CI-MAINTENANCE-GATE-001 | 加入 `maintenance_audit`、focused pytest、`git diff --check` 到 CI | 排队 |

## 当前阻塞和残留

- `maintenance_audit` 预计仍会保留低置信 secret-like warning 和 300 行以上文件 warning；只要 `failed=0` 即可继续。
- `docs/archive/` 中仍有历史引用；它们不是当前任务入口。
- Provider validation 默认关闭，除非显式授权对应 capability gate。
