# AgentFlow Studio 任务账本

最后更新：2026-06-09 by Codex

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
| AFS-MAINTENANCE-CLOSEOUT-001 | Maintainability Steward + Frontend Contract Steward | 强删旧 demo / Alpha / memory video pipeline / 旧 Web sample，调精维护审计，收紧当前 product spine | 已完成 | `docs/maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md` |
| AFS-MAINTENANCE-DEBT-CLOSURE-001 | Architecture Reset Lead + QA / Release Gatekeeper | 解除剩余包级循环、收紧架构门禁、新增 CI 维护门禁 | 已完成 | `docs/maintenance/AFS-MAINTENANCE-DEBT-CLOSURE-001.zh-CN.md` |
| AFS-MODEL-GATEWAY-CYCLE-001 | Architecture Reset Lead | 解除 `agentflow_studio.model_gateway <-> agentflow_studio.production` 循环 | 已完成 | `docs/maintenance/AFS-MODEL-GATEWAY-CYCLE-001.zh-CN.md` |
| AFS-PRODUCT-SPINE-RESET-003 | Maintainability Steward + Architecture Reset Lead | 删除旧入口、压缩历史文档面、强化 retention review、消除旧包/CLI/Web surface | 已提交 | `docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md` |
| AFS-RUNTIME-SERVICE-V0-2-001 | Runtime/API Integrator + Frontend Contract Steward | Runtime Service、OpenAPI、frontend-safe refs、request fixture | 已合入基线 | `docs/frontend_integration/`；`docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md` |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | Product Integration Steward + Runtime/API Integrator | 外部画布前端接 Runtime Service，首屏只做 project、run、artifact、review safe view | 排队 | 前端不接触 CLI 内部、secret、私有路径、signed URL 或媒体字节 |

## 当前基线

| 模块 | 状态 | 证据 |
|---|---|---|
| Git | 当前分支 `codex/afs-maintenance-debt-closure-001` | `git status --short --branch` |
| Production Memory Asset Loop | deterministic 本地 contract chain 已具备 | `agentflow/memory/`；`apps/cli/production_memory_command_registry.py` |
| Runtime Service | 前端主对接面 | `apps/api/`；`apps/cli/runtime_service_command.py` |
| 过渡 Web | 只保留 read-only / local-only artifact viewer | `apps/web/README.md` |
| 维护审计 | 本地维护审计和 retention review 可运行 | `tools/maintenance_audit.py`；`tools/repository_retention_review.py` |

## 下一步队列

| ID | 范围 | 状态 |
|---|---|---|
| AFS-FLOW-RUN-READY-001 | 基于当前低成本维护基线，进入自研轻量 Web 前的流程跑通准备 | 待启动 |
| AFS-LIGHTWEIGHT-WEB-001 | 后续自研轻量 Web，只接 Runtime Service / OpenAPI / safe artifact refs | 待启动 |

## 当前阻塞和残留

- `maintenance_audit` 的 secret-like warning 已在收口切片中降为 0；预计仍会保留 300 行以上文件 warning，后续触碰对应模块时继续拆分。
- Hidden CLI support commands 仍是兼容支持面；删除前必须做独立 CLI 协议迁移。
- Provider validation 默认关闭，除非显式授权对应 capability gate。
- 维护审计仍保留 300 行以上文件 warning；这些是后续触碰对应模块时顺手拆分的工程债，不阻塞当前低成本维护基线。
## 2026-06-09 - Oversized Maintenance Closure 001

| ID | Owner role | 范围 | 状态 | 证据 |
|---|---|---|---|---|
| AFS-OVERSIZED-MAINTENANCE-CLOSURE-001 | Maintainability Steward + Architecture Reset Lead | 删除退休成片后处理 surfaces，拆分剩余超长核心文件，清零 `maintenance_audit` oversized warning | 验证中 | `docs/maintenance/AFS-OVERSIZED-MAINTENANCE-CLOSURE-001.zh-CN.md` |

当前边界：

- 保留 Runtime Service、Production Memory Asset Loop、Project Manifest、Provider Gate、maintenance audit、read-only artifact viewer、纯切片与内容制作 workflow。
- 直接删除不再服务主线的 BGM、cover、subtitle burn、final package、delivery readiness 等后处理 pipeline、demo、SOP、旧测试。
- 本轮不写入 COS active rule；只生成 project-local Company OS feedback candidate packet。
- provider 默认关闭；未写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
最终验证：CLI help/version、`maintenance_audit`、focused pytest、full pytest、`git diff --check` 已通过；`oversized_files=0`。
