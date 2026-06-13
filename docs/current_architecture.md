# Current Architecture

中文摘要：本文描述当前仍有效的 AFS 架构投影。产品入口是 `/studio/`，后端入口是 Runtime Service，核心能力是把节点 prompt、专业知识、人物/场景上下文、节点参数和 provider gate 组合成安全可追踪的创作指令。旧 Workbench、旧静态 Web、历史候选记忆审核流程和 provider 原始响应不属于当前产品面。本文只作为工程协作和接口理解依据，不声明人工验收、商业验证或 durable memory。

执行标准：任何生成链路都先保留 canonical brief、safe manifest、trace 和非声明边界，再考虑调用真实模型。secret、signed URL、本地绝对路径、媒体字节、provider 原始响应不得写入仓库或返回前端。用户偏好只是软约束，专业规则、节点参数、角色身份和场景连续性优先。

AgentFlow Studio 是 AI 内容生产的 Agent-native 生产操作层。当前 Web 产品是 **AFS Studio**：一个面向 prompt-first 创作流程的无限画布创作图谱。

The product surface is flow-native:

```text
AFS Studio canvas
  -> prompt optimization
  -> creative intent control agent trace
  -> gated keyframe generation request
  -> safe Runtime Service API
  -> deterministic artifacts or gated provider tasks
  -> reviewable evidence
```

Passing tests and browser QA are runtime verification only. They are not human acceptance, business validation, provider smoke, or durable-memory promotion.

## Code Layers

```text
apps/api/              Runtime Service, the only official backend boundary for frontend code
apps/cli/              local operations, deterministic harness, smoke entrypoints
apps/studio/           current user-facing AFS Studio canvas frontend
agentflow/             platform contracts, memory loop, harness, router, skills
agentflow_studio/      content production, workflow, distribution, provider adapters
configs/               example configuration and tool catalog contracts
examples/              committed contract fixtures
workflows/             YAML workflow definitions
docs/                  current docs, runbooks, contracts, maintenance ledgers
tests/                 automated verification
data/                  ignored runtime data; only .gitkeep is committed
```

Retired Workbench and static memory-workbench packages are no longer part of the current architecture.

## Frontend Boundary

Start the Runtime Service:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

Open:

```text
http://127.0.0.1:8790/studio/
```

Frontend code may use:

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest
- OpenAPI request and response shapes

Frontend code must not expose:

- CLI internals
- provider secrets
- local absolute media paths
- signed URLs
- provider raw responses
- private media bytes
- generated media bytes

## Current Core Capabilities

- AFS Studio canvas shell and node workflow.
- Prompt optimization API and local fallback.
- Creative intent control agent v1: deterministic constraint layering, candidate scoring, selected canonical prompt, and provider translation trace.
- Fixed visual asset APIs and graph-scoped context resolver.
- Provider Gateway v0.1 descriptor registry, account pools, Runtime image dispatch, registry-backed LLM prompt enhancement, and fake async video lifecycle contract.
- Provider descriptors use `AFS_ALLOW_REMOTE_*` gates only; legacy `NARRATOCUT_ALLOW_REMOTE_*` gate compatibility has been retired.
- Director Compiler v1 for deterministic 2D director setup translation.
- Keyframe generation Runtime API with `AFS_ALLOW_REMOTE_IMAGE` gate closed by default.
- Project Manifest v0.1.
- Safe Runtime artifacts: run trace, safe manifest, request plan, context bundle, handoff record, maintenance audit report.

Legacy/optional capabilities still exist as frozen reference implementations,
but are not the current product surface or default merge gate:

- subtitle/text -> hooks -> scripts -> clip_plans -> videos -> metadata distribution chain.
- Production Memory asset loop and related review/promotion harnesses, kept behind CLI/function tests rather than current Runtime HTTP routes.
- Frozen production-memory and distribution-chain tests run with `pytest -m legacy`; default `pytest` runs the current Runtime/Studio/contract gate.
- Runtime Service v0.2 list/import/source-assets/content-cards/canvas-draft/scene-inspector/review-decisions/export routes, hidden unless `AFS_ENABLE_LEGACY_RUNTIME_V02=true`.

## Governance

- Remote provider calls are closed by default and opened only by explicit capability gates.
- Capability gates use the `AFS_ALLOW_REMOTE_*` prefix; old `NARRATOCUT_ALLOW_REMOTE_*` names are not accepted.
- Feedback is raw evidence, not automatic memory.
- Candidate memory is not durable memory.
- Runtime Service outputs safe refs and must not leak private paths or secrets.
- Maintenance cleanup records the decision before deletion.

## Next Engineering Focus

```text
Studio interaction QA
  -> fixed visual asset QA
  -> graph context resolver hardening
  -> director compiler browser QA
  -> provider adapter smoke readiness
  -> provider-gated video slice after keyframe controllability evidence
```
