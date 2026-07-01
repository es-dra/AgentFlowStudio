# AFS Video Node Deterministic Slice Recovery - 2026-07-02

## Status

`implementation_ready_for_review`

Branch/worktree:

```text
branch: codex/afs-video-node-deterministic-slice-recovery-20260702
worktree: C:\Users\chenzy\.codex\worktrees\5529\AgentFlowStudio
base: 38c7cf5ef08b6d84217ef145129c4592866d8b49
```

## Scope

Recovered an inspectable deterministic slice for video-node first-frame inputs
and duration request contracts. The slice covers:

- direct uploaded image on a video node as valid first-frame input;
- upstream uploaded-image node to downstream video node;
- upstream generated-image/keyframe node to downstream video node;
- visual asset reference to first-frame image asset;
- explicit first-frame selection preservation;
- Runtime `input_source`, `input_mode`, and `duration_contract` propagation into
  safe model-call context, request plan, preflight, safe manifest, and task state;
- request-level duration validation for 1-15 seconds;
- provider-specific unsupported duration/input-mode errors when the video gate
  is explicitly opened;
- closed provider gate returning deterministic planning artifacts without
  starting provider calls.

## Files Touched

- `apps/studio/src/video-node-flow.js`
- `apps/studio/src/node-video-actions.js`
- `apps/studio/src/presets/specs.js`
- `apps/studio/src/runtime-client.js`
- `apps/api/runtime_video_contract.py`
- `apps/api/runtime_models.py`
- `apps/api/runtime_generation_preflight.py`
- `apps/api/runtime_model_call_context.py`
- `apps/api/runtime_video_dispatch.py`
- `apps/api/runtime_video_manifest.py`
- `apps/api/runtime_video_routes.py`
- `apps/api/runtime_errors.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `agentflow/algorithms/request_projection/__init__.py`
- `agentflow_studio/model_gateway/provider_adapter.py`
- `agentflow_studio/model_gateway/provider_adapter_impl.py`
- `agentflow_studio/model_gateway/volc_seedance_video.py`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_web_studio_video_node_contract.py`
- `tests/test_api_runtime_video_generations.py`
- `tests/test_web_studio_frontend_wave.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_api_runtime_video_generations.py::test_video_generation_gate_closed_plans_supported_duration_contract_boundaries tests\test_api_runtime_video_generations.py::test_video_generation_rejects_duration_outside_contract tests\test_api_runtime_video_generations.py::test_video_generation_gate_open_returns_structured_unsupported_duration tests\test_api_runtime_video_generations.py::test_video_generation_gate_open_returns_structured_unsupported_input_mode tests\test_api_runtime_video_generations.py::test_video_generation_request_plan_carries_input_source -q
# expected red before implementation: 8 failed, 1 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_api_runtime_video_generations.py::test_video_generation_gate_closed_plans_supported_duration_contract_boundaries tests\test_api_runtime_video_generations.py::test_video_generation_rejects_duration_outside_contract tests\test_api_runtime_video_generations.py::test_video_generation_gate_open_returns_structured_unsupported_duration tests\test_api_runtime_video_generations.py::test_video_generation_gate_open_returns_structured_unsupported_input_mode tests\test_api_runtime_video_generations.py::test_video_generation_request_plan_carries_input_source -q
# 10 passed, 1 warning

npm run check:studio-js
# JS syntax check passed: 134 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_api_runtime_video_generations.py tests\test_volc_seedance_video_adapter.py tests\test_web_studio_frontend_wave.py -q
# 50 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 854 passed, 520 deselected, 2 warnings

git diff --check
# passed
```

## Boundaries

- Provider state remained closed for verification; no `AFS_ALLOW_REMOTE_VIDEO`
  provider smoke claim is made.
- No generated media, provider raw response, signed URL, local media byte,
  secret, customer material, cost data, server sync, deploy, Runtime health,
  human acceptance, business validation, durable-memory promotion, or COS active
  rule promotion occurred.
- `docs/demo-docs-20260629/` was not touched.

## Residual Risk

- `apps/api/runtime_video_dispatch.py` and `tests/test_api_runtime_video_generations.py`
  remain oversized existing surfaces. This lane added the deterministic slice
  without broad route/test-module refactoring. A later maintenance lane should
  split video contract helpers/tests further if video work continues.
- Provider-specific live behavior was not validated because no video provider
  smoke was authorized. Current evidence is deterministic closed-gate and mocked
  gate-open contract verification.

## Next Action

Evaluator should inspect `base..HEAD` for the committed artifact, verify the
planning artifacts carry `input_source` and `duration_contract`, and decide
whether to route this to integration or request a smaller follow-up maintenance
split for the oversized Runtime video dispatch/test surfaces.
