# AFS ModelCallContext Contract - 2026-06-18

## Summary

Implemented the first algorithm-contract slice for the AFS six-core-algorithm
plan and extended the same contract through the current Runtime model-call
entrypoints: prompt optimization, keyframe/image generation, video generation,
visual inspect / asset-card drafting, and video revision. `ModelCallContext`
keeps algorithm state separate from provider gates, manifests, and UI actions.

## GFR Packet

- Identity: Engineering Delivery Lead + Runtime/API Integrator + Rule Steward + QA Gatekeeper.
- Task type: Deep algorithm contract / Runtime integration.
- Context packs: `engineering_delivery`, `afs_project`, `rule_steward`.
- Write scope: algorithm modules, Runtime adapters, focused tests, architecture docs, project records.
- Provider gates: closed by default; no live provider call authorized or started.
- Non-goals: SaaS, live provider smoke, human acceptance, business validation, durable memory promotion.
- Feedback route: repo records execution projection; COS feedback remains candidate/limited only.

## Changed

- Added `agentflow.algorithms.model_call_context` with safe context IDs,
  operation mapping, fixed-only asset eligibility, reference merge, feedback
  evidence, provider constraints, and unsafe text redaction.
- Added `agentflow.algorithms.request_projection` for provider-neutral request
  plans. It infers T2I/I2I/T2V/I2V from `ModelCallContext`.
- Added `agentflow.algorithms.visual_understanding` as the normalization layer
  before asset-card drafts.
- Added `fixed_asset_memory.asset_continuity_context` to make fixed/draft/
  rejected/retired eligibility explicit.
- Updated `agentflow.algorithms` taxonomy so the six core algorithms are
  separate from auxiliary engineering modules.
- Runtime prompt optimization now writes `model_call_context.json` and returns
  `model_call_context_id`.
- Runtime keyframe generation now writes `model_call_context.json` and
  `model_request_plan.json`; the legacy `keyframe_request_plan.json` references
  the same context ID.
- Runtime video generation now writes `model_call_context.json` and
  `model_request_plan.json`; blocked/gated paths expose the same
  `model_call_context_id` in the safe manifest without opening providers.
- Runtime asset-card drafts now build a `visual_inspect` context, request plan,
  and `visual_understanding_observation.json` before producing draft asset-card
  evidence. Drafts still do not enter fixed asset memory automatically.
- Runtime video revisions now write `revision_plan.json`,
  `model_call_context.json`, and `model_request_plan.json`; revision intent is
  captured as preserve/change evidence while feature/provider gates remain
  fail-closed.
- Studio Runtime base URL selection now keeps Runtime-hosted `/studio/` on a
  non-default local port same-origin, while preserving the known static/dev
  fallback to `127.0.0.1:8790`.
- Added `docs/architecture/AFS_MODEL_CALL_CONTEXT_CONTRACT.zh-CN.md`.
- Updated `docs/architecture/AFS_ALGORITHM_LIBRARY.zh-CN.md` to the current six-algorithm taxonomy.
- Updated `docs/architecture/AFS_CORE_ALGORITHM_AND_OPERATION_MAP.zh-CN.md`
  into the v3 confirmation-package framing with `ModelCallContext` in the two
  core diagrams and explicit user-link confirmation points.

## Verification

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_algorithm_library_contracts.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_asset_card_drafts.py tests\test_api_runtime_video_revisions.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py::test_runtime_client_uses_runtime_port_when_studio_is_served_from_dev_port -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json" --packets-dir "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\task-startup-packets"
.\.venv\Scripts\python.exe "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\contracts\scripts\validate_ai_native_contracts.py"
```

One earlier combined focused test command timed out before reporting a result;
the same groups passed when split.

Final default pytest result: `464 passed, 527 deselected, 2 warnings`.
Maintenance audit result: `failed=0`, warnings only.
GFR audit result: `status=pass`, checked paths 41, checked packets 3.

Browser verification:

- Started local Runtime on `http://127.0.0.1:8797` with all remote provider
  gates explicitly set to false.
- `/health` returned ready and reported Studio static ready.
- Final closeout HTTP smoke also returned `/health` ready, `/studio/` HTTP
  200, and runtime client HTTP 200 on the same local port with provider gates
  false.
- Runtime-hosted `/studio/` loaded with HTTP 200, console errors 0, page errors
  0, Runtime base URL `http://127.0.0.1:8797`, and no mobile horizontal
  overflow.
- Starter-card interaction created 3 nodes and reached saved state.
- Evidence outside the repo: Codex backups under
  `AgentFlowStudio/model-call-context-runtime-20260618-gateclosed/`, including
  `studio-browser-smoke-report.json` and `studio-browser-interaction-report.json`.

## Boundaries

- No provider gate was opened.
- No provider raw response, secret, credentialed URL, local private path, or
  media bytes were stored.
- This is structure/runtime verification only.
- This is not provider smoke, human acceptance, business validation, or durable
  memory promotion.

## Next

- After the algorithm contract is accepted, harden the user operation chain
  around the current algorithm-trigger map instead of redrawing it around
  existing buttons.
- Decide whether the current implementation evidence should update the existing
  COS feedback packet as candidate-only evidence.
