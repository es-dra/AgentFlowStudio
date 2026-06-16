# AFS Algorithm Library Hard Refactor - 2026-06-17

中文摘要:本轮不是新增旁路功能,而是把资产卡草稿、资产记忆、
上下文选择、provider gate/safe manifest、质量反馈、revision/drift 和
action selection 收敛到 `agentflow/algorithms/`。Runtime route 只保留
HTTP 编排、store/job/artifact 和 safe error 投影。

## Scope

| Area | Decision | Reason | Verification |
|---|---|---|---|
| `apps/api/runtime_visual_assets.py` asset validation/projection | migrate | 资产清洗、公开投影和 human-confirmed 边界属于 fixed asset memory 算法 | `tests/test_api_runtime_visual_assets.py` |
| `apps/api/runtime_context_resolver.py` resolver orchestration | migrate | context selection 是核心算法,不应继续作为 Runtime route-side helper | `tests/test_api_runtime_context_resolver.py` |
| keyframe/video safe manifest shape | migrate incrementally | provider safety 需要统一 gate/manifest 语义;本轮先让新增 vision route 使用算法模块 | asset-card draft tests + existing generation tests |
| `/studio/` visual asset panel | migrate UI behavior only | Studio 只触发草稿与展示 Runtime safe state,不拼算法判断 | `tests/test_web_studio_static.py`, `node --check` |
| legacy Runtime v02 | freeze | 当前 `/studio/` 主线不依赖 v02,本轮不为它增加兼容分支 | `tests/test_api_runtime_service_v02.py` if needed |
| production-memory HTTP routes | freeze | 已从当前 Runtime surface 退休,不作为新算法调用方 | maintenance audit |

## Hard Rules

- 新业务逻辑进入 `agentflow/algorithms/`,不再塞进 `runtime_*` 巨石文件。
- draft 永远不是 fixed asset;只有 human-confirmed fixed assets 进入 context resolver。
- Vision 分析使用独立 gate `AFS_ALLOW_REMOTE_VISION`,不复用 image/video/LLM gate。
- Provider raw response、secret、signed URL、本地绝对路径、媒体字节不得进入 API JSON 或 repo artifact。

## Implementation Addendum - 2026-06-17

This slice turns the algorithm library from a planning object into executable
contracts for the current Runtime surface.

- Added `agentflow.algorithms` contract exports and kept package directories as
  the only active algorithm module shape.
- Added independent `vision` provider capability and fake vision adapter gated
  by `AFS_ALLOW_REMOTE_VISION`.
- Added `POST /projects/{project_id}/asset-card-drafts`, which returns
  `blocked` before provider work when the vision gate is closed, and returns a
  draft asset card when opened. Drafts are not fixed assets and do not enter the
  context resolver.
- Added `POST /projects/{project_id}/video-assets/promote` for human-reviewed
  video asset records.
- Added Studio client methods and minimal static UI hooks for draft asset cards
  without changing the main fixed/rejected visual asset flow.
- Kept any Company OS / GFR feedback candidate-only and outside the repository;
  no active rule was promoted automatically.

Boundary:

- No real provider smoke was run.
- No provider config or secret files were touched.
- No business, customer, cost, contract, provider raw response, media bytes, or
  durable Company OS memory was written into the repo.
- Verification proves focused structure/runtime contracts only; human
  acceptance and business validation remain separate.

Architecture closeout:

- Default pytest caught a package cycle between `agentflow.algorithms` and
  `apps.api`.
- Fixed by moving resolver assets/budget/subgraph/text/vocabulary helpers into
  `agentflow.algorithms.context_resolver.*`; Runtime now supplies
  `compile_director_setup` as an adapter callback.
- Repository retention review caught the new algorithm directories as unknown;
  `tools/repository_retention_policy.py` now classifies
  `agentflow/algorithms` as current production spine.

Verification:

```text
pytest visual/provider/static: 54 passed, 1 warning
pytest context/video revisions: 20 passed, 1 warning
pytest creative/prompt loop: 26 passed, 1 warning
pytest algorithm/asset draft/service: 17 passed, 1 warning
changed Studio JS node --check: passed
CLI help/version: passed, version 0.1.0
OpenAPI export: docs/openapi/afs-runtime-service.openapi.json updated
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0, CRLF notices only
architecture cycle + retention tests: 2 passed
focused algorithm/provider/static/context/retention suite: 57 passed, 1 warning
full default pytest: 433 passed, 527 deselected, 2 warnings
```

## Non-Goals

- 不做 M4 真人测试或服务器完整 provider smoke。
- 不改 Nginx/systemd/provider secret。
- 不恢复 retired Workbench、旧静态 Web 或 production-memory HTTP 面。
