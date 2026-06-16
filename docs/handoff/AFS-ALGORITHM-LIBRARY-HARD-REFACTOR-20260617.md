# AFS Algorithm Library Hard Refactor - Handoff

Date: 2026-06-17

Branch: `codex/afs-algorithm-library-hard-refactor`

中文摘要：本次工作把 AFS 的第一批智能体算法从概念规划推进到可执行的
Runtime 合约层。重点不是扩展 UI，也不是打开真实 provider，而是先建立
`agentflow/algorithms/` 的稳定入口，把资产卡草稿、固定资产上下文边界、
provider gate / safe manifest、质量反馈和视频资产确认路径接入当前
`/studio/` 与 Runtime Service。草稿资产仍然只是候选证据，必须经过人工确认
后才能成为 fixed asset；provider smoke、人工验收、商业验证和 COS 记忆晋升
继续保持分离。COS/GFR 侧只写入启动包和 candidate feedback，不直接晋升规则。

## What Changed

- Added the first executable algorithm-library surface under
  `agentflow/algorithms/`.
- Added `vision` as an independent provider capability with default gate
  `AFS_ALLOW_REMOTE_VISION`.
- Added fake vision adapter coverage for provider registry contract tests.
- Added Runtime asset-card draft route:
  `POST /projects/{project_id}/asset-card-drafts`.
- Added Runtime video-asset promotion route:
  `POST /projects/{project_id}/video-assets/promote`.
- Added Studio client methods and static UI markers for draft asset cards and
  video asset-card drafts.
- Kept any external knowledge-base feedback as candidate-only material outside
  this repository.
- Split context resolver helper logic into algorithm-owned submodules so
  `agentflow.algorithms` no longer imports `apps.api`. Runtime now remains an
  adapter/caller and passes its director compiler callback into the algorithm.
- Classified `agentflow/algorithms` in the repository retention policy as
  current production spine.

## Current Boundary

- No real provider call was run.
- No provider config, provider secret, customer data, cost data, contract raw
  text, provider raw response, or media bytes were touched.
- Asset-card drafts are not fixed assets. They must not be included in context
  until a human promotion path creates a fixed asset record.
- Provider smoke, human acceptance, business validation, and durable-memory
  promotion remain separate claim states.

## Verification

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_assets.py tests\test_provider_adapter_registry.py tests\test_web_studio_static.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py tests\test_api_runtime_video_revisions.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_prompt_memory_loop.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_algorithm_library_contracts.py tests\test_api_runtime_asset_card_drafts.py tests\test_api_runtime_service.py -q
node --check apps/studio/src/panels/visual-asset-panel.js
node --check apps/studio/src/runtime-client.js
node --check apps/studio/src/node-actions.js
node --check apps/studio/src/main.js
node --check apps/studio/src/node-result-view.js
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs/openapi/afs-runtime-service.openapi.json
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
54 passed, 1 warning
20 passed, 1 warning
26 passed, 1 warning
17 passed, 1 warning
JS syntax checks passed
OpenAPI export passed
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0, CRLF notices only
Focused algorithm/provider/static/context/retention suite: 57 passed, 1 warning
Full default pytest: 433 passed, 527 deselected, 2 warnings
repository_retention_review --summary-only: manual_review_required_count=0
```

## Next Work

1. Decide whether this branch should commit the AFS projection separately or
   stay combined with the broader algorithm-library refactor.
2. After the algorithm layer is stable, use the provider-connected validation
   GFR packet before opening any real provider gate.

## External Feedback Boundary

Any Company OS / GFR feedback for this work remains candidate-only and outside
this repository. No rule was promoted automatically.
