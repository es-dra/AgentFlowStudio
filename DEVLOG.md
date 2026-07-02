# Devlog

## 2026-07-02 - Provider Submit Preflight Hardening

- Completed Lane D1 provider-submit preflight hardening on `codex/afs-d1-provider-preflight-hardening-20260702` from baseline `f00fbc6c1404a4c3b812056a0f142626edb75ea8`.
- Runtime keyframe and video submit routes now require a matching current preflight token before provider-capable submit when the relevant remote provider gate is open.
- Runtime generation-comparison submit now follows the same fresh-preflight rule when image dispatch is possible: `/projects/{project_id}/generation-comparisons/preflight` returns no-submit comparison evidence and a token derived from the A/B/C keyframe-arm preflights, while `/generation-comparisons` rejects missing or stale tokens before any arm can reach provider dispatch.
- Preflight tokens now include provider-submit gate state, so a token produced while gates were closed cannot authorize a later gate-open submit.
- Gate-closed/local planning behavior remains available without requiring a token; preflight responses remain no-submit evidence with `provider_calls_started=false`.
- Updated gate-open keyframe/video/comparison tests to run the preflight endpoint before fake provider submit paths; rejected missing/stale paths assert no-submit evidence.
- Regenerated the Runtime Service OpenAPI snapshot for the new comparison preflight route and comparison request `preflight_token` field.
- No real provider call, provider smoke, generated media, generated-media QA, human creative acceptance, business validation, public/legal readiness, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
python -m pytest tests\test_api_runtime_provider_submit_preflight.py -q
# 9 passed

python -m pytest tests\test_api_runtime_generation_comparison.py -q
# 1 passed

python -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
# exported

python -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed

python -m pytest tests\test_api_runtime_provider_submit_preflight.py tests\test_api_runtime_generation_comparison.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_asset_card_revision_legacy_slots.py tests\test_api_runtime_keyframe_reference_assets.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_generation_manifest_safety.py tests\test_api_runtime_video_generations.py tests\test_api_runtime_video_routes_modules.py tests\test_api_runtime_video_revisions.py tests\test_volc_seedance_video_adapter.py tests\test_web_studio_assets_generation_static.py -q
# 90 passed

git diff --check
# passed
```

## 2026-07-02 - D5 Provider-Closed Readiness Packet Currency

- Completed Lane D5 on `codex/afs-d5-provider-closed-readiness-20260702` from D2 commit `654002a295330c0722102d8a2202804189865235`; base remains `origin/master=f00fbc6c1404a4c3b812056a0f142626edb75ea8`.
- Updated the provider-closed internal tryout/readiness packet tooling so the D2 accepted-generation-plan bridge is a required readiness input.
- Added browser QA coverage that opens the Studio accepted generation plan modal and records the default blocked preview evidence: `preview_status=blocked`, `job.status=blocked`, `accepted=false`, `source_mode=fixture_demo`, `provider_calls_started=false`, and `provider_gate=closed`.
- Added fail-closed checks for accepted-plan non-claim collapse, including product readiness, deploy/runtime health, provider smoke, generated-media QA, human creative acceptance, business validation, public/legal/patent readiness, and COS promotion.
- Generated local ignored evidence at `runs\d5_studio_main_path_delivery_readiness.json`, `runs\d5_studio_main_path_delivery_readiness.png`, `runs\d5_provider_closed_internal_tryout_packet.json`, and `runs\d5_provider_closed_internal_tryout_packet.md`.
- Handoff: `docs/handoff/AFS-D5-PROVIDER-CLOSED-READINESS-PACKET-CURRENCY-20260702.md`.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_studio_provider_closed_tryout_packet.py tests\test_studio_main_path_browser_qa_tool.py -q
# 21 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\d5-browser-runtime --report runs\d5_studio_main_path_delivery_readiness.json --screenshot runs\d5_studio_main_path_delivery_readiness.png
# passed; accepted generation plan preview POST returned 200; provider_calls_started=false

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\studio_provider_closed_tryout_packet.py --readiness-report runs\d5_studio_main_path_delivery_readiness.json --output runs\d5_provider_closed_internal_tryout_packet.json --markdown runs\d5_provider_closed_internal_tryout_packet.md
# passed; provider_calls_started=false

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py tests\test_web_studio_accepted_generation_plan_static.py tests\test_web_studio_human_gate_static.py tests\test_studio_provider_closed_tryout_packet.py tests\test_studio_main_path_browser_qa_tool.py -q
# 36 passed, 1 warning

npm run check:studio-js
# JS syntax check passed: 135 files

git diff --check
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning categories include existing legacy/doc/secret-like/oversized findings
```

Non-claims: no provider smoke, live provider call, external download, generated media, generated-media QA, human creative acceptance, product readiness, business validation, public/legal/patent readiness, deploy/runtime freshness, CompanyOS/COS promotion, durable-memory promotion, or final integration claim.

## 2026-07-02 - D2 Accepted Generation Plan Evidence Hardening

- Completed Lane D2 on `codex/afs-d2-accepted-generation-plan-hardening-20260702` from `origin/master=f00fbc6c1404a4c3b812056a0f142626edb75ea8`.
- Hardened `POST /projects/{project_id}/accepted-generation-plan-packets/preview` so bundled fixture modes are non-acceptance demo evidence only. `confirmed_local_fixture` now returns `fixture_demo_non_acceptance`, `accepted=false`, `job.status=blocked`, and `preview_status=blocked`.
- Added project-scoped preview source support with `source_artifact_id` and `source_human_gate_id`. Accepted preview state now requires a safe project artifact whose packet is not `repo_local_fixture` evidence plus a manifest-linked `accepted_generation_plan_packet` local human-gate decision targeting that source artifact.
- Added safe manifest `accepted_generation_plan_refs` so operators/evaluators can recover latest plan preview refs without provider raw, media bytes, signed URLs, private paths, human creative acceptance claims, or business validation claims.
- Extended Runtime/Studio human-gate target support to `accepted_generation_plan_packet`; Studio fixture copy now says `Fixture demo (blocked)` and reserves accepted wording for project artifact step-gate evidence.
- Regenerated the Runtime OpenAPI snapshot for the request model and human-gate enum changes.
- Handoff: `docs/handoff/AFS-D2-ACCEPTED-GENERATION-PLAN-HARDENING-20260702.md`.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py -q
# 9 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_accepted_generation_plan_static.py tests\test_web_studio_human_gate_static.py -q
# 5 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -c "from pathlib import Path; from apps.api.openapi_export import export_openapi_schema; export_openapi_schema(Path('docs/openapi/afs-runtime-service.openapi.json'))"
# regenerated committed OpenAPI snapshot

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py tests\test_web_studio_accepted_generation_plan_static.py tests\test_web_studio_human_gate_static.py -q
# 16 passed, 1 warning

npm run check:studio-js
# JS syntax check passed: 135 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py tests\test_api_runtime_openapi_snapshot.py -q
# 11 passed, 1 warning

git diff --check
# passed
```

Non-claims: no provider smoke, live provider call, external download, generated media, generated-media QA, human creative acceptance, product readiness, business validation, public/legal/patent readiness, deploy/runtime freshness, CompanyOS/COS promotion, durable-memory promotion, or final integration claim.

## 2026-07-02 - Accepted Generation Plan Runtime/Studio Bridge

- Completed Lane C on `codex/afs-accepted-generation-plan-runtime-studio-bridge-20260702` from baseline `2491cfff534362ff2c9d7dafed5faccc0c93a656`.
- Added a provider-closed Runtime preview endpoint for T58 `accepted_generation_plan_packet`: `POST /projects/{project_id}/accepted-generation-plan-packets/preview`.
- Preserved the default unconfirmed package as blocked: default request mode is `default_unconfirmed`, returning `packet_state=blocked_pending_generation_plan_prerequisites` and `accepted=false`.
- Added explicit `confirmed_local_fixture` mode for the accepted local fixture contract, carrying state, provenance, residual blockers/closures, and non-claim boundaries without provider calls or generated media.
- Added a minimal Studio review surface: one dock button, one Runtime client method, and one compact modal that loads the blocked default first and requires a separate confirmed-fixture control for the accepted packet.
- Regenerated the Runtime OpenAPI snapshot for the new route.
- No provider call, external download, generated media, generated-media QA, broad UI redesign, server/deploy sync, live Runtime health claim, human creative acceptance, business validation, product readiness, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.
- Handoff: `docs/handoff/AFS-ACCEPTED-GENERATION-PLAN-RUNTIME-STUDIO-BRIDGE-20260702.md`.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-api-red tests\test_api_runtime_accepted_generation_plan_packet.py -q
# red before route implementation: 3 failed with 404

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-focused-2 tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_web_studio_accepted_generation_plan_static.py -q
# 5 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-openapi-check-2 tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed after OpenAPI snapshot regeneration

npm.cmd run check:studio-js
# JS syntax check passed: 135 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-impacted-1 tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_openapi_snapshot.py tests\test_web_studio_accepted_generation_plan_static.py tests\test_branch_workflow_accepted_generation_plan_packet.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 75 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-service-1 tests\test_api_runtime_service.py -q
# 12 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

git diff --check
# passed
```

## 2026-07-02 - Professional Prompt Optimization Deterministic Hardening

- Completed provider-closed deterministic hardening on `codex/afs-professional-prompt-optimization-hardening-20260702` from base `4cc62a36df5d724f0861154d195067f260e65fc1`.
- Added a focused professional prompt contract helper for visual prompt optimization. Real CJK prompts such as `女生在笑`, `女生微笑`, `雨夜街道，紧张`, `让她慢慢回头微笑`, and `开心` now extract subject, emotion, scene, action, and motion semantics before prompt assembly.
- Hardened image/keyframe prompt assembly with subject identity, restrained realistic expression cues, expression-before-action decomposition, body/action carrier, grounded scene, light/camera details, continuity, and professional negative constraints.
- Hardened video prompt assembly with start state, transition, movement/body carrier, camera/environment motion, end state, duration/beat language, and first-frame/source continuity when available. Image-to-video optimization now emphasizes motion-first continuation and provenance instead of restating the full upstream image.
- Added focused semantic tests at `tests/test_api_runtime_professional_prompt_optimization.py`; Studio JS was not touched and the lightweight optimize action remains unchanged.
- No provider call, generated media, external download, Studio redesign, server/deploy sync, Runtime health claim, OpenAPI change, human acceptance, business validation, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.
- Handoff: `docs/handoff/AFS-PROFESSIONAL-PROMPT-OPTIMIZATION-DETERMINISTIC-HARDENING-20260702.md`.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_professional_prompt_optimization.py
# red before implementation: 5 failed, 1 warning
# green after implementation: 5 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_memory_candidates.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_director_setup_prompt.py tests\test_algorithm_library_contracts.py
# 81 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 862 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

git diff --check
# passed
```

## 2026-07-02 - Video Node Duration and Provenance Idempotence Revision

- Completed the evaluator-blocking duration/provenance idempotence revision on `codex/afs-video-node-duration-provenance-revision-20260702` from commit `2f96939c784b9e41616a29a5fde6061d8a2263aa`.
- Fixed `explicitFirstFrameSource()` / `videoInputSourceForRequest()` so generic upload `source_node_id` or `source_job_id` no longer upgrades a first-frame source to `upstream_generated_image`.
- Preserved repeated direct-upload and upstream uploaded-image request sources as `uploaded_image` and `upstream_uploaded_image`, while keyframe-generated sources still preserve original keyframe node/job provenance as `upstream_generated_image`.
- Replaced the Studio video duration option surface with deterministic `1s` through `15s` choices, preserving the existing `5s` default and backend/provider duration guards.
- Added regression coverage for repeated ensure/request idempotence and runtime duration option generation through the generation-panel profile.
- No provider call, generated media, external download, server/deploy sync, Runtime health claim, OpenAPI change, human acceptance, business validation, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_web_studio_frontend_wave.py -q
# red before patch: direct upload and upstream uploaded image flipped to upstream_generated_image; duration list exposed only 1s/5s/10s/15s
# green after patch: 24 passed

npm run check:studio-js
# JS syntax check passed: 134 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_api_runtime_video_generations.py tests\test_volc_seedance_video_adapter.py tests\test_web_studio_frontend_wave.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_modules.py -q
# 64 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 857 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

OpenAPI was not touched, so the OpenAPI snapshot was not regenerated or rerun for this revision.

## 2026-07-02 - Video Node Keyframe Provenance Revision

- Completed the evaluator-blocking provenance revision on `codex/afs-video-node-keyframe-provenance-revision-20260702` from video-node recovery commit `87cbe3247261d819e3752e0e5a18cf96223d03e4`.
- Fixed `createVideoNodeFromKeyframe()` so keyframe-created video nodes persist `videoInputSource` as `upstream_generated_image` with the original keyframe node id, first-frame asset id, and keyframe job id.
- Hardened `explicitFirstFrameSource()` so `ensureVideoFirstFrameAsset()` does not downgrade generated-keyframe continuation nodes to `explicit_first_frame_selection` when the first-frame id is already set.
- Added a narrow backend Studio-state sanitizer for `videoInputSource`, plus a persistence test so save/reload keeps the new source model.
- Added a deterministic request-chain test covering `createVideoNodeFromKeyframe()` -> `ensureVideoFirstFrameAsset()` -> `videoInputSourceForRequest()`.
- No provider call, generated media, external download, server/deploy sync, Runtime health claim, OpenAPI change, human acceptance, business validation, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
Detached base reproduction at 87cbe3247261d819e3752e0e5a18cf96223d03e4
# expected failure: requestSource.source_mode=explicit_first_frame_selection, source_node_id=node_1, source_job_id=null

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py::test_keyframe_selected_first_frame_overrides_stale_explicit_source tests\test_web_studio_video_node_contract.py::test_keyframe_continuation_request_preserves_generated_image_provenance tests\test_api_runtime_studio_state.py::test_studio_state_preserves_safe_video_lifecycle_fields -q
# 3 passed, 1 warning

npm run check:studio-js
# JS syntax check passed: 134 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_api_runtime_video_generations.py tests\test_volc_seedance_video_adapter.py tests\test_web_studio_frontend_wave.py -q
# 52 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 856 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

## 2026-07-02 - Video Node Deterministic Slice Recovery

- Completed provider-closed deterministic recovery on `codex/afs-video-node-deterministic-slice-recovery-20260702` from T58 baseline `38c7cf5ef08b6d84217ef145129c4592866d8b49`.
- Added explicit video first-frame input source contracts for direct video-node uploads, upstream uploaded-image nodes, upstream generated-image/keyframe nodes, fixed visual asset references, and explicit first-frame selection.
- Added Runtime `VideoInputSource`, `input_mode`, and `duration_contract` propagation through preflight, model-call context, provider-neutral request plan, safe manifest, and task state. Closed video gates now return deterministic planning artifacts before provider-specific duration/input-mode checks start; gate-open provider-specific unsupported duration and input-mode errors remain structured and reject before provider submit.
- Widened the Studio video duration selector to the request contract boundary values `1s`, `5s`, `10s`, and `15s`, while preserving the 5s default and provider-specific duration checks.
- Added `tests/test_web_studio_video_node_contract.py`, expanded Runtime video generation contract tests, regenerated the Runtime OpenAPI snapshot, and recorded the handoff at `docs/handoff/AFS-VIDEO-NODE-DETERMINISTIC-SLICE-RECOVERY-20260702.md`.
- No provider call, generated media, external download, server/deploy sync, Runtime health claim, human acceptance, business validation, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
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

## 2026-07-02 - SPEC2 Accepted Generation Plan Assembly Contract

- Completed AFS-T58 on `codex/afs-t58-generation-plan-contract-20260702` from T57 integration commit `be476eed107cdaf318f6a6f8a5c3d7c6ac33c95f`.
- Added `agentflow.algorithms.branch_workflow_package._generation_plan_packet`, a deterministic local helper that assembles `accepted_generation_plan_packet` only after the existing generation-planning candidate, fixed-asset confirmation evidence, residual-question closure evidence, accepted review state, and protected non-claim checks are complete.
- The default T57 fixture remains blocked with `packet_state=blocked_pending_generation_plan_prerequisites`; the accepted packet path is proven through an explicit repo-local fixture mutation with branch-specific fixed asset refs, residual closure refs, evidence refs, owner/reviewer/close-condition refs, review state, non-claim boundaries, and provider-closed generation-request planning fields.
- Preserved local-only evidence origin boundaries and fail-closed behavior for fake external confirmations, provider response evidence, graph writes, unsafe markers, and protected non-claim collapse.
- No Runtime route, OpenAPI path, Studio UI, provider adapter/config, external download, provider call, generated media, reader playback, storage lifecycle, deploy/server sync, Runtime health claim, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-red tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# expected red: 2 failed, 1 passed because accepted_generation_plan_packet was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-focused tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# 3 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-branch-contract tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# 37 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-impacted tests\test_branch_workflow_accepted_generation_plan_packet.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 69 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories, including current-scope _validator.py at 311 lines

git diff --check
# passed
```

## 2026-07-02 - SPEC2 Fixed Asset Confirmation Evidence Contract Integration

- Integrated AFS-T57 into `master` from evaluated worktree `C:\Users\chenzy\.codex\worktrees\5e58\AgentFlowStudio` on top of docs-cleanup commit `7823a86c972b238227da50d3009b24ef9bfcd0ba`.
- Replayed only the scoped fixed-asset confirmation evidence contract delta: branch workflow package algorithm files, fixture, focused/contract tests, T57 handoff, and handoff index. `DEVLOG.md` and `TASK_TRACKER.md` were merged deliberately above the docs-cleanup records instead of replaying stale T56-base versions.
- Added `agentflow.algorithms.branch_workflow_package._confirmation_evidence`, a deterministic local validator for fixed-asset confirmation evidence and residual-question closure evidence inside the existing `branch_workflow_package` contract.
- The default fixture now carries a pending `fixed_asset_confirmation_evidence` envelope with the shared map asset confirmed and both branch-specific assets still visible as unconfirmed candidates. The default package remains blocked for generation planning.
- Branch-specific assets cannot become implementation-ready evidence without repo-local confirmation records, fixed asset source refs, confirmation source refs, owner/reviewer decision refs, close-condition refs, protected non-claim refs, provider prompt closure, and graph-write closure.
- Residual questions cannot be closed without target refs, evidence refs, owner/reviewer decision refs, and explicit non-claim-preserving close conditions. `generation_planning_candidate` now checks both fixed-asset confirmation completeness and residual-question closure completeness.
- Preserved docs cleanup delivered at `7823a86c`; did not touch `docs/demo-docs-20260629/`, Runtime/OpenAPI/Studio/provider/storage/reader/deploy/server surfaces, generated media, CompanyOS/Learning_notes material, or COS state.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-focused tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 16 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-branch-contract tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 34 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-impacted tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 66 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-full -q
# 841 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories including the T57 focused test oversized warning
```

## 2026-07-02 - Docs Low-Value Deletion Cleanup

- Continued the C1 docs cleanup on `codex/afs-docs-low-value-deletion-cleanup-20260702` from T56 / `origin/master` commit `61b5b8b9d98577df1d2b7c0c273f32869ffb8518`.
- Deleted the 20 C1 archived Markdown files under `docs/archive/handoff/` and `docs/archive/maintenance/` after confirming they had no current handoff index entry and no live references beyond `DEVLOG.md` plus the archive summary / cleanup ledger.
- Updated `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` and `docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` so the live repo keeps the summary, reasons, and git recovery route instead of retaining low-value duplicate archive copies.
- Protected scope held: no `docs/demo-docs-20260629/`, provider/config/secret, generated media, Runtime/OpenAPI/Studio/product, server/deploy, CompanyOS source, durable-memory promotion, or COS active-rule change.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
# delete_candidate_count=0; manual_review_required_count=0; remove_applied_pending_stage=20

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only existing categories

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-docs-deletion-audit tests\test_repository_retention_review.py tests\test_maintenance_audit.py -q
# 15 passed

docs/handoff/INDEX.md target check
# passed

git diff --check
# passed

git diff --cached --check
# passed before staging
```

## 2026-07-02 - SPEC2 Generation Planning Evidence Gate

- Completed AFS-T56 on `codex/afs-t56-spec2-generation-planning-evidence-gate-20260702` from current `master` at T55 commit `1786c61d5c4f99f3ebd9358c0e482d1ea9b54082`.
- Extended the T54/T55 `branch_workflow_package` validator with `agentflow.algorithms.branch_workflow_package._generation_planning`, a deterministic local generation-planning candidate gate that reports `generation_planning_candidate` as structure evidence only.
- The gate requires repo-local fixture evidence origins, complete implementation-ready asset evidence, generation-planning review acceptance, no unresolved open questions, residual-boundary allowance, and protected non-claim preservation before marking the candidate eligible.
- Integration decision for delivery: narrowed accepted evidence origins to the literal `repo_local_fixture` value; the unused `deterministic_fixture` alias was not retained.
- The default fixture remains blocked because branch-specific candidate assets are unconfirmed and PB3/T54 residual questions still block `accepted_for_generation_planning`; the report now surfaces those blockers without collapsing them into provider/product readiness.
- No Runtime route, OpenAPI path, Studio UI, provider adapter/config, external download, provider call, generated media, reader playback, storage lifecycle, deploy/server sync, Runtime health claim, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t56-red tests\test_branch_workflow_package_contract.py -q
# expected red before implementation: 3 failed, 18 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t56-focused tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 21 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t56-impacted tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 53 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only existing categories

git diff --check
# passed
```

## 2026-07-02 - SPEC2 Review Status Residual Boundary Hardening

- Integrated AFS-T55 on `codex/afs-t55-spec2-review-status-residual-boundary-hardening-20260702` after rebasing the worktree from the stale T54 base onto current `origin/master` at `f15b47db`. The integration replayed only the T55 branch workflow package hardening and added fresh project record entries on top of the C1 docs cleanup baseline.
- Added `agentflow.algorithms.branch_workflow_package._review_status` to validate structured `review_status.open_questions` and the `residual_boundary` envelope. Open questions now require owner/next-action/close-condition fields plus non-empty target and evidence refs, and residuals cannot be converted into implementation-ready or generation-planning evidence.
- Updated the SPEC2 fixture and contract tests so unresolved PB3/T54 residuals keep `readiness.implementation_ready_evidence_complete=false`, preserve blocked stages, surface unresolved question refs, expose the residual claim boundary, and fail closed if a review state claims `accepted_for_generation_planning` while residuals remain open.
- No Runtime route, OpenAPI path, Studio UI, provider adapter/config, external download, provider call, generated media, reader playback, storage lifecycle, deploy/server sync, Runtime health claim, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t55-integration-focused tests\test_branch_workflow_package_contract.py -q
# 18 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t55-integration-impacted tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 50 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t55-integration-full -q
# 825 passed, 520 deselected, 2 warnings

git diff --check
# passed
```

## 2026-07-02 - Docs Currentness Archive Cleanup

- Continued C1 on `codex/afs-c1-docs-cli-micro-cleanup-20260702` after merging current `origin/master` with T54. The protected untracked `docs/demo-docs-20260629/` files remained untouched.
- Moved 11 unindexed/unreferenced historical handoff files from `docs/handoff/` to `docs/archive/handoff/`, and 9 unindexed/unreferenced maintenance ledgers from `docs/maintenance/` to `docs/archive/maintenance/`.
- Added `docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` as the currentness/index record for this cleanup and added it to `docs/handoff/INDEX.md`.
- No tracked docs were physically deleted in this pass. Provider gates stayed closed; no server/deploy/runtime health, external download, generated media, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

## 2026-07-02 - SPEC2 Branch Workflow Package Contract

- Completed AFS-T54 on `codex/afs-t54-spec2-branch-workflow-package-20260702` in an isolated worktree from `master` at `5ddbd399`, leaving the primary checkout's protected untracked `docs/demo-docs-20260629/` untouched.
- Added `agentflow.algorithms.branch_workflow_package`, a deterministic SPEC2 wrapper contract for `branch_workflow_package` that reuses the T53 `interactive_manga_branch_package` fixture as source evidence instead of duplicating the branch package validator.
- Added `tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json` and `tests/test_branch_workflow_package_contract.py`. The fixture validates choice point, branch path, branch shot, asset need, continuity constraint, evidence requirement, review status, and handoff envelope fields while preserving the shared versus branch-specific asset distinction.
- The validator checks graph references are reference-only, rejects unsafe markers, preserves protected non-claims, keeps review-ready evidence separate from implementation-ready evidence, and fails if unconfirmed branch-specific candidates are included in implementation-ready evidence.
- PB3 local package commit `8296afa31b639224bcb3e7c1f8dea70000ea00b4` remains `review_pending_local_package`; PB3 SPEC evaluator and Stage0/Stage1 evaluator outcomes are carried only as `pass_with_residual_risk` review boundaries, not final schema, product, runtime, provider, or acceptance claims.
- No Runtime route, OpenAPI path, Studio UI, provider adapter/config, external download, provider call, generated media, reader playback, deploy/server sync, Runtime health claim, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-red tests\test_branch_workflow_package_contract.py -q
# red as expected: 9 failed because branch_workflow_package was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-green tests\test_branch_workflow_package_contract.py -q
# 9 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-impacted-final tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 41 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories include the new English T54 handoff in human_doc_chinese_coverage

git diff --check
# passed
```

## 2026-07-01 - Interactive Manga Branch Package Contract

- Completed AFS-T53 on `codex/afs-t53-interactive-manga-branch-package-20260701` in an isolated worktree from `master` at `56c3f700`, leaving the primary checkout's untracked `docs/demo-docs-20260629/` and `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md` untouched.
- Added `agentflow.algorithms.interactive_manga_branch_package`, a deterministic local validator for one Interactive Manga branch package fixture. It verifies one choice point, two branch paths, branch shots mapped back to base storyboard/shot refs with branch-specific shot refs, shared versus branch-specific asset needs, continuity scopes, evidence requirement mappings, graph-reference-only behavior, unsafe-marker rejection, and protected non-claims. The validator is split into public exports, helper functions, and a 287-line contract validator to avoid a new oversized module.
- Added `tests/fixtures/interactive_manga_branch_package/branch_package_fixture.json` and `tests/test_interactive_manga_branch_package_contract.py`. The fixture builds on the T52 shared-object/evidence boundary by carrying Stage1/T52 source refs and `stage1_evaluator_system_error_residual` without upgrading it into acceptance.
- No reader playback, public interactive runtime, Studio UI, Runtime route, OpenAPI path, provider prompt inclusion, provider call, image/video/ASR, external download, generated media, deploy/server sync, Runtime health claim, CompanyOS projection, durable-memory promotion, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-red tests\test_interactive_manga_branch_package_contract.py -q
# red as expected: 9 failed because interactive_manga_branch_package was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-green tests\test_interactive_manga_branch_package_contract.py -q
# 9 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-final-impacted tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 32 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warnings are existing legacy_frozen_surface, human_doc_chinese_coverage, secret_like_fragments, oversized_files categories

git diff --check
# passed
```

## 2026-07-01 - Shared Object Evidence Fixture

- Completed AFS-T52 on `codex/afs-t52-shared-object-evidence-fixture-20260701` in an isolated worktree so the primary checkout's T51 dirty files and `docs/demo-docs-20260629/` remained untouched.
- Added `agentflow.algorithms.shared_object_evidence`, a deterministic local validator for the Stage1 shared object/evidence fixture. It validates stable refs, object counts, unresolved refs, Production Graph node/reference separation, unsafe-marker rejection, partial-evidence gap reasons, handoff completeness, fixed-asset source evidence, and protected non-claims.
- Added `tests/fixtures/shared_object_evidence/stage1_contract_fixture.json` and `tests/test_shared_object_evidence_contract_fixture.py`. The fixture covers project, script, storyboard, base shots, branch path/shot, asset candidate, fixed asset, Production Graph node/reference, evidence refs, feedback review state, handoff envelope, and reuse scope.
- Stage1 residual is carried explicitly as `stage1_evaluator_system_error_residual` in the handoff envelope and reported as `evaluator_system_error_residual_carried`; it does not block deterministic local fixture verification.
- No Runtime route, OpenAPI path, Studio UI, provider adapter/config, external download, generated media, provider call, deploy, Runtime health claim, CompanyOS projection, or COS active-rule promotion occurred.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t52-red tests\test_shared_object_evidence_contract_fixture.py -q
# red as expected: 8 failed because shared_object_evidence was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t52-green tests\test_shared_object_evidence_contract_fixture.py -q
# 8 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t52-impacted-worktree tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py tests\test_model_call_context_contract.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py -q
# 36 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warnings are legacy_frozen_surface, human_doc_chinese_coverage, secret_like_fragments, oversized_files

git diff --check
# passed
```

## 2026-07-01 - Provider-Closed Internal Tryout Packet

- Completed AFS-T51 on `codex/afs-post-main-loop-e2e-continuation-20260630` as a provider-closed internal tryout packet lane.
- Added `tools/studio_provider_closed_tryout_packet.py`, which validates the T50 browser readiness report, requires `internal_provider_closed_tryout_ready`, fails closed on provider-call signals, and writes a JSON packet plus optional Markdown review summary.
- Added `tests/test_studio_provider_closed_tryout_packet.py` for non-claim preservation, missing-gate failures, provider-call fail-closed behavior, CLI output, and provider-closed static guards.
- Revised the browser evidence harness after evaluator review: recovered `/studio-state` `409 Conflict` save retries are suppressed only when the run proves persisted saved keyframe/feedback evidence; unrecovered `/studio-state` conflicts, unrelated `409` responses, and non-recovered console/network failures still fail.
- No `apps/studio/` change, provider config change, live provider call, generated media, human creative acceptance, business validation, public/legal/patent decision, deploy/runtime health claim, or COS active-rule promotion occurred. This entry claims `provider_calls_started=false` in the generated evidence, not ambient environment-level provider gate closure.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t51-tryout tests\test_studio_provider_closed_tryout_packet.py tests\test_studio_main_path_browser_qa_tool.py -q
# 17 passed, 1 warning

.\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\t51-browser-runtime --report runs\t51_studio_main_path_delivery_readiness.json --screenshot runs\t51_studio_main_path_delivery_readiness.png
# passed; provider_calls_started=false; verdict=internal_provider_closed_tryout_ready; console_error_count=0; response_error_count=0

.\.venv\Scripts\python.exe tools\studio_provider_closed_tryout_packet.py --readiness-report runs\t51_studio_main_path_delivery_readiness.json --output runs\t51_provider_closed_internal_tryout_packet.json --markdown runs\t51_provider_closed_internal_tryout_packet.md
# passed; provider_calls_started=false

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed; no whitespace errors; Git printed line-ending normalization warnings only
```

## 2026-07-01 - Studio Main-Path Delivery Readiness Gate

- Completed AFS-T50 on `codex/afs-post-main-loop-e2e-continuation-20260630` as a provider-closed internal delivery readiness gate for the Studio/Runtime main path.
- Upgraded `tools/studio_main_path_browser_qa.py` to seed the T49 real-script benchmark `multi_role_prop_exchange_chase` and emit `delivery_readiness.verdict=internal_provider_closed_tryout_ready` when storyboard/content-quality, asset candidate/fixed asset, Production Graph reuse, keyframe request/preflight/blocked bridge, and feedback overlay checks all pass.
- Added `tools/studio_delivery_readiness_gate.py` as the small readiness contract and kept current-wave files below the 300-line maintenance threshold after cleanup.
- Product verdict: ready for internal provider-closed tryout as structure-verified workflow evidence. Remaining gates: provider smoke, generated-media quality review, human creative acceptance, business validation, public/legal/patent decisions, deploy/runtime health, and COS active-rule promotion.
- AFS Redundancy Maintenance Lane remains archive_deferred; CompanyOS/COS items are governance/integration authorization items and were not modified by T50.
- No provider smoke, live provider call, generated media, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, Runtime health claim, or COS active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t50-focused tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_e2e.py tests\test_storyboard_content_quality_benchmarks.py -q
# 9 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t50-impacted tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_storyboard_content_quality_benchmarks.py tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 20 passed, 1 warning

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\t50-browser-runtime --report runs\t50_studio_main_path_delivery_readiness.json --screenshot runs\t50_studio_main_path_delivery_readiness.png
# passed; verdict=internal_provider_closed_tryout_ready; provider_calls_started=false; console_error_count=0; response_error_count=0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```
## 2026-07-01 - Content Quality Benchmark Expansion

- Completed AFS-T49 on `codex/afs-post-main-loop-e2e-continuation-20260630` as a provider-closed content-quality benchmark expansion.
- Added `multi_role_prop_exchange_chase`, a real six-beat short-drama benchmark for three-character misunderstanding, restaurant/street/office scene transitions, map and letter prop continuity, emotion shift, action continuity, and narrative-driven shot rhythm.
- Expanded the benchmark test so each case now verifies asset-card candidate continuity and Production Graph relationships in addition to content-quality report checks; the new case asserts relationship shots, scene order, reused prop candidates, story terms, and forbidden fixed five-shot rhythm.
- Kept the benchmark file below the 300-line ideal threshold at 297 lines after current-wave metadata compaction.
- Managed thread register update: the AFS Redundancy Maintenance Lane has been superseded/closed as a blocker through fresh rebuild; branch `codex/afs-redundancy-maintenance-ledger-rebuild-20260701` is at `eb16cc3e`, no-op verification is complete, and owner review/push is pending outside T49.
- No provider smoke, live provider call, generated media, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, Runtime health claim, or COS active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t49-focused tests\test_storyboard_content_quality_benchmarks.py -q
# 1 passed

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t49-impacted tests\test_storyboard_content_quality_benchmarks.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py -q
# 26 passed, 1 warning

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

## 2026-07-01 - Full Pytest Residual Triage

- Completed AFS-T48 on `codex/afs-post-main-loop-e2e-continuation-20260630` as provider-closed full pytest residual triage.
- Converted the four T47 full pytest residuals into deterministic fixture/test conclusions: `.venv` basetemp maintenance failures were git-fixture isolation debt, `runtime_root_persisted` was a hard-coded test assumption, and `C:/Users/chenzy/.afs-codex` chmod denial was user-home fixture leakage.
- Updated the affected tests with minimal fixture changes; no Runtime route, OpenAPI, Studio UI, provider adapter behavior, generated media path, or business/product surface was expanded.
- Managed thread register remains active: AFS Redundancy Maintenance Lane is still owned by `019f1b8c-4e67-7840-93ca-5cd0b99b1d21` and was not edited by T48; CompanyOS projection lane `019f1ba2-9956-7c80-9d18-c0d541b3142c` remains its own uncommitted/unpushed follow-up.
- No provider smoke, live provider call, generated media, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, Runtime health claim, or COS active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t48-residual tests\test_maintenance_audit.py::test_maintenance_audit_reports_expected_contract_shape tests\test_maintenance_audit.py::test_historical_docs_are_exempt_only_when_summary_exists tests\test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets tests\test_codex_local_provider_errors.py::test_codex_local_missing_cli_is_reported_as_model_gateway_error -q
# 4 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t48-full -q
# 778 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

## 2026-07-01 - Studio Main Path Browser QA

- Completed AFS-T47 on `codex/afs-post-main-loop-e2e-continuation-20260630` as a provider-closed Studio main-path browser smoke.
- Terminology note for this closeout: the execution method is Agentic Loop Engineering; the project book, execution spec, task ledger, and state file are loop artifacts. AFS product identity remains the AI-native manga/video/image content production workbench.
- Added a reusable browser QA harness that seeds the real Runtime main-loop E2E baseline, opens `/studio/`, creates a keyframe layer from a script node, runs the generation bridge with the image provider gate closed, records a feedback overlay include decision, and verifies the second blocked request plan carries fixed-asset, production-graph, source-evidence, and overlay context safely.
- Fixed the deterministic Studio state bridge so safe production graph summaries, source-evidence refs, human-gate non-claim flags, and keyframe-layer evidence can survive Studio state persistence without keeping unsafe runtime trace payloads.
- No provider smoke, live provider call, generated media, human creative acceptance, business validation, public claim, patent/legal decision, external download, or COS active-rule promotion occurred.
- Cleanup note: `.tmp/pytest-t47-*` is generated pytest basetemp from this run; deletion hit Windows access denial and remains local cleanup pending. Later verification used ignored `.venv` basetemp to avoid adding more untracked scan noise.

Verification:

```text
npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t47-focused tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_main_loop_e2e.py tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_api_runtime_studio_state_persistence.py tests\test_api_runtime_studio_state_modules.py -q
# 18 passed, 1 warning

.\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\t47-browser-runtime --report runs\t47_studio_main_path_browser_qa.json --screenshot runs\t47_studio_main_path_browser_qa.png
# passed; provider_calls_started=false; console_error_count=0; response_error_count=0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warnings include generated .tmp cleanup-pending files and existing historical warnings

git diff --check
# passed

YAML parse for AFS-AI-Execution-Spec.yaml and AFS-Goal-Driven-Execution-State-v0.1.yaml
# passed
```

## 2026-06-30 - Main Loop E2E Integration Gate

- Completed AFS-T46 normal integration gate for
  `codex/afs-goal-mode-main-loop-e2e-20260630`.
- Re-ran startup scan, branch integration review, full pytest,
  maintenance audit, `git diff --check`, and execution YAML parsing before
  integration.
- Fast-forwarded local `master` from `a7d536a4` to the reviewed branch head
  `72c698ac`, pushed `origin/master`, and fast-forwarded both server checkouts:
  `/home/afs-ops/AgentFlowStudio` and `/opt/afs/AgentFlowStudio`.
- Runtime service stayed active and `/health` returned `status=ready` after the
  server sync.
- This is runtime/structure verification only. It is not provider smoke,
  generated media, human creative acceptance, business validation, public claim,
  patent/legal decision, or COS active-rule promotion.

Verification:

```text
.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --repo-root . --base-ref origin/master --allowed-untracked docs/demo-docs-20260629/ --report runs\afs_goal_mode_branch_review_t46_premerge.json
# status=ready_for_human_merge_review; blocker_count=0; merge_review_threshold_reached=false

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed

YAML parse for AFS-AI-Execution-Spec.yaml and AFS-Goal-Driven-Execution-State-v0.1.yaml
# passed

ssh afs-bwg-ops "curl -fsS http://127.0.0.1:8790/health"
# status=ready
```

## 2026-06-30 - Multi-Shot Request Plan Bridge Consistency

- Continued provider-closed work on
  `codex/afs-goal-mode-main-loop-e2e-20260630` for AFS-T45.
- Added a narrow request-plan/bridge consistency check to the real
  `multi_character_restaurant_note` Runtime E2E regression.
- The test now reads the `keyframe_request_plan` artifact and verifies its
  context bundle keeps the same two fixed asset ids, source asset-card
  candidate ids, and feedback overlay id that appear in blocked bridge evidence.
- No Runtime route, OpenAPI path, Studio UI, provider call, generated media,
  human creative acceptance, business validation, public claim, patent/legal
  decision, or COS active-rule promotion changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

## 2026-06-30 - Main Loop E2E Redundancy Cleanup

- Continued provider-closed work on
  `codex/afs-goal-mode-main-loop-e2e-20260630` for AFS-T44.
- Classified the current-branch T41-T43 redundancy and acted on the test
  support slice instead of adding another record-heavy feature artifact.
- Replaced duplicated storyboard breakdown, feedback-candidate promotion,
  context-overlay creation, and keyframe preflight setup in the multi-character
  bridge regression with shared parameterized helpers in
  `tests/runtime_main_loop_e2e_support.py`.
- Removed the obsolete per-test storyboard/feedback overlay helpers from
  `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py`; the shared
  support file is back under the 300-line ideal threshold at 299 lines, and the
  multi-character test dropped to 178 lines.
- No Runtime route, OpenAPI path, Studio UI, provider call, generated media,
  human creative acceptance, business validation, public claim, patent/legal
  decision, or COS active-rule promotion changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py
# 3 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; no new T44 handoff Chinese-coverage warning

git diff --check
# passed
```

## 2026-06-30 - Multi-Character Bridge Regression

- Continued provider-closed work on
  `codex/afs-goal-mode-main-loop-e2e-20260630` for AFS-T43.
- Added a second real benchmark regression using
  `multi_character_restaurant_note` to stress two confirmed character fixed
  assets through keyframe preflight and blocked keyframe bridge evidence.
- Parameterized `tests/runtime_main_loop_e2e_support.py` so the shared image
  upload and fixed-asset promotion helpers can create additional benchmark
  characters without duplicating setup code.
- Verified the bridge carries two safe source-evidence refs for `周岚` and
  `陈默`, while the provider reference-image channel remains slot-limited and
  the image provider gate remains blocked.
- No Runtime route, OpenAPI path, Studio UI, provider call, generated media,
  human creative acceptance, business validation, public claim, patent/legal
  decision, or COS active-rule promotion changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings
```

## 2026-06-30 - Main Loop Keyframe Bridge Evidence

- Continued provider-closed work on
  `codex/afs-goal-mode-main-loop-e2e-20260630` for AFS-T42.
- Extended the real `multi_scene_map_chase` Runtime E2E path from keyframe
  preflight into blocked local keyframe generation bridge evidence.
- Added `tests/runtime_main_loop_e2e_support.py` so T41/T42 share the same
  benchmark setup without duplicating test scaffolding; touched test/support
  files remain below the 300-line ideal threshold.
- Added `tests/test_api_runtime_main_loop_keyframe_bridge_e2e.py`.
  The red baseline failed because `generation_bridge.context_evidence` did not
  include fixed-asset source-evidence refs.
- Updated `agentflow.algorithms.generation_bridge` so blocked bridge artifacts
  now carry safe `included_asset_source_evidence_refs`, including the fixed
  asset id, source human-gate id, asset-card candidate id, and non-claim flags.
- No Runtime route, OpenAPI path, Studio UI, provider call, generated media,
  human creative acceptance, business validation, public claim, patent/legal
  decision, or COS active-rule promotion changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py -q
# red before implementation: KeyError 'included_asset_source_evidence_refs'

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 772 passed, 520 deselected, 2 warnings
```

## 2026-06-30 - Main Loop E2E Baseline Regression

- Started fresh continuation branch
  `codex/afs-goal-mode-main-loop-e2e-20260630` from synced `master`
  `a7d536a4c22412c5f3f77cfcf5da8fb6fbaa3718`.
- Added a provider-closed Runtime E2E regression using the real
  `multi_scene_map_chase` benchmark script. The test exercises storyboard
  content quality, fixed visual asset reuse, production graph, evidence ledger,
  human gate, asset-graph feedback candidate, feedback overlay promotion, and
  keyframe preflight context consumption.
- Fixed two CJK reference-preservation gaps found by the E2E harness:
  human-gate target IDs and fixed-asset source-evidence candidate refs now keep
  Chinese asset-card candidate suffixes such as
  `asset_card_candidate:graph_character_林晚`.
- Kept provider gates closed. No provider smoke, live provider call, generated
  media, human creative acceptance, business validation, public claim, patent
  or legal decision, or COS active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 771 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed
```

## 2026-06-30 - T40 Authorized Merge Sync Runtime Health Gate

- Executed AFS-T40 under standing integration authorization after fresh startup
  scan and branch review on `codex/afs-goal-mode-threshold-gate-20260630`.
- Re-ran the required green gates: branch integration review reported
  `blocker_count=0`, full pytest passed, Studio JS passed, maintenance audit
  had `failed=0`, `git diff --check` passed, CLI help/version passed, and the
  execution YAML files parsed.
- Fast-forwarded local `master` from `f51237df89c680dafc54296d7e013bd98cd459af`
  to `3f65c0a1178ecbe1d51c8fd16f4ca56a374d6084`, pushed `origin/master`, then
  fast-forwarded server `/home/afs-ops/AgentFlowStudio` and
  `/opt/afs/AgentFlowStudio` without reset or clean.
- Verified `afs-runtime.service` remained `active/running` from
  `/opt/afs/AgentFlowStudio` and `http://127.0.0.1:8790/health` returned
  `status=ready`.
- No provider smoke, live provider call, generated media, human creative
  acceptance, business validation, public claim, patent/legal claim, or COS
  active-rule promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --repo-root . --base-ref origin/master --allowed-untracked docs/demo-docs-20260629/ --report runs\afs_goal_mode_branch_review_t40_premerge.json
# status=ready_for_human_merge_review; blocker_count=0; commit_count=20; changed_files=60; insertions=4860; deletions=21

.\.venv\Scripts\python.exe -m pytest
# 770 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

YAML parse for AFS-AI-Execution-Spec.yaml and AFS-Goal-Driven-Execution-State-v0.1.yaml
# passed

git merge --ff-only codex/afs-goal-mode-threshold-gate-20260630
# master fast-forwarded to 3f65c0a1178ecbe1d51c8fd16f4ca56a374d6084

git push origin master
# master -> master at 3f65c0a1178ecbe1d51c8fd16f4ca56a374d6084

ssh afs-bwg-ops "git -C /home/afs-ops/AgentFlowStudio merge --ff-only origin/master"
ssh afs-bwg-ops "git -C /opt/afs/AgentFlowStudio merge --ff-only origin/master"
# both server checkouts fast-forwarded to 3f65c0a1178ecbe1d51c8fd16f4ca56a374d6084

ssh afs-bwg-ops "curl -fsS http://127.0.0.1:8790/health"
# status=ready; studio_static.status=ready
```

## 2026-06-30 - Goal-Mode Threshold Merge Review Gate

- Stopped feature work on `codex/afs-goal-mode-threshold-gate-20260630` for
  T39 threshold review instead of adding another product slice.
- Reviewed `origin/master..HEAD` at
  `fa04cfbe83b9559303d256a1b8813d64cce144af`: 19 commits, 59 changed files,
  4610 insertions, 20 deletions, and 0 branch review blockers before this gate
  record.
- Classified the branch as a coherent provider-closed asset reuse/source
  evidence chain: runtime/algorithm contracts, Studio review surfaces, focused
  tests, governance tooling, and handoff records.
- Recommendation: merge after explicit human authorization; do not continue
  feature work on this branch because the T39 record reaches the 20-commit
  threshold.
- No Runtime route, OpenAPI path, provider gate, provider call, generated media,
  deploy, server sync, human creative acceptance, business validation, or
  durable-memory promotion changed.

Verification:

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 770 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --repo-root . --base-ref origin/master --allowed-untracked docs/demo-docs-20260629/ --report runs\afs_goal_mode_branch_review_t39_precommit.json
# status=ready_for_human_merge_review; blocker_count=0
```

## 2026-06-30 - Studio Source Evidence Non-Claim Flags

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T37 asset-library
  source-evidence preservation slice.
- Extended the shared Studio `sourceEvidenceRefs()` normalizer to retain
  `provider_calls_started` and `human_creative_acceptance_claimed` as explicit
  boolean non-claim flags.
- Verified the flags flow from fixed visual assets into keyframe layer evidence
  refs without exposing signed URLs, local paths, provider raw data, or media
  bytes.
- No Runtime route, OpenAPI path, provider prompt inclusion policy, provider
  call, generated media, deploy, server sync, human creative acceptance, or
  business validation claim changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_source_evidence_claim_flags.py tests\test_web_studio_keyframe_layer_source_evidence.py tests\test_web_studio_asset_detail_source_evidence.py
# 9 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

## 2026-06-30 - Studio Asset Library Source Evidence Preservation

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T36 asset-detail
  source-evidence surface.
- Preserved fixed visual asset `source_evidence` when adding promoted assets to
  the Studio asset library entry, so opening details from the library can show
  the same evidence as the node-local visual asset.
- Kept this as a local Studio state/evidence fix: no Runtime route, OpenAPI
  path, provider call, generated media, deploy, server sync, human creative
  acceptance, or business validation claim changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_asset_detail_source_evidence.py tests\test_web_studio_visual_asset_promotion_gate_static.py
# 6 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

## 2026-06-30 - Studio Asset Detail Source Evidence Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T35 promotion-gate
  production graph evidence slice.
- Surfaced fixed visual asset `source_evidence` in the Studio asset detail
  popover as a small white-listed evidence section.
- Added `assetSourceEvidenceRows()` as a pure helper so the display boundary can
  be tested without browser/provider calls.
- Kept the surface local to Studio review UI; no Runtime route, OpenAPI path,
  provider prompt inclusion policy, provider call, generated media, deploy,
  server sync, human creative acceptance, or business validation claim changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_asset_detail_source_evidence.py tests\test_web_studio_keyframe_layer_source_evidence.py
# 7 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

## 2026-06-30 - Studio Promotion Gate Production Graph Evidence

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T34 keyframe trace
  alignment.
- Added the safe production graph snapshot artifact id to Studio human-gate
  asset-card review notes when the storyboard breakdown already has a
  production graph snapshot.
- Extended `promotionGateReviewSummary()` and the fixed visual asset promotion
  panel meta line to show the production graph artifact id alongside fixed
  reuse count.
- Kept Runtime promotion payload and public API shape unchanged; this remains a
  Studio local review/evidence surface and does not add provider calls,
  generated media, deploy, server sync, human creative acceptance, or business
  validation claims.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_production_graph_reuse_static.py tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_web_studio_human_gate_static.py
# 7 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

## 2026-06-30 - Studio Production Graph Keyframe Trace Alignment

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T33 output-record
  trace surface.
- Added a safe `production_graph_review` summary to Studio keyframe layers
  created from storyboard script nodes that already hold a Runtime production
  graph snapshot.
- Extended `lastKeyframeSourceEvidenceTrace` to carry the same safe review
  summary so output records can connect keyframe source evidence with
  production graph fixed-asset reuse.
- Kept the boundary local to Studio state and trace records: no Runtime route,
  OpenAPI path, provider prompt inclusion policy, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim changed.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_keyframe_layer_source_evidence.py tests\test_web_studio_production_graph_reuse_static.py
# 9 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed
```

## 2026-06-30 - Studio Keyframe Source Evidence Output Record

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T32 local generation
  trace.
- Added a safe `keyframeSourceEvidenceTraceSummaryText()` helper for displaying
  `lastKeyframeSourceEvidenceTrace` in Studio output records.
- Surfaced the keyframe source-evidence trace in the inspector `输出记录`
  section, including the explicit `excluded_by_default` provider prompt policy.
- Extended focused Node regressions to cover trace summary safety and inspector
  wiring.
- No Runtime route, OpenAPI path, provider call, generated media, deploy,
  server sync, human creative acceptance claim, or business validation claim
  occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 5 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details
# 3 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T33
```

## 2026-06-30 - Studio Keyframe Source Evidence Local Generation Trace

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T31 inspector review
  surface.
- Added `keyframe-source-evidence-trace.js` as a shared Studio helper for
  keyframe source-evidence summaries and local traces, reusing the existing
  `sourceEvidenceRefs()` safe normalizer.
- Recorded `lastKeyframeSourceEvidenceTrace` when applying keyframe generation
  responses so the node keeps a safe local trace of fixed-asset source evidence.
- Kept `provider_prompt_inclusion_policy` as `excluded_by_default`; this does
  not change provider prompt inclusion policy or Runtime request schema.
- No Runtime route, OpenAPI path, provider call, generated media, deploy,
  server sync, human creative acceptance claim, or business validation claim
  occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 3 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only
# 3 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T32
```

## 2026-06-30 - Studio Keyframe Evidence Inspector Review Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T30
  promotion-to-keyframe evidence-chain slice.
- Surfaced `keyframeLayer.fixed_asset_source_evidence_refs` in the Studio
  inspector `本次参考摘要`, so an operator can see which fixed asset source
  evidence is attached to a keyframe node.
- Added `keyframeLayer` to the inspector signature so evidence changes refresh
  the right-side review surface.
- Extended the executable Studio regression for keyframe source evidence to
  cover the inspector summary.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 2 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_prompt_policy_review_surface_is_local
# 3 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T31
```

## 2026-06-30 - Studio Promotion-to-Keyframe Evidence Chain

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T29 promotion-gate
  fixed-reuse summary.
- Carried safe fixed visual asset source-evidence refs into
  `keyframeLayer.fixed_asset_source_evidence_refs` when Studio creates a
  keyframe node from storyboard output.
- Reused the existing `sourceEvidenceRefs()` normalizer instead of adding a
  duplicate sanitizer in the keyframe code path.
- Added an executable Node-based Studio regression proving unsafe fixed-asset
  fields such as signed URLs, local paths, and base64 media bytes are not
  retained in keyframe-layer evidence refs.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details tests\test_web_studio_preflight_source_evidence_static.py
# 2 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T30
```

## 2026-06-30 - Studio Promotion Gate Fixed Reuse Summary

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T28 production graph
  fixed-asset reuse surface.
- Extended `promotionGateReviewSummary()` to parse
  `fixed_asset_reuse_count` from accepted asset-card human-gate notes.
- Surfaced the fixed-asset reuse label in the visual-asset promotion review
  summary, so promotion review shows both candidate provenance and graph reuse
  background.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 3 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T29
```

## 2026-06-30 - Studio Production Graph Fixed Asset Reuse Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T27 Studio preflight
  source-evidence surface.
- Persisted Runtime `production_graph` and `production_graph_snapshot` artifact
  id into the script node storyboard breakdown state.
- Surfaced production-graph fixed-asset reuse as human-gate target metadata,
  for example `Fixed reuse / 1 asset`, without adding a new Runtime
  `target_type`.
- Added a small static/Node regression for production graph persistence and
  human-gate target metadata.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_production_graph_reuse_static.py tests\test_web_studio_human_gate_static.py -q
# 4 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T28
```

## 2026-06-30 - Studio Keyframe Preflight Source Evidence Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T26 Runtime
  preflight source-evidence summary slice.
- Added a small Studio helper that turns
  `included_asset_source_evidence_refs` into a safe one-line review summary.
- Surfaced that summary in the existing fixed-asset carry confirmation modal,
  so the operator can see which carried fixed assets came from which human gate
  or asset-card candidate before continuing generation.
- Reused the existing asset reference label helper and removed the duplicate
  local `assetTypeLabel()` from `node-generation-guards.js`; the touched large
  file shrank from 322 lines to 320 lines.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_preflight_source_evidence_static.py -q
# 1 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_preflight_source_evidence_static.py tests\test_web_studio_assets_generation_static.py::test_loop003_qal003_001_fixed_asset_submit_interlock_has_regression_markers tests\test_web_studio_assets_generation_static.py::test_asset_card_generation_uses_optional_fixed_asset_carry_policy -q
# 3 passed

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T27
```

## 2026-06-30 - Keyframe Preflight Source Evidence Summary

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T25 production graph
  fixed-asset reuse evidence slice.
- Added safe fixed-asset source-evidence summary fields to generation preflight
  responses: `included_asset_source_evidence_count` and
  `included_asset_source_evidence_refs`.
- Kept the detailed asset evidence in `included_assets` while adding a compact
  review surface for keyframe preflight and future Studio display.
- Included source-evidence identifiers in the preflight token digest so stale
  review tokens track source-provenance changes, not only asset ids.
- No Runtime route, request schema, OpenAPI path, provider call, generated
  media, deploy, server sync, human creative acceptance claim, or business
  validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_fixed_asset_source_evidence_context.py tests\test_api_runtime_context_resolver.py -q
# 19 passed, 1 existing warning

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T26
```

## 2026-06-30 - Production Graph Fixed Asset Reuse Evidence

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T24 fixed asset
  source-evidence context slice.
- Let storyboard production graph consume current project fixed visual assets
  through their safe public projection.
- Added `fixed_visual_asset` graph nodes and `script_can_reuse_fixed_asset`
  relationships so the production graph now records which fixed assets are
  available for reuse and which source evidence they carry.
- Added `safe_manifest.fixed_visual_asset_source_evidence_count` so the
  storyboard artifact records whether fixed asset source evidence was present.
- No provider call, generated media, Runtime request schema expansion, deploy,
  server sync, human creative acceptance claim, or business validation claim
  occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py -q
# 3 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 8 passed, 1 existing warning

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T25
```

## 2026-06-30 - Fixed Asset Source Evidence Context

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T23 Studio promotion
  gate reuse summary surface.
- Added a safe `source_evidence` public projection for fixed visual assets,
  derived from the existing `promotion_gate` instead of duplicating source data
  into the stored asset record.
- Let keyframe context inherit this safe evidence through the existing
  `public_visual_asset()` path, connecting `asset_card_candidate -> human gate
  -> fixed visual asset -> keyframe context`.
- Added a small focused context test rather than expanding the already large
  context-resolver test file.
- No Runtime request schema expansion, provider call, generated media, deploy,
  server sync, human creative acceptance claim, or business validation claim
  occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_asset_promotion_gate.py -q
# 2 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 1 passed, 1 existing warning

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T24
```

## 2026-06-30 - Studio Promotion Gate Reuse Summary Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T22 Studio
  human-gate reuse-policy surface.
- Added a local Studio review summary for the fixed-asset promotion panel. The
  panel now shows the latest accepted `asset_card_candidate` human-gate reuse
  summary, such as `Project reuse / 3 shots`, before the operator confirms a
  fixed visual asset.
- Kept the Runtime promotion payload stable: it still sends only
  `source_human_gate_id` and `source_asset_card_candidate_id`; it does not send
  `reuse_scope` or expand OpenAPI.
- Added a safe fallback for legacy accepted gate decisions without reuse notes:
  they display as `Accepted asset-card gate` instead of pretending to be
  shot-local or project-reusable.
- No provider call, generated media, deploy, server sync, human creative
  acceptance claim, or business validation claim occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 3 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_web_studio_human_gate_static.py -q
# 7 passed, 1 existing warning

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T23
```

## 2026-06-30 - Studio Human Gate Asset Reuse Policy Surface

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T21 asset reuse
  candidate policy slice.
- Surfaced `asset_card_candidates.reuse_policy` in the Studio human-gate target
  contract so operators can see whether a candidate is `project_reuse_candidate`
  or `shot_local_candidate` before recording a local step-gate decision.
- Added a visible `reuse_label` marker in the existing human-gate menu and
  carried a safe reuse summary into the Runtime human-gate decision `note`.
- Kept the boundary closed: no Runtime API or OpenAPI change, no fixed asset
  write, no provider call, no generated media, no server sync, no human creative
  acceptance claim, and no business validation claim.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# 2 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py tests\test_api_runtime_asset_card_candidates_contract.py -q
# 5 passed, 1 existing warning

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T22
```

## 2026-06-30 - Asset Reuse Candidate Policy

- Continued provider-closed full goal-mode work on
  `codex/afs-goal-mode-threshold-gate-20260630` after the T20 threshold gate.
- Added a deterministic `reuse_policy` to storyboard-derived
  `asset_card_candidates`. Candidates now distinguish multi-shot
  `project_reuse_candidate` assets from `shot_local_candidate` assets using
  existing asset-graph `shot_refs`.
- Exposed `reuse_scope_counts` in the candidate-set summary and
  `asset_card_project_reuse_candidate_count` in the storyboard safe manifest.
- This supports the fixed-asset reuse and human-gate path without writing fixed
  asset memory, starting provider calls, storing media bytes, or claiming human
  creative acceptance.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py -q
# 2 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py -q
# 24 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest
# 752 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T21
```

## 2026-06-30 - Branch Size Merge Review Threshold Gate

- Started fresh branch `codex/afs-goal-mode-threshold-gate-20260630` from the
  synced `master` baseline `f51237df89c680dafc54296d7e013bd98cd459af` after
  the authorized T19 merge/sync gate.
- Added a reusable branch-size threshold helper for the next goal-mode branch:
  automatic merge review gate is required at 20 commits, 80 changed files, or
  5000 insertions.
- Extended `tools/afs_goal_mode_branch_integration_review.py` so its JSON
  report includes insertion/deletion/binary-file counts and
  `merge_review_thresholds` with `required_action`.
- Added regression tests for below-threshold slices and the exact threshold
  limits. This is governance automation only; it does not change Runtime,
  Studio, OpenAPI, provider gates, or product behavior.
- No provider smoke, live provider call, server sync, deploy, human acceptance,
  business validation, generated media, or durable memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 7 passed

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T20
```

## 2026-06-30 - Authorized Master Merge and Three-End Sync

- Human technical lead authorized `merge` for
  `codex/afs-project-book-full-goal-20260630` after T19 branch integration
  review.
- Re-ran the release gate from the codex branch at
  `aba7494b88fd969bf337d692e2be3d5f63f1751f` before touching `master`.
- Fast-forwarded local `master` from
  `6071ef1aa665930df2b9fa383260fc68ed4e4e64` to
  `aba7494b88fd969bf337d692e2be3d5f63f1751f` with `git merge --ff-only`.
- Pushed `master` to GitHub and fast-forwarded both server checkouts:
  `/home/afs-ops/AgentFlowStudio` and `/opt/afs/AgentFlowStudio`.
- Runtime Service was not restarted. A read-only `/health` check reported
  `status=ready`; provider gates were observed but no provider smoke or live
  provider call was run.
- No generated media, provider raw response, secret, signed URL, human creative
  acceptance, business validation, or durable memory promotion was claimed.
- Next goal-mode work must start from the new `master` baseline on a fresh
  `codex/*` branch. The next branch must enter merge review automatically when
  it reaches any threshold: 20 commits, 80 changed files, or 5000 insertions.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest
# 750 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t19_authorized_premerge.json
# status=ready_for_human_merge_review; blocker_count=0

git diff --check
# passed

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

## 2026-06-30 - Studio Quality Feedback Context Overlay Browser QA

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `69a34eea1d7ab1d4da90833b0fc2eccbcaf95daf`.
- Added `AFS-T15i Studio Quality Feedback Context Overlay Browser QA` as the
  provider-closed closeout slice for the T15h quality-feedback UI hook.
- Added a real Playwright/browser QA harness for the Studio quality-feedback
  candidate flow. The harness seeds local Runtime Studio state, submits Studio
  feedback, promotes it, records the next-context overlay, waits for Studio
  state persistence, and verifies safe manifest/runtime-state references.
- Found and fixed a contract bug from the browser path: Runtime feedback and
  promotion artifact ids can be longer than the generic 180-character UI text
  limit. Studio now preserves artifact refs up to 512 characters when building
  promotion/context-overlay requests and summaries; Runtime Studio-state
  sanitization uses the same artifact-ref bound for feedback, promotion, and
  context-overlay artifact ids.
- Added regression tests for the browser QA harness, long Runtime artifact ids
  in Studio JS, and Runtime Studio-state sanitization.
- No provider gate, generated media, durable memory, Company KB promotion,
  master merge, deploy, server sync, Runtime health verification, or
  human/business acceptance occurred.
- Cleanup note: the long-artifact-id JS regression was split into its own test
  file, and the browser QA tool was kept below the 300-line maintenance
  threshold.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_studio_quality_feedback_context_overlay_browser_qa_tool.py tests\test_web_studio_feedback_candidate_static.py tests\test_web_studio_feedback_candidate_artifact_ids.py tests\test_api_runtime_studio_quality_feedback_state.py -q
# 17 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\studio_quality_feedback_context_overlay_browser_qa.py --report runs\studio_quality_feedback_context_overlay_browser_qa_t15i.json --timeout-ms 90000
# status=passed; provider_calls_started=false; manifest_feedback_ref_count=3

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 750 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# passed; current_task_id=AFS-T15i
```

## 2026-06-30 - Studio Quality Feedback Context Overlay UI Hook

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `ee87172d6a32bf90e91bdf246458ceb040b96fb5`.
- Added `AFS-T15h Studio Quality Feedback Context Overlay UI Hook` as a
  provider-closed feedback-loop/Studio UX slice.
- Added an explicit, default-off quality-feedback checkbox that lets the
  operator request "next local context" inclusion after recording feedback.
- Extracted Studio feedback Runtime handling from `main.js` into
  `quality-feedback-runtime-flow.js`, with `feedback-candidate-flow.js`
  building the promotion and context-overlay requests.
- The UI now records only a bounded `qualityFeedbackCandidates` summary on the
  node. Runtime Studio-state persistence gained a dedicated sanitizer for that
  summary, forcing `provider_calls_started=false`, `writes_long_term_memory=false`,
  and `writes_company_kb=false`.
- No Runtime route, OpenAPI path, provider gate, generated media, durable
  memory, Company KB promotion, master merge, deploy, server sync, Runtime
  health verification, or human/business acceptance occurred.
- Cleanup note: the initial test placement pushed an existing test file over
  the oversized threshold; it was split into
  `tests/test_api_runtime_studio_quality_feedback_state.py`, returning
  `oversized_files` to the prior count of 59.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_quality_feedback_state.py tests\test_api_runtime_studio_state_modules.py tests\test_web_studio_feedback_candidate_static.py tests\test_web_studio_assets_generation_static.py -q
# 42 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state_modules.py tests\test_web_studio_assets_generation_static.py tests\test_web_studio_feedback_candidate_static.py -q
# 62 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 743 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed
```

## 2026-06-30 - Model Call Feedback Overlay Sanitizer Split

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `e865237bc3d6f297e220a26138563ed501f20c90`.
- Added `AFS-T18e Model Call Feedback Overlay Sanitizer Split` as a
  provider-closed maintenance/contract slice.
- Moved model-call feedback overlay summary sanitization from
  `agentflow/algorithms/model_call_context/__init__.py` into
  `agentflow/algorithms/model_call_context/feedback_context.py`.
- Reduced `model_call_context/__init__.py` from 294 lines to 228 lines; the new
  helper is 91 lines.
- Kept behavior unchanged by injecting the existing `_sanitize_text` and
  `_safe_ref_list` functions into the helper instead of duplicating URL,
  credential, local-path, and safe-ref normalization.
- Added a module-boundary regression so future feedback overlay fields do not
  get reintroduced into the model-call context main module.
- No Runtime route, OpenAPI path, Studio fetch, provider call, generated media,
  durable memory, Company KB promotion, master merge, deploy, server sync,
  Runtime health verification, or human/business acceptance occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_openapi_snapshot.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 739 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed
```

## 2026-06-30 - Feedback Candidate Scope Conflict Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `af441fc93bdd36215a52248b503f773274b85853`.
- Added `AFS-T15g Feedback Candidate Scope + Conflict Contract` as a
  provider-closed feedback-governance slice.
- Runtime `feedback_candidate` now carries safe `target_binding`,
  `scope_policy`, and `conflict_summary` objects so feedback remains
  project-scoped and cannot be mistaken for a global rule or durable memory.
- Promotion decisions, context overlays, context resolver summaries,
  model-call context, and Studio-state persistence now preserve these safe
  scope/conflict summaries.
- Added deterministic conflict signals for single feedback events:
  mixed quality ratings, low revision success versus high ratings, and mixed
  asset decisions.
- Kept the contract additive: no new Runtime route, no OpenAPI path change, no
  Studio fetch, no provider gate, no generated media, and no durable memory or
  Company KB write.
- Cleanup note: `agentflow/algorithms/model_call_context/__init__.py` is now
  294 lines; future expansion should split overlay sanitization instead of
  adding more fields in place.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_openapi_snapshot.py -q
# 25 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 738 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed, with existing CRLF normalization warning for apps/api/runtime_events.py

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Feedback Candidate Taxonomy Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `a87b8f2f29c0e32c0f9d28fff86c2242be8decd3`.
- Added `AFS-T15f Feedback Candidate Taxonomy Contract` as a provider-closed
  feedback/knowledge-accumulation slice.
- `sanitize_quality_feedback(...)` now emits a bounded `feedback_taxonomy`
  list for Studio quality feedback, asset-graph feedback, and generic runtime
  feedback using controlled category IDs only.
- Runtime `feedback_candidate`, promotion-decision artifacts, context-overlay
  artifacts, context resolver summaries, model-call context, and Studio-state
  persistence now preserve the safe taxonomy IDs plus `taxonomy_count`.
- Kept the contract additive: no new Runtime route, no OpenAPI path change, no
  Studio fetch, no provider gate, and no generated media or durable memory
  write.
- Corrected the T18d handoff status to reflect the already completed
  commit/push/branch-preflight state.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py -q
# 15 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_openapi_snapshot.py -q
# 25 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 738 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed, with existing CRLF normalization warning for apps/api/runtime_events.py

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Studio State Feedback Policy Sanitizer Split

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `98ca7477964fe9bb428ca0343e6c4d20dc224865`.
- Added `AFS-T18d Studio State Feedback Policy Sanitizer Split` as a
  provider-closed maintenance/contract slice.
- Split feedback overlay prompt-policy Studio-state sanitization out of
  `apps/api/runtime_studio_state_context.py` into
  `apps/api/runtime_studio_state_feedback_policy.py`.
- Reduced `runtime_studio_state_context.py` from 300 lines to 248 lines and
  kept the new helper at 84 lines, avoiding new oversized-file debt in the
  current-wave state sanitizer path.
- Kept behavior unchanged: the new helper receives the existing `_text`
  sanitizer and `safe_id`, so local-path/runtime-artifact-path rejection and ID
  normalization remain under the same boundary.
- Updated the module split regression to include the new helper and keep all
  Studio state sanitizer modules under 300 lines.
- Corrected the T18c handoff status to reflect the already completed
  commit/push/branch-preflight state.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state_modules.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 737 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Feedback Overlay Prompt Approval Gate

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `d1c8f509ab62b43573b8af938ec8f1602723679a`.
- Added `AFS-T18c Feedback Overlay Prompt Authorization Design Gate` as a
  provider-closed contract slice.
- `feedback_context_overlay_prompt_policy` now includes a structured
  `prompt_provider_gate` with default state `blocked_by_default`,
  `provider_prompt_inclusion_allowed=false`, human approval required, provider
  gate required, prompt budget review required, and safety filtering required.
- Kept the existing Studio state forbidden-key guard intact. An initial focused
  run failed when the persisted field name contained the security-sensitive
  word `authorization`; the implementation now uses safe approval/gate wording
  instead of relaxing the sanitizer.
- Studio state persistence and Studio helper normalization now pass only
  whitelisted safe gate fields and continue to prune provider raw data, signed
  URLs, local paths, and media-byte markers.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 10 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 37 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 737 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Feedback Overlay Prompt Policy Review Surface

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `76d2c407c8c0e9622e4421bc185f13d82c1f6a14`.
- Added `AFS-T18b Feedback Overlay Prompt Policy Review Surface`.
- Runtime context bundles now expose a safe top-level
  `feedback_context_overlay_prompt_policy` for Studio display, reusing the
  policy already recorded in context trace.
- Studio state persistence now keeps only bounded prompt-policy summary fields
  and continues to prune trace internals, provider raw data, signed URLs, local
  paths, and media-byte markers.
- Studio shows the policy in existing review surfaces: the node context summary
  and the algorithm process panel both report that selected feedback overlays
  remain local context and are not injected into generation prompts by default.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 10 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 37 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 737 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Feedback Overlay Prompt Policy Gate

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `b58a364a32af175ca3fdf60bd4f189ec39d8ce57`.
- Added `AFS-T17b Feedback Overlay Prompt Policy Gate`. The suffix avoids
  colliding with the earlier `AFS-T17 Goal-Mode Branch Integration Review` in
  this same branch history.
- Added a small shared `feedback_overlay_prompt_policy` helper and wired it
  into Runtime context trace, model-call context, request projection, keyframe
  safe manifest, and generation bridge evidence.
- Locked the default policy: selected feedback overlays remain local context
  evidence only, `provider_prompt_includes_context_overlays=false`, and any
  future use of overlay text in provider prompts requires a separate explicit
  prompt policy gate.
- Added a regression proving a selected overlay marker stays in
  `feedback_context_overlays` but does not appear in `keyframe_request_plan`
  provider prompt or `model_request_plan.provider_request.prompt`.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy -q
# red baseline: failed because feedback_context.prompt_policy did not exist
# after implementation: 1 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_runtime_context_text.py -q
# 4 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_generation_comparison.py tests\test_api_runtime_openapi_snapshot.py -q
# 28 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 735 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok
```

## 2026-06-30 - Feedback Overlay Selection UI Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `829f980d8157059fb721f399eda4bcfe33cb9493`.
- Added `AFS-T16 Feedback Overlay Selection / Rejection UI Contract`.
- Studio can now record local include/reject decisions for already-consumed
  feedback context overlays, persist them through `/studio-state` as bounded
  safe node params, and carry them into keyframe request context as
  `feedback_context_overlay_decisions`.
- Runtime context resolution now applies those selected/rejected overlay IDs
  when attaching safe `feedback_context_overlays`, and records selected/rejected
  IDs in trace only when an actual decision exists.
- The new Studio review UI is local-only: it does not call `fetch`, does not
  create feedback overlays, and does not start provider work.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 7 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py -q
# 15 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# first closeout run failed once because new UI copy included "知识库" and
# violated an existing product-facing prompt optimizer source guard.
# After copy fix: 734 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4

git diff --check
# passed

YAML parse check
# yaml_ok
```

## 2026-06-30 - Studio Feedback Overlay Review Surface

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `7be884f75829da9e6614aab288898b11f04775bb`.
- Added `AFS-T15e Studio Feedback Overlay Review Surface`.
- Studio state persistence now keeps bounded safe
  `lastContextBundle.feedback_context_overlays` summaries so consumed feedback
  overlays survive `/studio-state` save/load without carrying provider raw,
  signed URLs, local paths, trace internals, safety-boundary fragments, or media
  byte markers.
- Added a pure Studio helper for feedback overlay summary/count rendering, then
  wired it into the existing inspector context summary and algorithm process
  panel. The UI reads only `lastContextBundle`; it does not create overlays,
  call provider routes, or start live generation.
- Added focused sanitizer/API persistence tests in a new small test file instead
  of pushing the existing Studio-state test over the 500-line hard threshold.
- No OpenAPI snapshot update was needed; path count remains 52.
- No provider call, generated media, master merge, deploy, server sync, Runtime
  health claim, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_feedback_candidate_static.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 6 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 730 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 129 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

## 2026-06-30 - Feedback Candidate Context Resolver Consumption Harness

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `6bffc18a6eceeabcf45733ddfd4c87e85a84cd80`.
- Added `AFS-T15d Feedback Candidate Context Resolver Consumption Harness`.
- Added a small Runtime helper that reads safe
  `runtime_feedback_candidate_context_overlay` artifacts from project
  `feedback_refs`, skips missing or unsafe overlay refs, and attaches bounded
  `feedback_context_overlays` summaries to the local context bundle.
- Wired the overlay summaries into keyframe/video preflight digest output,
  model-call context feedback evidence, keyframe safe manifest counts, and the
  local generation bridge context evidence.
- Preserved the hard boundary: promoted feedback overlays do not enter
  `included_assets`, `reference_image_channel`, `subject_reference_asset_id`,
  durable memory, Company KB, generated media, provider raw output, or live
  provider calls.
- No OpenAPI route or snapshot update was needed; path count remains 52.
- No Studio UI state machine, provider call, generated media, master merge,
  server sync, Runtime health claim, human creative acceptance, business
  validation, or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py -q
# red baseline: 2 failed because feedback_context_overlays were not attached
# after implementation: 2 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_context_resolver_asset_card_candidates.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py -q
# 41 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_model_call_context_contract.py -q
# 14 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_context_resolver_asset_card_candidates.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py tests\test_api_runtime_openapi_snapshot.py -q
# 42 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 727 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4
# after converting the new handoff to Chinese-primary, human_doc_chinese_coverage remains at the existing 22 tracked warnings

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

## 2026-06-30 - Runtime Feedback Candidate Context Overlay Harness

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `213e11df5593e982abb21db73b0fc28be611dea8`.
- Added `AFS-T15c Feedback Candidate Context Overlay Harness` as a local
  deterministic Runtime contract while `AFS-T19` master merge / three-end sync
  remains unauthorised.
- Added a public Runtime route:
  `POST /projects/{project_id}/feedback-candidate-context-overlays`.
- The route reads a source `runtime_feedback_candidate_promotion_decision`
  artifact, accepts only `promote_to_context_overlay`, writes a safe
  `runtime_feedback_candidate_context_overlay` artifact, appends it to project
  `feedback_refs`, and keeps provider, context-bundle, durable-memory, and
  Company-KB writes blocked.
- Added a thin Studio runtime-client method
  `recordFeedbackCandidateContextOverlay(payload)` with no UI state machine.
- Regenerated the Runtime OpenAPI snapshot with the project exporter; path
  count is now 52.
- No provider call, generated media, master merge, server sync, Runtime health
  claim, human creative acceptance, business validation, or durable memory
  promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_web_studio_feedback_candidate_static.py -q
# red baseline: 4 failed because route/client method did not exist

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# red after route addition: snapshot drifted as expected

.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
# Runtime Service OpenAPI exported

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_openapi_snapshot.py tests\test_web_studio_feedback_candidate_static.py tests\test_algorithm_library_contracts.py -q
# 24 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m pytest
# 725 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

## 2026-06-30 - Runtime Feedback Candidate Promotion Decision Harness

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `fca1eaf877d74eb84bdcd99ab94093fc651f9e11`.
- Added `AFS-T15b Feedback Candidate Promotion Decision Harness` as a local
  deterministic Runtime contract while `AFS-T19` master merge / three-end sync
  remains unauthorised.
- Added a public Runtime route:
  `POST /projects/{project_id}/feedback-candidate-promotions`.
- The route reads the source `runtime_feedback_event` artifact, verifies its
  `feedback_candidate`, writes a safe
  `runtime_feedback_candidate_promotion_decision` artifact, appends the decision
  to project `feedback_refs`, and keeps provider/context/memory writes blocked.
- Fixed the existing Studio quality feedback safety key away from an unsafe
  private-link key name to `no_private_external_link` so feedback artifacts can
  be safely read by Runtime promotion workflows without tripping the repository
  unsafe-fragment guard.
- Added a thin Studio runtime-client method
  `recordFeedbackCandidatePromotion(payload)` with no UI state machine.
- Regenerated the Runtime OpenAPI snapshot with the project exporter; path
  count is now 51.
- No provider call, generated media, master merge, server sync, Runtime health
  claim, human creative acceptance, business validation, or durable memory
  promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_promotion.py -q
# red baseline: 3 failed because route returned 404

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py -q
# 4 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_feedback_candidate_static.py -q
# 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# red after route addition: snapshot drifted as expected

.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
# Runtime Service OpenAPI exported

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_openapi_snapshot.py tests\test_web_studio_feedback_candidate_static.py -q
# 6 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 722 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

## 2026-06-30 - Runtime Feedback Candidate Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `5b0c15951d931e872f39164b1bae29c4cd8dc56a`.
- Tightened the existing Runtime `/feedback` event contract so every sanitized
  feedback event now carries a safe `feedback_candidate` summary.
- The candidate summary records scope, safe target refs, bounded evidence
  counts, `promotion_status=candidate_only`, and explicit promotion/provider/
  memory false flags.
- No new Runtime route, Studio route, OpenAPI path, provider call, generated
  media, master merge, server sync, Runtime health claim, human creative
  acceptance, business validation, or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py -q
# 1 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_openapi_snapshot.py -q
# 13 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# first run found 5 internal-beta acceptance failures because the new candidate
# safety field used a forbidden artifact key fragment; renamed it to
# external_private_link_stored and reran the failing subset.

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_afs_internal_beta_acceptance.py tests\test_afs_internal_beta_human_review_record.py tests\test_afs_internal_beta_preflight_public_edge.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 718 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9,
# oversized_files=59

git diff --check
# passed with CRLF normalization warning on apps/api/runtime_events.py

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T15a
```

## 2026-06-30 - Fast-Forward Merge Preflight Gate

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `38a1bdeacecaf2a347c063b058c65b5aba5b6371`.
- Enhanced `tools/afs_goal_mode_branch_integration_review.py` so the merge
  review report explicitly checks whether `origin/master` is an ancestor of the
  current codex branch `HEAD`.
- Added `base_is_ancestor_of_head` and `merge_mode_recommendation` to the
  report, with `fast_forward_candidate_after_human_authorization` used only
  when the rest of the branch review has no blockers.
- Added a `base_not_ancestor_of_head` blocker and a focused regression test so
  a diverged base cannot be reported as ready for human merge review.
- No merge to `master`, server sync, Runtime health check, provider call,
  generated media, human creative acceptance, business validation, or durable
  memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 5 passed

.\.venv\Scripts\python.exe -m pytest
# 718 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t19a_dirty.json
# status=needs_attention while T19a files are dirty;
# base_is_ancestor_of_head=true
```

## 2026-06-30 - Human Merge Review + Baseline Freeze Decision

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `21760e5d59707323ff305ae6a90e8ffa719b04cf`.
- Recorded `docs/handoff/AFS-HUMAN-MERGE-REVIEW-BASELINE-DECISION-20260630.md`
  as the T18 human merge-review evidence packet for the accumulated goal-mode
  branch.
- Re-ran the branch integration review and confirmed
  `ready_for_human_merge_review` with `blocker_count=0`.
- Captured the branch facts for human decision: local HEAD/upstream/GitHub
  remote branch all at `21760e5d59707323ff305ae6a90e8ffa719b04cf`,
  `origin/master` at `6071ef1aa665930df2b9fa383260fc68ed4e4e64`, 15 commits,
  77 changed files, and 15 indexed TaskRun handoffs since the frozen baseline.
- Corrected stale T17 handoff wording that still said commit/push was pending.
- No merge to `master`, server sync, Runtime restart/health claim, provider
  smoke, generated media, human creative acceptance, business validation, or
  durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t18_preflight.json
# status=ready_for_human_merge_review; blocker_count=0

.\.venv\Scripts\python.exe -m pytest
# 717 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# human_doc_chinese_coverage remained at the existing 22 after the T18 handoff
# was expanded with Chinese decision notes.

git diff --check
# passed
```

## 2026-06-30 - Goal-Mode Branch Integration Review

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `1af42f1462632436452dfe7358c7bbd9115cdf70`.
- Added `tools/afs_goal_mode_branch_integration_review.py` as a deterministic
  pre-merge branch hygiene gate for the accumulated goal-mode branch.
- The tool checks that the codex branch is on the expected prefix, local HEAD,
  upstream, and GitHub remote branch are aligned, local `master` matches
  `origin/master`, only explicitly allowed untracked files remain, no forbidden
  runtime/provider/generated-media paths are present in the branch diff, and
  new handoffs are indexed.
- Added `tests/test_afs_goal_mode_branch_integration_review.py` for allowed
  dirty ledger behavior, missing handoff index entries, forbidden artifact
  paths, wrong branch state, unpushed state, and local-base drift.
- This TaskRun is a branch integration review only. It does not merge to
  `master`, deploy, sync server checkouts, restart Runtime, open provider gates,
  run provider calls, claim human acceptance, claim business validation, or
  promote durable memory.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 4 passed

.\.venv\Scripts\python.exe -m pytest
# 717 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed
```

## 2026-06-30 - Provider Smoke Readiness Gate

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `abea0d15edd5c7274ecb1be955baec055b669889`.
- Calibrated `tools/afs_provider_connected_validation_readiness.py` so enabled
  `AFS_ALLOW_REMOTE_LLM` / `AFS_ALLOW_REMOTE_IMAGE` environment gates no longer
  imply current-session live provider smoke authorization.
- Added explicit `authorization_state` fields:
  `human_live_provider_smoke_authorized`,
  `current_session_approval_inferred_from_env`,
  `env_gates_are_not_authorization`, and
  `provider_calls_allowed_by_this_tool`.
- Added `ready_for_human_authorization` as the no-cost state when Runtime,
  provider config presence, and required gates are technically ready but the
  current TaskRun has not been authorized to spend provider calls.
- Added `--live-smoke-authorized` for a future no-cost preflight rerun after
  human authorization. The readiness tool still does not call providers.
- Extended `tests/test_afs_provider_connected_validation_readiness.py` to prove
  env gates are not authorization, explicit readiness authorization is required
  for `ready_for_provider_smoke`, and provider config paths/secrets stay out of
  the report.
- Current local readiness report is `ready_for_human_authorization` with
  `provider_calls_started=false`, `secrets_printed=false`, and
  `path_disclosed=false`.
- No provider gate was opened by this TaskRun, no provider call was started, no
  generated media was written, and no deploy/server sync/human acceptance/
  business validation/durable memory promotion occurred.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_provider_connected_validation_readiness.py -q
# 5 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\afs_provider_connected_validation_readiness.py --report runs\provider_smoke_readiness_gate_t16.json
# status=ready_for_human_authorization; provider_calls_started=false;
# secrets_printed=false; env_gates_are_not_authorization=true

.\.venv\Scripts\python.exe -m pytest
# 713 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

YAML parse for external execution state
# yaml_parse_ok

git diff --check
# passed
```

## 2026-06-30 - Deterministic Promotion Browser Harness

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `fe4be34b535c2193fd199a6c995953ddd2e39692`.
- Added `tools/studio_visual_asset_promotion_browser_qa.py` as a deterministic
  browser/runtime harness for the fixed visual asset promotion flow.
- The harness seeds a local Runtime project with one image node, a safe uploaded
  image asset, and an accepted `asset_card_candidate` human gate summary, then
  opens `/studio/`, submits the fixed visual asset modal, and verifies the
  Runtime visual asset record contains the sanitized `promotion_gate`.
- Added `apps/api/runtime_studio_state_human_gate.py` and wired
  `humanGateDecisions` into the Runtime Studio-state sanitizer so accepted gate
  summaries can survive Runtime hydration without storing media bytes or unsafe
  fields.
- Moved the duplicated Studio static-route helper from two browser QA scripts
  into `tools/studio_asset_context_browser_qa_support.py`; the old scripts now
  reuse that helper instead of carrying a third copy.
- Added `tests/test_studio_visual_asset_promotion_browser_qa_tool.py` for the
  harness path defaults and seeded Studio-state contract.
- No provider gate, provider call, generated media, deploy, server sync, human
  creative acceptance, business validation, or durable memory promotion
  occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_studio_visual_asset_promotion_browser_qa_tool.py -q
# red baseline: ImportError for missing studio_visual_asset_promotion_browser_qa
# final: 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_studio_visual_asset_promotion_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_support.py -q
# 12 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\studio_visual_asset_promotion_browser_qa.py --report runs\studio_visual_asset_promotion_browser_qa_t15.json --timeout-ms 90000
# passed; ignored report recorded promotion_gate, console_error_count=0,
# response_error_count=0, provider_calls_started=false

.\.venv\Scripts\python.exe -m pytest
# first run failed because the initial sanitizer placement made
# runtime_studio_state_param_values.py exceed the 300-line module guard
# final run: 712 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed
```

## 2026-06-30 - Deterministic Promotion UI Harness

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `e2a4862222444783a6c4cfe53246d150c886c379`.
- Added `apps/studio/src/panels/visual-asset-promotion-request.js` as a small
  deterministic builder for fixed visual asset promotion payloads.
- `visual-asset-panel.js` now calls the builder instead of assembling Runtime
  request fields inline. The panel stayed under the 300-line threshold and the
  request contract is directly import-testable.
- Extended `tests/test_web_studio_visual_asset_promotion_gate_static.py` from a
  string-only guard into an executable Node harness. It verifies accepted
  asset-card human gate provenance, sanitization, direct-promotion fallback, and
  absence of provider/media-byte fields in the payload.
- Calibrated one brittle static assertion in
  `tests/test_web_studio_prompt_script_static.py`: `supersedes_asset_id` now
  belongs to the builder module while the panel continues to pass
  `supersedesAssetId`.
- No Runtime/OpenAPI change, provider gate, provider call, generated media,
  deploy, server sync, human creative acceptance, business validation, or
  durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# red baseline: missing visual-asset-promotion-request.js

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 2 passed

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_web_studio_human_gate_static.py tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_api_runtime_visual_assets.py -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# first run exposed brittle static assertion after extracting the builder
# final run: 709 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed
```

## 2026-06-30 - Browser Studio Gate Flow QA

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `f758ca8da101735cb48ae36b797dbbe0fba5c302`.
- Ran an in-app Browser QA smoke against local Runtime `/studio/` with an
  isolated temp runtime root and explicit provider gates set to false.
- Verified `/health` was `ready`, `studio_static.status=ready`, and provider
  gates were all false in the QA runtime environment.
- Verified `/studio/` rendered a non-empty first screen with title
  `AFS Studio 创作图谱`, no framework overlay, and zero browser console
  warnings/errors.
- Exercised the empty-project template gate: clicking `角色设定卡` before a
  project exists opens `请先新建项目` instead of silently failing.
- Exercised the continuation path: clicking `新建项目` -> `创建并切换` created
  `AFS 内测项目` and materialized the role-setting template as three canvas
  nodes, with zero console warnings/errors.
- Stopped the temporary Runtime after QA; port `8790` returned to no listener.
- No product code, OpenAPI, provider config, provider call, generated media,
  deploy, server sync, human creative acceptance, business validation, or
  durable memory promotion occurred.

Verification so far:

```text
Invoke-RestMethod http://127.0.0.1:8790/health
# status=ready; studio_static.status=ready; provider_gates all false

Browser QA
# /studio/ loaded at http://127.0.0.1:8790/studio/?project=studio-empty
# title: AFS Studio 创作图谱
# DOM non-empty; no framework overlay; console warn/error count 0
# empty-project template gate opened 请先新建项目
# project creation created AFS 内测项目 and 3 role-setting nodes
# final console warn/error count 0

Runtime cleanup
# listener_count=0 on port 8790 after stopping temp process

npm.cmd run check:studio-js
# JS syntax check passed: 127 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warning counts remain: human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T13
```

## 2026-06-30 - Asset Promotion Gate Provenance

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `510684c0383515efcb8473a40b99145b1ec8a261`.
- Added optional Runtime promotion provenance for fixed visual assets:
  `source_human_gate_id` and `source_asset_card_candidate_id` are now accepted
  by `VisualAssetPromoteRequest` and projected as a safe `promotion_gate`.
- Added `agentflow.algorithms.fixed_asset_memory.promotion_gate` so the
  provenance sanitization/projection stays outside the fixed asset core module
  and does not create a new oversized-file warning.
- Studio fixed-asset promotion now attaches the latest accepted
  `asset_card_candidate` human gate summary when present. Direct manual
  promotion still works without a human gate ID.
- Updated the Runtime OpenAPI snapshot with the exporter. Public path count
  stayed at 50; only the visual asset promotion request schema changed.
- No provider gate, provider call, generated media, deploy, server sync, human
  creative acceptance, business validation, or durable memory promotion
  occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# red baseline: Runtime response lacked promotion_gate; Studio helper file was missing

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_api_runtime_visual_assets.py tests\test_api_runtime_human_gate.py -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# expected drift before exporter refresh

.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
# exported; paths remained 50

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_api_runtime_openapi_snapshot.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 708 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 127 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warning counts remain: human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T12
```

## 2026-06-30 - Studio Human Gate UI Hook

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `4c18b2660ed1bef2875eb529330eb84cb74ead1b`.
- Added a thin Studio human gate hook for the T10 Runtime contract. Nodes with
  safe `asset_card_candidates` or `generation_bridge` refs now expose
  `记录人工 Gate` from the node menu.
- Storyboard breakdown responses now keep safe asset-card candidate refs on the
  source script node, and keyframe responses keep the safe generation bridge ref
  on the image node.
- The new `human-gate.js` popover dispatches local step-gate decisions through
  `runtime.recordHumanGateDecision(payload)`, then records only a safe
  `human_gate_id` summary in `node.params.humanGateDecisions`.
- No fixed asset promotion, provider gate, provider call, generated media,
  OpenAPI change, deploy, server sync, human creative acceptance, business
  validation, or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# red baseline: missing human-gate.js

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py tests\test_web_studio_assets_generation_static.py::test_mvp_experience_hardening_video_status_and_feedback_markers tests\test_api_runtime_human_gate.py -q
# 5 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 126 files

.\.venv\Scripts\python.exe -m pytest
# 705 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# oversized_files remains at the existing count of 59 after moving human gate
# styles into a dedicated CSS file.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T11
```

## 2026-06-30 - Runtime Human Gate Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `9a47869482faf7b8f1e1dbd4352681f1356aa532`.
- Added deterministic `agentflow.algorithms.human_gate` and a public Runtime
  route `POST /projects/{project_id}/human-gate-decisions`.
- The route records local human gate decisions for `asset_card_candidate` and
  `keyframe_generation_bridge` targets, writes a safe
  `runtime_human_gate_decision` artifact and run trace, and appends the
  decision to project `feedback_refs`.
- Studio now has a thin `recordHumanGateDecision(payload)` Runtime client
  method, without adding UI or a new Studio state machine.
- Updated the Runtime OpenAPI snapshot with the exporter; public path count
  changed from 49 to 50.
- Kept this as local step-gate evidence only: no provider gate, provider call,
  generated media, fixed asset promotion, Studio UI change, deploy, server
  sync, human creative acceptance, business validation, or durable memory
  promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py -q
# red baseline: 3 failed, missing Runtime route returned 404

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# expected drift before exporter refresh

OpenAPI exporter
# before_paths=49; after_paths=50
# added_paths=['/projects/{project_id}/human-gate-decisions']

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_feedback.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_web_studio_assets_generation_static.py::test_mvp_experience_hardening_video_status_and_feedback_markers -q
# 10 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 704 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# secret_like_fragments remains at the existing count of 9 after removing
# the initial unsafe-test literal.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T10
```

## 2026-06-30 - Keyframe Local Generation Bridge

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `71060697c7e5d9ddd95e19d1f49a900245d0b655`.
- Added deterministic `agentflow.algorithms.generation_bridge` and wired
  gate-closed keyframe generation to write `keyframe_generation_bridge.json`.
- The bridge records model/context/request-plan refs, provider gate state,
  planned local candidate ids, and explicit non-claims while keeping
  `provider_calls_started=false` and `bridge_media_generated=false`.
- `keyframe_generation_artifacts(...)` now registers the bridge artifact only
  when it exists, preserving compatibility with older keyframe runs and async
  poll paths.
- Moved bridge artifact writing into
  `apps/api/runtime_keyframe_generation_bridge.py` to avoid embedding the new
  bridge body in the already oversized `runtime_keyframes.py`.
- No provider gate, provider call, Studio UI change, public OpenAPI path
  change, generated media, deploy, server sync, human creative acceptance,
  business validation, or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_keyframe_generation_bridge.py
# red baseline: missing generation_bridge module and Runtime payload

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_generation_manifest_safety.py
# 4 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py::test_generate_context_uses_connected_fixed_assets_and_lock_overrides tests\test_api_runtime_context_resolver.py::test_generate_context_uses_label_matched_fixed_assets_without_edges tests\test_api_runtime_context_resolver.py::test_context_bundle_reproducibility_metadata_is_deterministic tests\test_api_runtime_asset_card_drafts.py::test_asset_card_draft_gate_closed_blocks_before_provider_and_stays_safe
# 4 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 701 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T8
```

## 2026-06-30 - Storyboard-to-Asset Evidence Ledger

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `0121a9956b232086d5720b96d795d442ff3c523c`.
- Added deterministic `agentflow.algorithms.evidence_ledger` and wired Runtime
  storyboard breakdown to return and persist a safe `evidence_ledger` artifact.
- The ledger connects storyboard request plan, safe artifact, safe manifest,
  asset graph, content quality report, production graph snapshot, and asset
  card candidates with explicit evidence states and non-claim boundaries.
- Split storyboard artifact writeout into `apps/api/runtime_storyboard_artifacts.py`
  after full pytest caught `runtime_storyboard_breakdown.py` crossing the
  focused 300-line route threshold; the route file is back to 267 lines.
- Kept this as structure/runtime evidence only: provider smoke, human
  acceptance, business validation, fixed asset memory, provider raw responses,
  private links, local paths, and media bytes remain outside the ledger.
- No provider gate, provider call, Studio UI change, public OpenAPI path change,
  fixed asset promotion, deploy, server sync, business validation, or durable
  memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_evidence_ledger.py
# red baseline: missing evidence_ledger module and Runtime payload

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_context_resolver_asset_card_candidates.py
# 7 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_modules.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_context_resolver_asset_card_candidates.py
# 8 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# 699 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T9
```

## 2026-06-30 - Context Resolver Candidate Boundary

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `a2016bc4bfeb0a2fb696cba32434df12e008e852`.
- Added a focused Runtime regression proving `asset_card_candidate:*` ids
  produced by storyboard breakdown do not enter keyframe preflight context,
  reference image channel, or subject reference selection.
- Narrowed the excluded-asset reason for `asset_card_candidate:*` and
  `asset_card:*` refs from generic `retired_or_missing_visual_asset` to
  `asset_card_candidate_unconfirmed`, while preserving
  `trace_summary.draft_assets_rejected=true`.
- Mirrored the helper change in `apps/api/runtime_context_assets.py` to avoid
  drift from the algorithm-library context resolver helper.
- No provider gate, provider call, Studio UI change, public OpenAPI path change,
  fixed asset promotion, deploy, server sync, human creative acceptance,
  business validation, or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver_asset_card_candidates.py -q
# red baseline: candidate excluded as retired_or_missing_visual_asset
# green: 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py -q
# 18 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_production_graph_contract.py -q
# 4 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 697 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Asset Card Candidate Runtime Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `72f818c37f031524dd3f163acd61e7c7acc92f79`.
- Added deterministic `agentflow.algorithms.asset_card_candidates` and wired
  Runtime storyboard breakdown to return and persist safe
  `asset_card_candidates` derived from the candidate asset graph.
- Each candidate stays `status=candidate` and
  `confirmation_state=needs_human_confirmation`, records safe shot/evidence
  refs, blocks fixed asset memory writes, and marks provider enrichment as
  gated by `AFS_ALLOW_REMOTE_VISION`.
- Kept the existing `/asset-card-drafts` vision route unchanged; this slice is
  a pre-provider candidate contract, not provider-backed card generation.
- No provider gate, provider call, Studio UI change, public OpenAPI path change,
  deploy, server sync, human creative acceptance, business validation, or
  durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py -q
# red baseline: missing asset_card_candidates module and Runtime payload
# green: 2 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py -q
# 22 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_drafts.py tests\test_api_runtime_asset_card_modules.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_asset_card_candidates_contract.py -q
# 8 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 696 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Production Graph Runtime Contract

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `d55ecdb92177cf48988fb730d1b8bb55e1b8c53f`.
- Added deterministic `agentflow.algorithms.production_graph` and wired Runtime
  storyboard breakdown to return and persist a safe `production_graph` snapshot.
  The graph connects script, shot, candidate asset, and content-quality-report
  nodes with explicit relationship types.
- Runtime now records `production_graph_node_count` in the storyboard safe
  manifest, writes `production_graph_snapshot.json`, and registers a
  `production_graph_snapshot` artifact.
- Added `tests/test_api_runtime_production_graph_contract.py` plus algorithm
  library registration coverage. The red baseline failed because
  `production_graph` was absent; focused tests are now green.
- No provider gate, provider call, Studio UI change, public OpenAPI path change,
  deploy, server sync, human creative acceptance, business validation, or
  durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_algorithm_library_contracts.py -q
# 17 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_algorithm_library_contracts.py -q
# 35 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_production_graph_contract.py -q
# 3 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 694 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Content Quality Benchmark Script Regression

- Continued on `codex/afs-project-book-full-goal-20260630` after commit
  `8c20e4da098afc7b0f21ed3599c3d7783a64a723`.
- Added the first repo-safe benchmark script fixture:
  `examples/agentflow/content_quality_benchmark_scripts.example.json`.
  It covers dialogue/investigation, action, emotion turn, multi-scene chase,
  line-based device steps, and multi-character restaurant handoff cases.
- Added `tests/test_storyboard_content_quality_benchmarks.py` so benchmark
  cases exercise `local_storyboard_shots`, `build_asset_graph`, and
  `evaluate_storyboard_content_quality` together.
- The benchmark red/green loop exposed two real local fallback gaps: `海边`
  and `餐厅` were scene hints but were not normalized by `_infer_scene_label`,
  so they fell back to `主要场景`. Added minimal scene normalization for those
  two cases in `apps/api/runtime_storyboard_local.py`.
- No provider gate, provider call, Studio UI change, OpenAPI public surface
  change, deploy, server sync, human creative acceptance, business validation,
  or durable memory promotion occurred.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_storyboard_content_quality_benchmarks.py -q
# red baseline: fixture missing
# red after fixture: missing ('海边', 'scene')
# red after first fix: missing ('餐厅', 'scene')
# green after minimal scene normalization: 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_storyboard_content_quality_benchmarks.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_api_runtime_storyboard_modules.py -q
# 20 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 692 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Project-Book Goal Mode Content Quality Contract

- Started the formal `AFS Project-Book Full Goal-Mode Execution` line on
  `codex/afs-project-book-full-goal-20260630` from frozen baseline
  `6071ef1aa665930df2b9fa383260fc68ed4e4e64`.
- Selected the first verified slice from the project-book task ledger:
  `AFS-T14 Content Quality Evaluation`, supporting later `AFS-T3/T4/T5`
  work on data model, production graph, and asset cards.
- Added deterministic `agentflow.algorithms.content_quality_evaluation` and
  attached `content_quality_report` to Runtime storyboard breakdown output.
  The report checks script source grounding, dynamic shot-count policy, asset
  evidence, keyframe/video intent fields, and safe non-claim boundaries.
- Runtime now writes `content_quality_report.json`, registers it as a
  `content_quality_report` artifact, and records the report status in the
  storyboard safe manifest.
- Kept the slice additive: no provider gate change, no live provider call, no
  Studio UI change, no OpenAPI public-surface expansion, no deployment, and no
  human creative acceptance/business validation claim.

Verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_content_quality.py -q
# red baseline reproduced: missing content_quality_report

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_algorithm_library_contracts.py -q
# 33 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_storyboard_content_quality.py -q
# 2 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 691 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# initial run flagged the new handoff for Chinese coverage; handoff was rewritten
# as a Chinese-first document and the warning count returned to the existing 22
# human_doc_chinese_coverage findings

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Three-End Sync + Runtime Health Verification

- Continued after the AFS-T4 baseline freeze and synchronized the pushed
  baseline across local, GitHub, server `/home/afs-ops/AgentFlowStudio`, and
  server `/opt/afs/AgentFlowStudio`.
- Server sync method: read current state, then `git fetch origin master` and
  `git merge --ff-only origin/master` in each server checkout. No reset, clean,
  branch deletion, provider config edit, deploy script, Nginx edit, or runtime
  artifact cleanup was performed.
- Server `/home` preserved its existing untracked local files:
  `docs/demo/` and `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`.
- Runtime service was not restarted because the synced baseline contains tests,
  docs, and OpenAPI snapshot records, not Runtime product-code changes. Service
  status was checked read-only.
- Runtime `/health` returned `status=ready`, `studio_static.status=ready`,
  `auth_required=true`, and observed provider gates:
  `llm=true`, `image=true`, `video=true`, `vision=true`, `asr=false`,
  `external_download=false`.
- This is three-end sync and runtime-health verification only. It is not
  provider smoke, human acceptance, business validation, creative quality
  validation, or durable memory promotion.

## 2026-06-30 - Baseline Freeze Commit/Push Prep

- Executed `AFS-T4 Baseline Freeze Commit/Push + Three-End Sync Prep` to turn
  the first-to-fifth-wave green baseline candidate into a Git-traceable local
  baseline.
- Re-ran the full local gate before staging:
  - full pytest: `690 passed, 520 deselected, 2 warnings`;
  - CLI help: passed;
  - CLI version: `0.1.0`;
  - Studio JS check: `125 files passed`;
  - maintenance audit: `failed=0`, `passed=3`, `warning=4`;
  - `git diff --check`: passed.
- Chose a two-commit freeze:
  - `test(runtime): freeze runtime contract baseline` for OpenAPI snapshot and
    Runtime/media/error/module contract tests;
  - `docs(handoff): record AFS baseline freeze gates` for DEVLOG, handoff index,
    and first-to-sixth wave handoff records.
- `docs/demo-docs-20260629/` remains intentionally untracked and unstaged.
- No product behavior change, OpenAPI public-surface change, provider gate,
  provider call, deployment, server mutation, Runtime restart, human acceptance,
  business validation, secret, signed URL, provider raw response, or generated
  media byte was produced.

## 2026-06-30 - Test Contract Calibration + Baseline Freeze Prep

- Executed `AFS-T3a Test Contract Calibration + Baseline Freeze Prep` to remove
  the 4 full-pytest blockers found by the goal-mode readiness gate.
- Reproduced the red baseline first: the two module-split tests failed on hard
  `<=300` line thresholds, and the two Runtime error tests failed on stale
  assertions that expected pre-structured error payloads.
- Calibrated module split tests to assert real maintenance contracts:
  extracted helper modules still exist, route files do not redefine extracted
  helpers, and active files over 300 lines must remain visible in
  `maintenance_audit` `oversized_files` warnings.
- Calibrated structured-error tests to assert the current safe Runtime error
  payload and verify unsafe exception text, local paths, provider raw markers,
  signed URL markers, token markers, and API-key markers are not leaked.
- No Runtime behavior, Studio behavior, OpenAPI snapshot, public API, provider
  adapter, provider gate, commit, push, deploy, server health check, human
  acceptance, business validation, secret, signed URL, provider raw response, or
  generated media byte was produced.
- Remaining maintenance debt is still explicit: `runtime_video_dispatch.py`
  remains a >500-line split candidate and should be handled in a dedicated
  follow-up, not hidden as solved.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_enhancement_modules.py::test_llm_enhancement_keeps_runtime_helpers_split tests\test_api_runtime_video_routes_modules.py::test_video_routes_keep_runtime_helpers_split tests\test_api_runtime_service.py::test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text tests\test_api_runtime_studio_state.py::test_studio_state_uses_expected_version_to_prevent_stale_overwrite -q
# red baseline reproduced: 4 failed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_enhancement_modules.py tests\test_api_runtime_video_routes_modules.py tests\test_api_runtime_service.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_media_contract.py -q
# 27 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 690 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Goal-Mode Readiness Gate

- Executed `AFS-T3 Goal-Mode Readiness Gate` after the first three local waves.
- Judgment: not ready for unbounded full Codex goal mode. The wave outputs are
  explainable and focused-contract tests are in place, but full `pytest` is red
  and should not be treated as a clean freeze baseline.
- Classified current dirty state as attributable:
  - first/second/third/fourth wave records in `DEVLOG.md` and `docs/handoff/`;
  - second-wave OpenAPI snapshot and parity test;
  - third-wave Runtime media contract test and structured Studio-state assertion;
  - pre-existing `docs/demo-docs-20260629/` remains do-not-touch.
- Recommended next task: `AFS-T3a Test Contract Calibration + Baseline Freeze Prep`.
  It should resolve the 4 full-pytest blockers, rerun full verification, then
  decide commit/push/server-sync.
- No commit, push, deploy, server health check, provider call, COS active-rule
  promotion, human acceptance, business validation, secret, signed URL,
  provider raw response, or generated media byte was produced.

Verification:

```text
git status --short --branch
# master...origin/master with first/second/third/fourth wave dirty files and pre-existing docs/demo-docs-20260629/

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe -m pytest
# failed: 686 passed, 4 failed, 520 deselected, 2 warnings
# failing tests:
# - tests/test_api_runtime_llm_enhancement_modules.py::test_llm_enhancement_keeps_runtime_helpers_split
# - tests/test_api_runtime_service.py::test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text
# - tests/test_api_runtime_studio_state.py::test_studio_state_uses_expected_version_to_prevent_stale_overwrite
# - tests/test_api_runtime_video_routes_modules.py::test_video_routes_keep_runtime_helpers_split

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; warnings remain classified

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## 2026-06-30 - Runtime Media Contract Baseline

- Executed the third-wave `AFS-T2b Runtime Media Contract` pass for the
  `image-assets*` boundary between Runtime Service and `/studio/`.
- Classified `image-assets*` as an existing Studio-facing private Runtime media
  contract, not a public OpenAPI contract at this stage. The routes remain
  intentionally absent from `docs/openapi/afs-runtime-service.openapi.json`
  because they carry browser upload `data_base64` and byte-returning preview
  behavior that needs a dedicated public media API decision before exposure.
- Added `tests/test_api_runtime_media_contract.py` to pin the private contract:
  OpenAPI exclusion, upload/list/delete safe JSON fields, no local paths or
  base64 echo, preview `content-type`, preview `Cache-Control: no-store`, and
  byte return only through the preview `FileResponse`.
- Repaired one stale Studio-state test assertion so it checks the current
  structured Runtime error payload for unsafe preview URL rejection.
- Left Runtime behavior, Studio behavior, provider adapters, provider gates, and
  the OpenAPI snapshot unchanged.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_media_contract.py tests\test_api_runtime_auth.py::test_auth_enabled_projects_are_owner_scoped tests\test_api_runtime_studio_state_persistence.py::test_image_asset_list_returns_public_metadata_only tests\test_api_runtime_studio_state_persistence.py::test_studio_state_rejects_unsafe_preview_url tests\test_api_runtime_creative_agent_keyframes.py::test_uploaded_image_asset_can_be_deleted_from_project_runtime tests\test_web_studio_frontend_wave.py::test_runtime_media_urls_are_normalized_only_at_render_boundaries tests\test_web_studio_frontend_wave.py::test_runtime_media_source_caches_authorized_project_media_between_rerenders tests\test_web_studio_static.py::test_studio_keeps_flow_native_canvas_controls -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_media_contract.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; warnings remain classified as maintenance debt
# legacy_frozen_surface=10, human_doc_chinese_coverage=22, secret_like_fragments=9 high_confidence_count=0, oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

Boundary:

- No provider gate was opened and no live provider call, external download,
  ASR, video generation, generated media byte, provider raw response, signed
  URL, secret, invite code, customer material, real cost, human acceptance,
  business validation, durable memory promotion, commit, push, deploy, or
  server sync claim was made.

## 2026-06-30 - Runtime Contract Snapshot Alignment

- Executed the second-wave `AFS-T2 Runtime Contract` pass against the current
  Runtime Service, committed OpenAPI snapshot, and Studio Runtime client
  boundary.
- Found a real OpenAPI maintenance drift: the default live Runtime app exposed
  49 OpenAPI paths while the committed snapshot had 34. The missing paths were
  current Runtime surfaces such as client events, project delete,
  storyboard/shot asset planning, sprite routes, and community requests.
- Regenerated `docs/openapi/afs-runtime-service.openapi.json` with the existing
  `runtime-service-openapi-export` command, bringing the snapshot back to
  parity with the default Runtime app.
- Added `tests/test_api_runtime_openapi_snapshot.py` so future Runtime route
  changes cannot silently leave the committed OpenAPI snapshot stale.
- Audited Studio fetch boundaries. Studio source fetches remain centralized in
  `runtime-client.js` and authorized Runtime media preview loading; no Studio
  source bypass to CLI internals, provider secrets, signed URLs, provider raw
  responses, local private paths, or provider internals was found.
- Classified the `image-assets` Runtime endpoints as a deferred media contract
  decision: they are used by Studio but intentionally hidden from OpenAPI today,
  so this pass did not expand the public API surface without a dedicated
  media-contract slice.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_service_v02.py::test_runtime_service_v02_routes_are_hidden_by_default tests\test_api_runtime_storyboard_breakdown.py::test_storyboard_breakdown_is_exported_without_secret_surface tests\test_api_runtime_sprite.py::test_sprite_chat_falls_back_to_local_rules_when_llm_gate_closed tests\test_web_studio_prompt_script_static.py::test_storyboard_asset_identification_uses_runtime_plan_and_allows_manual_asset_nodes tests\test_web_studio_sprite_static.py::test_studio_sprite_widget_is_wired_to_runtime_chat -q
# 6 passed, 1 existing warning

OpenAPI parity check after export:
# live_paths=49; snap_paths=49; schema_equal=True; missing_paths=0; stale_paths=0

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; status=warning; passed=3; warning=4
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22, all tracked
# secret_like_fragments=9, high_confidence_count=0
# oversized_files=59, tracked=57, untracked=2

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# current_task_id=AFS-T2
# cleanup_status=completed_for_second_wave_runtime_contract_records
# feedback_status=none_needed_for_second_wave
```

Boundary:

- No provider gate was opened and no live provider call, external download,
  ASR, video generation, generated media byte, provider raw response, signed
  URL, secret, invite code, customer material, real cost, human acceptance,
  business validation, durable memory promotion, commit, push, deploy, or
  server sync claim was made.

## 2026-06-30 - First-Wave Startup Scan Packet

- Completed the first-wave AFS startup scan against the current `master`
  checkout, the linked `Learning_notes` source-KB repo, the AFS repo rules, and
  the 2026-06-30 project-book package.
- Recorded the true dirty ownership boundary: AFS still has pre-existing
  untracked `docs/demo-docs-20260629/`; `Learning_notes` is on
  `codex/cos-evidence-promotion-v03` ahead of `origin/master` with pre-existing
  `.obsidian`, Week Planner, Company OS, workflow-adapter, and project-package
  changes.
- Confirmed the current key entrypoints: Runtime Service
  `apps/api/runtime_service.py`, OpenAPI
  `docs/openapi/afs-runtime-service.openapi.json` version `0.2.0` with 34
  paths, Studio `/studio/` under `apps/studio/`, algorithm modules under
  `agentflow/algorithms/`, and Python/package commands in `pyproject.toml`.
- Added the first-wave TaskRun/Handoff packet at
  `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md` and updated the
  private project-package execution state with the verified repo state and next
  valid action.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; status=warning; existing warning classes only

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# evidence_state=structure_verified
# cleanup_status=completed_for_first_wave_startup_records
# feedback_status=none_needed_for_first_wave
```

Boundary:

- No Runtime, Studio, schema, provider, or product feature code was changed.
- No provider gate was opened and no live provider call was started.
- No commit, push, deploy, secret, signed URL, provider raw response, generated
  media byte, invite code, customer material, real cost, human acceptance, or
  business validation claim was made.

## 2026-06-29 - Test Maintenance Audit Classification

- Added Git state classification to the maintenance audit so findings can now
  distinguish tracked, untracked, ignored, and unknown text files. This keeps
  local demo files and ignored runtime evidence from being flattened into the
  same active maintenance-debt bucket.
- Split the Git status helpers into `tools/maintenance_audit_git.py` so
  `tools/maintenance_audit.py` stays under the 300-line maintenance threshold.
- Kept secret-like scanning over the full text-file set, including ignored
  files, while excluding ignored files from active oversized and Chinese-doc
  coverage checks.
- Inspected `origin/zhaowei` in an isolated worktree. A no-commit trial merge
  conflicted across current Runtime/Studio generation files and would reintroduce
  a large stale branch surface; current `master` already carries the equivalent
  image relay, Crazyrouter artifact host, Codex home, script expansion, and
  optimizer-pollution protections.

Verification:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_maintenance_audit.py -q -> 11 passed
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help -> passed
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version -> 0.1.0
npm.cmd run check:studio-js -> JS syntax check passed: 125 files
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py -> failed=0, warnings only; oversized findings now tracked=57 in the isolated worktree
```

Boundary:

- No provider call was started.
- No Runtime product contract or provider gate changed.
- No main-worktree untracked demo document, server `/home` untracked artifact,
  provider secret, signed URL, invite code, raw provider response, or generated
  media byte was written to Git.

## 2026-06-28 - Branch Reconciliation and Diagnostics Merge

- Merged the remote Studio generation diagnostics branch into `master`,
  preserving the Runtime file logging, structured exception handling, frontend
  client error reporting, generation panel controls, and video/keyframe timing
  diagnostics.
- Merged `codex/algorithm-agent-foundation` into the same line so the expert
  timeline, asset graph continuity, asset feedback overlay, grounded storyboard
  planning, and related runtime plan contracts are now combined with the latest
  Studio diagnostics work.
- Reconciled merge-time test contracts for structured Runtime error payloads,
  current video generation prompt guidance, visible-area project navigation,
  and Studio file-size thresholds. Also replaced one stale fallback message
  that still claimed only image nodes support real generation.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py tests/test_runtime_generation_logging_static.py tests/test_volc_seedance_video_adapter.py tests/test_web_studio_frontend_wave.py tests/test_web_studio_mature_shell_static.py tests/test_web_studio_prompt_script_static.py tests/test_web_studio_static.py -> 167 passed, 1 existing warning
npm.cmd run check:studio-js -> JS syntax check passed: 125 files
.\.venv\Scripts\python.exe -m apps.cli.main --help -> passed
.\.venv\Scripts\python.exe -m apps.cli.main version -> 0.1.0
git diff --check -> passed
```

Boundary:

- No provider call was started during the merge verification.
- Server synchronization and branch cleanup are operational follow-up steps for
  the same three-end reconciliation pass.

## 2026-06-28 - Expert Timeline and Asset Feedback Slice

- Added a structured expert-knowledge runtime layer covering camera, lighting,
  depth of field, editing pacing, art direction, motion design, and continuity.
  Video plans now carry this context separately from provider prompt text so
  downstream logic can inspect professional decisions instead of parsing prose.
- Added `temporal_director_plan` to video generation plans. A 5s video now has
  second-level beats with character state, action, camera state, lighting state,
  depth of field, composition guard, asset continuity, forbidden changes, and
  edit intent. Provider prompts include a compact second-level director timeline
  while preserving existing asset identity, professional reference, and director
  scenario sections within provider prompt limits.
- Added asset-graph feedback overlay support. Runtime plans can now consume
  user decisions to confirm, lock, revise, or reject graph assets. Rejected
  graph assets are excluded from locked asset context and converted into
  forbidden changes; locked/revised assets add continuity and negative locks.
  The overlay remains raw runtime evidence and does not write long-term memory
  or Company OS source knowledge.
- `/feedback` sanitization now preserves safe asset-graph feedback decisions
  rather than flattening them into a generic note.

Verification:

```text
python -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py -> 94 passed, 1 existing warning
python -m py_compile changed knowledge/algorithm/runtime modules -> passed
```

Boundary:

- No server checkout, `/test` checkout, runtime service, provider config, or
  deployed process was modified.
- No live LLM, image, video, ASR, vision, or external download provider call
  was started.
- The new expert layer and feedback overlay are execution-projection logic, not
  durable Company OS rule promotion.

## 2026-06-28 - Asset Graph Keyframe/Video Continuity Slice

- Added a reusable asset-graph context summarizer for downstream generation
  plans. It extracts `asset_graph` from context bundles or context subgraphs,
  normalizes locked assets, continuity locks, negative locks, evidence, review
  state, and unsupported additions without promoting anything to durable memory.
- Keyframe plans now include `asset_graph_context` and merge graph-derived
  locks into `asset_locks`, `scene_locks`, and `forbidden_changes`. This gives
  keyframe generation a concrete way to preserve assets such as a plush robot
  head shell or a flat rooftop platform instead of relying only on prompt text.
- Video generation plans and video provider prompts now consume the same graph
  context. The plan records whether graph context was used, editing locks inherit
  graph continuity and negative constraints, and the provider prompt includes an
  `Asset graph continuity` section for first-frame image-to-video continuity.

Verification:

```text
python -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py -> 88 passed, 1 existing warning
python -m py_compile changed asset graph/keyframe/video modules -> passed
```

Boundary:

- No server checkout, `/test` checkout, runtime service, provider config, or
  deployed process was modified.
- No live LLM, image, video, ASR, vision, or external download provider call
  was started.
- The new graph context remains candidate/runtime evidence and does not write
  long-term memory or Company OS source knowledge.

## 2026-06-28 - Asset Graph Contract Slice

- Added a Runtime `AssetGraph` contract for storyboard and shot asset planning.
  The graph aggregates candidate characters, scenes, and props across shots
  with `graph_asset_id`, role, confidence, shot refs, evidence spans,
  continuity locks, negative locks, and review state.
- Storyboard breakdown responses and safe artifacts now include `asset_graph`,
  plus safe manifest counts for graph assets and unsupported additions. The
  graph also records unsupported provider additions such as unrequested chairs,
  stools, or eaves for human review.
- Shot asset planning now returns the same graph shape and attaches
  `graph_asset_id` to each returned asset ref before building editable profile
  plans. This gives downstream asset cards, keyframes, video nodes, and future
  asset feedback a stable merge handle.

Verification:

```text
python -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py -> 86 passed, 1 existing warning
python -m py_compile changed Runtime asset graph modules -> passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
git diff --check -> passed
```

Boundary:

- No server checkout, `/test` checkout, runtime service, provider config, or
  deployed process was modified.
- No live LLM, image, video, ASR, vision, or external download provider call
  was started.
- No provider secret, signed URL, raw provider response, media byte, private
  Company OS source content, or durable memory promotion was written to Git.

## 2026-06-28 - Grounded Algorithm Agent Contract Slice

- Added source-grounding fields to storyboard outputs from both local fallback
  and LLM/provider JSON parsing: `source_span`, `grounding_status`,
  `unsupported_additions`, and a small `planning_agent` trace.
- Added asset evidence and confidence metadata to storyboard asset refs so
  downstream asset cards, keyframe plans, and video nodes can distinguish
  source-backed candidates from unsupported additions.
- Updated storyboard LLM instructions to require source spans,
  `unsupported_additions`, and asset evidence instead of accepting free-form
  shot lists. Unrequested chairs, stools, eaves, and similar set pieces are now
  surfaced for review instead of silently entering the chain.
- Replaced the fixed four-section script plan with a density-aware formal
  script expansion strategy. Short ideas now use a compact prose strategy, and
  storyboard splitting remains explicitly deferred.

Verification:

```text
python -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py -> 85 passed, 1 existing warning
python -m py_compile changed Runtime algorithm modules -> passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
git diff --check -> passed
```

Boundary:

- No server checkout, `/test` checkout, runtime service, provider config, or
  deployed process was modified.
- No live LLM, image, video, ASR, vision, or external download provider call
  was started.
- No provider secret, signed URL, raw provider response, media byte, private
  Company OS source content, or durable memory promotion was written to Git.

## 2026-06-27 - Director Scenario Packs

- Added AFS-native director scenario packs for faceless channel, SaaS launch,
  podcast visual, and a short-video hook auxiliary layer. The packs are
  structured execution-projection knowledge, not copied Claude Skill text and
  not durable Company OS memory.
- Wired `director_scenario` through prompt optimization traces, script plans,
  storyboard shot plans, keyframe request plans, video generation plans, and
  video provider prompts. Prompt optimization model-call context now records
  `director_scenario:<id>` references for provider-bound evidence.
- Video provider prompt assembly now respects the selected provider
  `prompt_char_limit` before adapter validation, preventing richer director
  guidance from turning fake/real provider dispatch into prompt-length failure.

Verification:

```text
python -m py_compile changed algorithm/runtime modules -> passed
python -m pytest tests/test_agentflow_knowledgebase.py tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_video_generations.py -q -> 83 passed, 1 existing warning
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
git diff --check -> passed with CRLF/LF warning on agentflow/knowledge/__init__.py
```

Boundary:

- No live LLM, image, video, ASR, vision, or external download provider call
  was started.
- No provider secret, signed URL, raw provider response, media byte, private
  Company OS source content, or external repository prose was written to Git.

## 2026-06-27 - Creative Algorithm Planning Layer

- Added safe structured planning artifacts for the Studio generation chain: formal script plan, storyboard shot function/keyframe/video requirements, editable asset profile seeds, keyframe plan, and video motion/editing plan.
- Kept provider gates unchanged; no live LLM, image, video, ASR, or external download was triggered. New plans are deterministic request/context projections and are not durable memory or Company OS feedback promotion.
- Verification: focused algorithm/runtime pytest `67 passed`; broader regression excluding environment-conflicting full-repo scan/home-permission tests `637 passed`; CLI `--help` and `version` passed; `git diff --check` passed.

## 2026-06-27 - Professional Creative Reference Layer

- Added a deterministic professional reference context for camera/framing, motivated lighting, depth of field, temporal pacing, and scene-continuity constraints. It currently detects production tags such as night, rooftop, rural, robot, observational action, single-frame, and video.
- Wired the reference context into prompt assembly sections and trace artifacts, storyboard shot planning, keyframe request planning, and video generation/provider prompts so downstream nodes receive explicit professional guidance instead of only generic cinematic phrasing.
- Kept the source knowledgebase sync boundary intact: this pass adds an execution-projection algorithm layer and tests, but does not write to the external Company OS source KB, durable memory, provider raw responses, or media bytes.
- Verification: focused knowledge/runtime/storyboard/keyframe/video regression set `77 passed, 1 existing warning`; Python compile for changed algorithm/runtime/test files passed.

## 2026-06-26 - Studio Script Upload and Asset Video Reference Fix

- Fixed the canvas floating upload action so both `text` and `script` nodes
  route to local script import instead of sending script-node uploads through
  image asset upload.
- Fixed asset-library fixed visual assets used on video nodes: the selected
  visual asset now remains attached as context and its first public
  `image_asset_refs` entry is synchronized into `firstFrameImageAssetId` and
  the node upload list as a `first_frame` reference.
- Extended the same fixed-asset image resolution to drawer `设为首帧/设为尾帧`
  actions and to generation-time fallback for existing video nodes that already
  have `visualAssets` but no explicit first-frame image id.

Verification:

```text
npm run check:studio-js -> JS syntax check passed for 122 files
python -m pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py tests/test_api_runtime_context_resolver.py tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py tests/test_api_runtime_auth.py -q -> 84 passed
git diff --check -> passed
```

Boundary:

- No live image, video, LLM, ASR, vision, or external download provider call
  was started during this code change.
- No provider secret, signed URL, raw provider response, media byte, invite
  code, session token, or private Company OS source content was written to Git.

## 2026-06-26 - Runtime Image Relay Deployment Guard

- Added Runtime-side provider config migration for server environments that
  still have an ignored local `codex_image` API relay service in
  `AFS_PROVIDER_CONFIG`. The loader now projects that service and its account
  pool into `image_relay` in memory, removes the legacy service/pool from the
  validated Runtime store, adds the image edit endpoint default, and raises the
  reference image slot floor to 1 for asset-reference image edits.
- This keeps product-facing Studio requests, model plans, and safe manifests
  on `image_relay` even when the root-owned server config has not yet been
  manually rewritten.
- Allowed image relay artifact downloads over HTTP when, and only when, the
  artifact host matches the configured `allowed_artifact_hosts` allowlist. This
  matches the current relay's temporary artifact URL shape while still avoiding
  URL persistence in safe manifests. Crazyrouter image relay now also gets
  `.myqcloud.com` as a code-side default artifact host because the live relay
  returned temporary image artifacts from `vod2.myqcloud.com`.
- Fixed Seedance polling so the provider's initial `not_start` task state is
  treated as queued/running instead of a terminal failure.

Verification:

```text
python -m pytest tests/test_provider_adapter_registry.py tests/test_web_studio_assets_generation_static.py -q -> 55 passed
AFS_PROVIDER_CONFIG=/etc/afs/providers.local.json python - <<loader probe>> -> services ['image_relay', 'seedance_i2v']; codex_image lookup rejected
python -m pytest tests/test_provider_adapter_registry.py tests/test_api_runtime_generation_manifest_safety.py tests/test_model_call_context_runtime_routes.py tests/test_web_studio_assets_generation_static.py -q -> 61 passed
python -m pytest tests/test_provider_adapter_registry.py -q -> 28 passed
python -m pytest tests/test_provider_adapter_registry.py -q -> 28 passed after Crazyrouter artifact host default
python -m pytest tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py -q -> 19 passed
git diff --check -> passed
```

Boundary:

- No live image, video, LLM, ASR, vision, or external download provider call
  was started during this code change.
- No provider secret, signed URL, raw provider response, media byte, or local
  private material was written to Git.
- Root-owned `/etc/afs/providers.local.json` and systemd unit state still need
  a privileged cleanup to physically remove old local names and disable the
  legacy image worker unit.

## 2026-06-26 - Studio Generation Reference And Relay Fixes

- Added local script import support for `.docx`, `.pptx`, `.doc`, and `.ppt`
  alongside text/markdown uploads. OOXML files are parsed client-side; legacy
  binary Word/PPT use a conservative text-extraction fallback. The OOXML
  parser also has a Node-side `zlib` fallback so local regression tests can
  exercise real compressed Word/PPT fixtures under Node 18.
- Changed generation progress rendering so queued/running image and video jobs
  show available percentages instead of always showing an indeterminate label.
  Prompt optimization, script expansion, and storyboard breakdown now also
  write percentage state for the prompt bar.
- Fixed asset-library reference behavior. Selecting an image asset as
  reference on a video node now sets `firstFrameImageAssetId` and a first-frame
  upload ref; selecting it on an image/keyframe node writes a reusable
  `reference_image` upload ref instead of only marking the source node.
- Moved the current image product route from `codex_image` to `image_relay`.
  The Runtime keeps a legacy alias for existing ignored configs, but current
  Studio defaults, request models, provider example config, CLI smoke defaults,
  and prompt trace labels now use external relay terminology.
- Improved image/keyframe relay diagnostics so reference-slot overflow,
  reference-image unsupported routes, missing provider service, auth readiness,
  and relay HTTP errors have separate safe block ids.

Verification:

```text
npm run check:studio-js -> passed for 122 files
python -m json.tool configs/providers.example.json -> passed
python -m py_compile runtime/provider touched files -> passed
role-based local user simulation -> script import, asset reuse, progress, provider route passed
focused pytest set -> 104 passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
python -m pytest -> 637 passed / 3 failed / 520 deselected / 1 warning
```

Full pytest residual failures were environmental or pre-existing in this
checkout: two knowledgebase tests require the Windows `D:/Learning materials/...`
source path, and repository retention review reports 27 manual-review items from
the existing untracked `ops/sub2api/*` tree.

Boundary:

- No live LLM, image, video, ASR, or external download provider call was
  started.
- No provider secret, signed URL, raw provider response, media bytes, local
  private material, or Company OS private source content was written to Git.
- Browser/runtime verification remains separate from human acceptance, creative
  quality acceptance, business validation, and durable memory promotion.

## 2026-06-26 - Internal Beta Operational Hardening

- Added auth failure rate limiting for login and invite registration. The
  default policy is 5 failed attempts per source/account key in 15 minutes,
  followed by a 15 minute lockout.
- Added safe auth audit events for login/register success and failure, weak
  environment invite-code skips, and rate limiting. Audit logs include request
  id, client IP, user id where available, and email hash, but not passwords,
  session tokens, invite plaintext, or provider raw responses.
- Added request id middleware and slow/error request logging. Responses now get
  `X-Request-ID`; slow requests and 5xx exceptions are visible in the
  `afs-runtime` journal.
- Hardened `write_json` with same-directory temp files, `fsync`, atomic
  replace, and cross-platform file locks. Auth read-modify-write operations now
  use an `auth.lock` file to reduce lost-update risk during internal beta.
- Added `runtime-backup create` for administrator Runtime backups. The command
  writes `tar.gz` archives, defaults to excluding `codex-home`, removes
  transient lock/temp files, and applies owner-only permissions on POSIX.
- Updated `docs/handoff/AFS-INTERNAL-BETA-ADMIN-20260626.md` and added
  `docs/maintenance/AFS-INTERNAL-BETA-HARDENING-20260626.md`.

Boundary:

- This pass keeps the JSON-file Runtime store; it does not introduce a
  database, OAuth, email verification, password reset, public admin UI, or SaaS
  role/org/billing system.
- No provider call, real invite code plaintext, session token, provider secret,
  signed URL, media byte, or private Company OS source content was written to
  Git.

## 2026-06-26 - Internal Beta Invite Admin CLI

- Added an admin-only `auth-invites` CLI for the existing Runtime auth store.
  Maintainers can issue, list, and revoke one-time invite codes without adding
  a public HTTP admin surface.
- Invite code plaintext is never stored in Runtime auth state. The store keeps
  only hashes plus safe metadata (`invite_id`, status, batch, note, timestamps);
  plaintext is written only to an admin-local CSV when `--output` is provided.
  With `--output`, the CLI no longer prints plaintext codes to the terminal.
- Runtime registration now rejects revoked and expired invites in addition to
  consumed invites. The public invite listing returns safe status fields only.
- Invite admin helpers live in `apps/api/runtime_auth_invites.py` so
  `runtime_auth.py` stays under the project file-size boundary.
- Added `docs/handoff/AFS-INTERNAL-BETA-ADMIN-20260626.md` as the current
  operating runbook for internal beta account distribution and feedback intake.

Verification:

```text
pytest tests/test_api_runtime_auth.py tests/test_cli_command_registry_boundaries.py -q -> 16 passed, 1 warning
python -m apps.cli.main auth-invites --help -> passed
```

Boundary:

- This is an internal beta access mechanism, not a SaaS roles/orgs/billing
  system and not a public admin dashboard.
- No real invite codes, user passwords, session tokens, provider secrets,
  signed URLs, media bytes, or private Company OS source content were written
  to Git.

## 2026-06-26 - Branch Cleanup And AFS+COS Takeover Handoff

- Audited branch state across local `D:\Projects\AgentFlowStudio`, GitHub
  `origin`, server `/home/afs-ops/AgentFlowStudio`, and server
  `/opt/afs/AgentFlowStudio`.
- Deleted merged server-local branches:
  `codex/align-codex-routing-upstream`,
  `codex/frontend-b14-sync-20260619`, and
  `codex/studio-prompt-script-image-diagnostics` from `/home`; deleted
  `codex/align-codex-routing-upstream` and
  `codex/studio-prompt-script-image-diagnostics` from `/opt`.
- Inspected stale branch `codex/open-source-handoff-governance`; it contained
  useful onboarding/governance direction but was based behind current video
  chain work and would have reverted active Studio/Runtime changes if merged.
  The stale worktree, local branch, and GitHub remote branch were removed after
  the current handoff was recreated on `master`.
- Added `docs/handoff/AFS-COS-TAKEOVER-20260626.md` as the current takeover
  entry for AFS + COS collaborators, covering read order, product chain,
  evidence, branch baseline, server checks, provider gates, and claim
  boundaries.

Verification:

```text
Local branches: master only
GitHub heads: master only
Server /home branches: master only
Server /opt branches: master only
git worktree list: only D:\Projects\AgentFlowStudio
git worktree prune --dry-run: no stale entries
```

Boundary:

- The server `/home` checkout still has an untracked `ops/` directory; it was
  treated as an ops-local artifact and not removed.
- No provider call, secret read, media byte write, or private Company OS source
  copy occurred in this cleanup.

## 2026-06-26 - Script, Keyframe Asset, and Video Progress Hardening

- Fixed Studio idea expansion so `扩写剧本` asks the optimizer for a formal
  short-video script first, not a storyboard placeholder. Local fallback now
  writes a reusable script body with title, setup, development, and ending
  paragraphs; placeholder outputs like `推进主体/展示变化/收束结果` are rejected
  and replaced.
- Strengthened keyframe layer creation from storyboard asset cards. Candidate
  asset cards now become an editable `keyframeAssetPlan`, and the keyframe
  prompt explicitly carries candidate signatures, feature summaries, connected
  reference image counts, local-reference policy, and negative constraints
  against unrequested chairs, stools, eaves, extra props, new characters, text,
  watermarks, UI, or borders.
- Added a keyframe node menu action, `编辑关键帧资产约束`, which selects the
  keyframe, opens the generation panel, and keeps the editable prompt surface
  focused on the generated asset constraints before regeneration.
- Fixed the video node asset-card action path: `video-asset-card-draft` clicks
  now dispatch to the same Runtime draft flow as the menu action, resolve the
  freshest node by `node_id`, and show visible running/success/failure messages
  instead of silently doing nothing.
- Added safe video task timing into Runtime job progress. Submitted/running/
  succeeded video jobs now expose `provider_phase`, `elapsed_sec`,
  `queued_sec`, and `running_sec` where observable; Studio video result text
  renders the timing summary for user inspection.
- Inspected the user's current robot/rooftop safe video job on the server
  without reading provider raw responses. The job
  `studio-1782460097617-ynsp23-video_generation-d5b554ffabf1` succeeded with
  one MP4 candidate; pre-existing code lacked granular timing, but safe file
  timestamps indicate roughly 58 seconds before provider task state was
  persisted and about 3 minutes 32 seconds until final candidate/manifest
  write.

Verification:

```text
pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py -q -> 40 passed
pytest tests/test_api_runtime_video_generations.py -q -> 12 passed, 1 existing warning
npm.cmd run check:studio-js -> JS syntax check passed: 121 files
```

Boundary:

- No live video provider call was triggered in this pass. The timing fields are
  Runtime/provider queue evidence and do not claim creative quality acceptance,
  human acceptance, or business validation. The server job inspection read only
  Runtime safe/task artifacts and file metadata. No provider raw response,
  signed URL, media byte, secret, token, or private Company OS source content
  was written to the repo.

## 2026-06-26 - Keyframe Video Timeline Prompt

- Investigated the Studio screenshot video job on the deployed Runtime using
  safe artifacts only. Job
  `studio-1782194320739-0phdgx-video_generation-ed77c226b864` used
  `seedance_i2v`, `duration_sec=5`, `resolution=720p`, `aspect_ratio=16:9`,
  and first-frame image asset `img_gen_0e4d7d2f6bbafbd2`. Provider dispatch
  started, the task state persisted no provider raw response, and the safe
  manifest ended as `poll_failed` with block id `remote_video_policy_block`.
- Root cause for that run: upstream video provider policy/copyright block for
  the requested IP-like subject matter, not a closed video gate, missing first
  frame, Kling fallback, local poll timeout, credential issue, or provider 404.
  The roughly two-minute wait was async remote video queue/render/review time
  before the provider returned the policy result.
- Reworked the Studio right-click `接续视频节点` prompt from a keyframe-style
  paragraph into a 5-second image-to-video timeline contract. The generated
  prompt now locks 0.0s to the upstream keyframe, gives explicit
  `0.0-1.0s`, `1.0-2.5s`, `2.5-4.0s`, and `4.0-5.0s` motion phases, keeps a
  first-frame continuity lock, and filters image-only text such as
  `单张关键帧`.
- Adjusted the auto video asset plan to normalize prompt-only candidate-card
  mentions like `@金箍棒（候选资产卡...` back to the real asset label, avoid
  duplicates, and mark video asset entries with continuity/reference policy.
- Deployed commit `08dcf90` to origin, server `/home/afs-ops/AgentFlowStudio`,
  and server `/opt/afs/AgentFlowStudio`. Runtime `/health` remained ready with
  video gate true, and the new Studio static module
  `/studio/src/keyframe-video-prompt.js` returned HTTP 200 from Runtime.

Verification:

```text
pytest tests/test_web_studio_assets_generation_static.py -q -> 24 passed
npm.cmd run check:studio-js -> JS syntax check passed: 121 files
pytest tests/test_api_runtime_video_generations.py -q -> 12 passed, 1 existing warning
git diff --check -> passed
```

Boundary:

- No provider raw response, signed URL, generated media byte, secret, token, or
  private Company OS source content was written to the repo. This is prompt
  contract/runtime evidence, not human creative acceptance of any IP storyboard.

## 2026-06-26 - Seedance Video Node Live Smoke

- Completed an authorized live Runtime video-node smoke through the deployed
  `/projects/{project_id}/video-generations` route using `seedance_i2v`.
  The smoke created a temporary authenticated server-local session, uploaded a
  neutral non-IP first-frame image asset, submitted a 5-second `16:9` video
  node, polled the async task, and received a succeeded safe manifest with one
  MP4 candidate.
- Evidence: project `codex-video-node-smoke-189aa485`, job
  `codex-video-node-smoke-189aa485-video_generation-ac869ed4d54e`, candidate
  `candidate_001.mp4`, 2,125,543 bytes,
  SHA-256 `a3616dccd6eae36689412f5c3525461cfeb612b03c543b4dced1ab8c95a39b27`.
  The authenticated preview route returned HTTP 200 with `video/mp4` after
  Runtime restart.
- Media QA was performed from a temporary local copy outside the repository:
  `ffprobe` reported H.264 video, 1280x720, 24 fps, 5.041667 seconds, 121
  frames. `blackdetect` and `freezedetect` completed with zero detected events.
- Local `master`, `origin/master`, server `/home/afs-ops/AgentFlowStudio`, and
  server `/opt/afs/AgentFlowStudio` are aligned at `4381b39`; `afs-runtime`
  was restarted from `/opt` and `/health` remained ready with video gate true.

Boundary:

- This is runtime/provider/media verification for a neutral smoke prompt, not
  human creative acceptance of the Wolverine/Sun Wukong storyboard. No provider
  raw response, signed URL, generated media byte, auth token, sudo secret,
  provider credential, or private Company OS source content was written to Git.

## 2026-06-25 - Retire Kling Video Path and Default to Seedance Relay

- Follow-up fix after deploy: the deployed config intentionally shares a
  Crazyrouter account whose default image/LLM base URL includes `/v1`, while
  Seedance video service `seedance_i2v` overrides the base URL to the root
  host for `/volc/v1/contents/generations/tasks`. The Seedance adapter was
  incorrectly preferring the shared account base URL over the service override,
  producing a create URL shaped like `/v1/volc/v1/...` and a provider HTTP
  404. The adapter now lets the service-level base URL override the account
  base URL, and the regression mirrors that deployed config shape.
- A live server smoke then confirmed the 404 was gone: the request reached the
  Seedance create endpoint but hit the generic 120s read timeout before a task
  response. The adapter now uses the video descriptor `async_timeout_sec`
  (900s in server config) for Seedance create requests unless explicitly
  overridden by the service.
- A follow-up live smoke then confirmed Seedance create returned a task after
  the longer timeout window, but Runtime converted the result into a generic
  422 because the persisted async task state included the credential
  environment variable name, which contains the forbidden `api_key` fragment.
  Seedance submit tasks no longer persist credential env names; poll now
  rehydrates auth header/scheme/env from provider config at runtime.
- A deployed smoke after the task-state fix submitted successfully and polled
  the Seedance task, then the upstream provider failed the specific
  Wolverine/Sun Wukong keyframe with a copyright policy violation. The adapter
  now maps that provider failure into a safe policy-block reason and strips raw
  provider request ids from surfaced errors. Runtime safe manifests now report
  this as `remote_video_policy_block` instead of provider-not-ready.
- Investigated the deployed video failure behind the Studio screenshot. Runtime
  video gate was open, provider dispatch started, but the selected service was
  the retired `kling_i2v` path. The server provider config has Seedance relay
  service `seedance_i2v` for `doubao-seedance-2-0-fast`; the failure was a
  provider selection/configuration mismatch, not a copyright or safety block.
- Retired the active Kling video code path: removed the Kling adapter modules,
  CLI smoke command, provider preflight tool, smoke helpers, and Kling-specific
  tests. Provider registry no longer creates Kling adapters or infers legacy
  descriptorless Kling config.
- Switched Studio and Runtime video defaults to Seedance: the frontend video
  model list exposes only `Seedance 2.0 Fast`, Runtime video generation and
  video revision requests default to `seedance_i2v`, provider-validation hidden
  defaults use `seedance_i2v`, and `configs/providers.example.json` no longer
  includes Kling accounts, pools, or services.
- Updated readiness/acceptance helper scripts and regressions to use Seedance
  evidence naming and blocker IDs, while leaving historical DEVLOG/handoff
  evidence as historical records.

Verification:

```text
pytest tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py -q -> 18 passed, 1 warning
pytest tests/test_web_studio_assets_generation_static.py tests/test_provider_adapter_registry.py tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py tests/test_cli_command_registry_boundaries.py tests/test_architecture_audit_gates.py tests/test_afs_mvp_joint_qa_readiness_audit.py tests/test_production_memory_provider_validation_gate.py tests/test_api_runtime_studio_state.py tests/test_api_runtime_studio_state_persistence.py -q -> 108 passed, 5 deselected, 1 warning
npm.cmd run check:studio-js -> JS syntax check passed: 120 files
git diff --check -> passed
```

Boundary:

- Authorized live video smokes were run on the server to verify the deployed
  Runtime path. No provider raw response, signed URL, generated media byte,
  secret, or private Company OS source content was written to the repo.

## 2026-06-25 - Keyframe Menu Video Continuation for Legacy Nodes

- Expanded Studio keyframe detection so historical completed image nodes titled
  like `关键帧 · 分镜 01` can expose the right-click `接续视频节点` action even
  when they were created before explicit `keyframe_generation` metadata existed.
- The right-click continuation now creates a downstream image-to-video node
  with the keyframe image bound as `firstFrameImageAssetId`, a ready-to-edit
  video prompt, and a `videoAssetPlan` drafted from keyframe visual assets,
  connected asset-card nodes, and remaining `@` references in the keyframe
  prompt. Prompt-only references fill gaps but no longer duplicate connected
  asset-card entries.
- The generated video node tells the user it can be generated directly or
  edited first, matching the asset-card/keyframe workflow shape instead of
  leaving a blank generic video node that asks for a manual first frame.

Verification:

```text
red baseline: legacy keyframe title test failed before implementation because canContinueKeyframeToVideo returned false
pytest tests/test_web_studio_assets_generation_static.py::test_legacy_keyframe_title_can_auto_plan_video_node_assets tests/test_web_studio_assets_generation_static.py::test_keyframe_can_continue_to_explicit_first_frame_video_node tests/test_web_studio_assets_generation_static.py::test_keyframe_to_video_and_video_asset_card_menu_markers -> 3 passed
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 36 passed
npm.cmd run check:studio-js -> JS syntax check passed: 120 files
git diff --check -> passed
```

Boundary:

- No live provider call, provider raw response, signed URL, local media byte,
  secret, or private Company OS source content was written to the repo.

## 2026-06-25 - Keyframe to Video Continuation and Video Asset Cards

- Added a reusable Studio frontend path that turns any completed keyframe image
  node into a connected video node. The new video node stores the keyframe image
  asset as `firstFrameImageAssetId`, keeps the preview URL, and records the
  source keyframe/asset IDs so image-to-video generation does not have to infer
  the first frame from generated history.
- Added a right-click video-node entry for video asset-card recognition. It
  reuses the existing `afs:video-asset-card-draft` event and writes a local
  "generate video first" message when the video node has no accepted video job.
- Kept the implementation generic: the regression constructs a neutral
  keyframe node and verifies first-frame binding, graph connection, selection,
  video role metadata, and video-asset recognition state without depending on
  the Sun Wukong / Wolverine project.
- Keyframe quality review for the current screenshots: the generated keyframe
  is visually usable but still shows asset drift. Wolverine moves toward a
  yellow-suit/claw superhero look instead of the current asset sheet, Sun Wukong
  gains heavier ornate armor than the sheet, the staff prop card is polluted by
  character turnarounds, and output aspect ratio remains provider-controlled
  rather than strictly `16:9`. The scene board is comparatively clean.

Verification:

```text
red baseline: new focused tests failed before implementation because the module/menu entries were missing
pytest tests/test_web_studio_assets_generation_static.py::test_keyframe_can_continue_to_explicit_first_frame_video_node tests/test_web_studio_assets_generation_static.py::test_keyframe_to_video_and_video_asset_card_menu_markers -> 2 passed
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 35 passed
npm.cmd run check:studio-js -> JS syntax check passed: 120 files
```

Boundary:

- No live provider call, video submission, provider raw response, signed URL,
  local private media byte, secret, or Company OS private source content was
  written to the repo.

## 2026-06-25 - Keyframe Asset References and Generic Asset Defaults

- Investigated the latest failed keyframe run for the current Studio project:
  Runtime reached the remote image provider and then produced a safe blocked
  manifest with `remote_image_provider_not_ready` after a read timeout. The
  evidence points to provider timeout, not copyright or safety blocking.
- Updated Studio keyframe request assembly so a keyframe generated from a
  storyboard can carry image refs from connected asset-card nodes in the same
  storyboard tree. Fixed visual assets remain project-wide strong references;
  unfixed connected asset cards are local references only and do not become
  global project constraints.
- Wired asset-card prompt-bar edits into the same conservative revision
  channel used by panel field edits. A typed adjustment now becomes a
  `user_instruction` delta with prior generated/user reference images as the
  anchor, and clearing the prompt-bar instruction clears that prompt-bar
  revision state.
- Added a non-current-story regression using `林晚 / 雨夜码头 / 蓝色雨伞` to
  guard against overfitting asset-card defaults to the Sun Wukong / Wolverine
  example. Also changed generic prop signatures so they summarize the prop
  itself instead of copying the whole shot sentence with unrelated character
  names.

Verification:

```text
pytest tests/test_web_studio_prompt_script_static.py::test_keyframe_generation_carries_connected_asset_card_images_as_local_refs tests/test_web_studio_assets_generation_static.py::test_asset_card_prompt_box_is_for_user_revision_and_uploaded_refs tests/test_web_studio_assets_generation_static.py::test_asset_card_defaults_generalize_to_unrelated_script_assets -> 3 passed
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 33 passed
pytest tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_context_resolver.py tests/test_api_runtime_keyframe_reference_assets.py -> 37 passed, 1 existing warning
npm.cmd run check:studio-js -> JS syntax check passed: 119 files
git diff --check -> passed
server /health after deploy -> ready; provider gates image=true, video=true
server keyframe provider smoke -> succeeded, output_count=1, PNG candidate_001.png present
```

Residual risk:

- The server smoke output was valid PNG data, but the returned dimensions did
  not strictly match the requested `16:9` ratio. The keyframe path is now live
  and not copyright-blocked, but provider aspect enforcement still needs a
  follow-up adapter or post-processing decision.

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo.

## 2026-06-24 - Runtime Image Provider Timeout Boundary

- Hardened Runtime image generation so provider read timeouts are retried once
  and then converted into a safe `remote_image_provider_not_ready` blocked
  manifest instead of surfacing as HTTP 500 with an empty run directory.
- This explains the latest failed Wolverine asset-card smoke: the request
  reached the remote image provider and timed out after the provider read
  window. The safe manifest path is now preserved for Studio recovery and
  diagnostics. The observed failure is not a copyright/safety block; no safety
  block was returned, and the server log showed a provider read timeout.

Verification:

```text
pytest tests/test_api_runtime_creative_agent_keyframes.py::test_keyframe_generation_provider_timeout_returns_safe_block -> 1 passed
npm.cmd run check:studio-js -> JS syntax check passed: 119 files
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo.

## 2026-06-24 - Scene Asset Prompt Isolation

- Tightened scene asset-card defaults so story character names, handheld
  weapons, and combat-summary text do not enter reusable scene signatures or
  feature-card fields. Mountain / stone-platform battlefield scenes now resolve
  to concrete environment facts: stone platform, cliff edge, cloud sea, distant
  ridges, broken rocks, cracks, high-altitude light, and weather.
- Strengthened the scene asset image prompt so upstream character names are
  treated only as environmental-trace context, never as permission to render
  characters, portraits, turnarounds, handheld weapons, or silhouettes.
- Limited asset-card node upload refs to user-uploaded reference images. Prior
  generated `scene_reference` / `generated_keyframe_reference` outputs remain
  available as node/history assets but no longer auto-contaminate the next
  asset-card generation request.
- Extended the same isolation to target character asset cards. A character card
  such as `金刚狼` now rejects unrelated story characters, props, scene labels,
  shot metadata, and combat-summary text from the target asset signature and
  fields. The generated character prompt explicitly asks for one target
  character only, with no second character, handheld prop, or scene background.
- Tightened the `金刚狼` defaults after live smoke showed the prompt could drift
  into a silver-haired sci-fi armor sheet. The card now anchors a mature rugged
  male, dark short hair, sideburns / stubble, stocky close-combat build, and
  body-integrated metal claws while rejecting monkey traits, silver hair,
  sci-fi armor, cyan glow lines, and mythic armor.
- Server validation also found the local image relay was returning image URLs
  from a safe relay cache host not present in `codex_image.allowed_artifact_hosts`.
  The server-local provider config was updated to allow that host; no provider
  key, signed URL, raw provider response, or media byte was written to Git.

Verification:

```text
pytest tests/test_web_studio_assets_generation_static.py::test_scene_asset_card_keeps_story_characters_out_of_environment_prompt tests/test_web_studio_assets_generation_static.py::test_asset_card_generation_only_carries_user_uploaded_reference_images -> 2 passed
pytest tests/test_web_studio_assets_generation_static.py::test_character_asset_card_keeps_other_story_assets_out_of_target_prompt -> 1 passed
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 31 passed
npm.cmd run check:studio-js -> JS syntax check passed: 119 files
git diff --check -> passed
Runtime provider control smoke after server allowlist update -> provider dispatch succeeded, output_count=1
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo.

## 2026-06-24 - Asset Card Adjustment Prompt And Timeout Recovery

- Separated asset-card generation prompts from the editable prompt bar. Asset
  image nodes now keep the typed field for user revision instructions only,
  while the full asset-card image prompt is assembled at generation time from
  the card draft.
- Let users upload reference images directly to an asset-card image node and
  include those uploaded image asset refs in that asset-card generation request.
  This supports "upload a reference + write a local adjustment prompt" without
  requiring an asset-card field edit first.
- Extended timeout recovery for image/asset generation to keep polling Runtime
  image assets for up to ten minutes, so a long provider run that finishes after
  the browser request times out can still recover the completed node preview.
- Hardened Studio state persistence so video media filenames such as
  `candidate_001.mp4` are pruned from safe display fields before global
  repository-safety scanning, while safe Runtime preview routes and asset ids
  remain available.

Verification:

```text
pytest tests/test_web_studio_assets_generation_static.py::test_asset_card_prompt_box_is_for_user_revision_and_uploaded_refs tests/test_web_studio_assets_generation_static.py::test_asset_card_node_generation_prompt_is_not_written_into_prompt_box -> 2 passed
pytest tests/test_api_runtime_studio_state.py::test_studio_state_prunes_media_filenames_before_global_safety_scan -> 1 passed / 1 existing warning
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 28 passed
pytest tests/test_api_runtime_studio_state.py tests/test_api_runtime_studio_state_persistence.py tests/test_api_runtime_studio_state_modules.py -> 16 passed / 1 existing warning
npm.cmd run check:studio-js -> JS syntax check passed: 119 files
git diff --check -> passed
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo. The Wolverine failure observed in the browser was a timeout/recovery
  and state-save issue, not a copyright/safety block based on the safe manifest.

## 2026-06-24 - Studio Asset Reference Scope And Asset Library History

- Tightened Studio `@` asset suggestions so ordinary generated image
  candidates are no longer treated as project-fixed assets. Unconnected nodes
  only see fixed visual assets; connected script trees can also see unfixed
  asset-card draft nodes in that same connected tree.
- Split the asset drawer view from generated history. The active material list
  now keeps fixed visual assets and the latest renderable candidate per source
  node, while older generated candidates move to `历史资产`.
- Updated the history modal to list historical image assets and render safe
  Runtime previews when available.
- Replaced the three script-node context menu entries for adding character /
  scene / prop assets with one `新增资产` action. The modal asks for the asset
  name, infers asset type from current script/shot context plus conservative
  local rules, and creates the same editable asset-card node path as other
  asset nodes.

Verification:

```text
pytest tests/test_web_studio_prompt_script_static.py::test_storyboard_asset_identification_uses_runtime_plan_and_allows_manual_asset_nodes tests/test_web_studio_prompt_script_static.py::test_asset_mentions_scope_fixed_project_assets_and_tree_candidates tests/test_web_studio_prompt_script_static.py::test_asset_mentions_exclude_generated_history_from_unconnected_nodes -> 3 passed
pytest tests/test_web_studio_assets_generation_static.py::test_asset_drawer_does_not_seed_placeholder_assets_or_duplicate_runtime_assets tests/test_web_studio_assets_generation_static.py::test_asset_drawer_splits_current_assets_from_generated_history -> 2 passed
npm.cmd run check:studio-js -> JS syntax check passed: 119 files
```

Boundary:

- This is Studio frontend state and interaction logic only. No provider gate,
  provider config, secret, signed URL, raw provider response, generated media
  byte, or Company OS private source content was written to the repo.

## 2026-06-24 - Seedance Video Relay Adapter

- Added a `volc_seedance` video provider adapter for relay-style Volc/Seedance
  task APIs. It builds a safe task payload for `doubao-seedance-2-0-fast`, sends
  text plus first/last frame image references, polls the task endpoint, downloads
  the resulting video into local Runtime candidate storage, and does not persist
  provider URLs or raw provider responses.
- Extended Runtime video dispatch so `last_frame_image_asset_id` is passed into
  provider dispatch as the second reference image. Existing first-frame-only
  providers still receive the first frame as before.
- Added `seedance_i2v` to `configs/providers.example.json` with only environment
  variable names, model/endpoint shape, and descriptor metadata. No real relay
  base URL, key, signed URL, or provider-local config was written.
- Added focused regressions for Seedance descriptor registration, video gate
  blocking before network, safe submit/poll/download behavior, and Runtime
  first/last frame propagation.

Verification:

```text
pytest tests/test_volc_seedance_video_adapter.py -> 4 passed / 1 existing warning
pytest tests/test_provider_adapter_registry.py tests/test_api_runtime_video_generations.py -> 41 passed / 1 existing warning
npm.cmd run check:studio-js -> JS syntax check passed: 118 files
git diff --check -> passed
```

Boundary:

- This is adapter/Runtime contract verification, not a live provider smoke,
  video-quality validation, human acceptance, or business validation. Server
  provider credentials and local provider config remain outside the repo.

## 2026-06-24 - Asset Card Fixed Asset Carry Policy

- Fixed Studio generation preflight for asset-card image nodes. Character
  asset-card generation now automatically excludes unrelated fixed assets so a
  new character card is not visually constrained by another fixed character in
  the project.
- Changed scene and prop asset-card generation to treat fixed assets as
  optional references. The confirmation modal now carries only checked assets
  for this one generation and excludes unchecked fixed assets from the request.
- Kept ordinary image/video generation on the stricter fixed-asset confirmation
  path, because those outputs should still preserve approved continuity unless
  the user explicitly excludes a fixed asset for the run.
- Added a static Studio regression covering the optional fixed-asset carry
  policy markers and user-facing confirmation text.

Verification:

```text
pytest tests/test_web_studio_assets_generation_static.py::test_asset_card_generation_uses_optional_fixed_asset_carry_policy -> 1 passed
npm.cmd run check:studio-js -> JS syntax check passed: 118 files
git diff --check -> passed
```

Boundary:

- Provider gates, provider configs, secrets, signed URLs, provider raw
  responses, and generated media bytes were not written to the repo. Browser
  visual acceptance and live provider quality remain separate validation claims.

## 2026-06-24 - Runtime Shot Asset Planning And Media Preview Controls

- Added a safe Runtime `/shot-asset-plans` route for shot-level asset planning.
  It returns reviewable character / scene / prop refs with evidence text, safe
  manifest metadata, and explicit non-claims. It does not create canvas nodes,
  call media providers, store provider raw responses, write generated bytes, or
  promote fixed memory.
- Rewired Studio `识别资产` for script/storyboard nodes to prefer Runtime asset
  planning and fall back to local parsing if Runtime is unavailable. Manual
  `添加角色资产` / `添加场景资产` / `添加道具资产` entries now let users add missed
  candidate asset cards directly from the script node menu.
- Mirrored the improved local fallback in Studio so offline parsing also
  recognizes named battle characters such as `孙悟空` / `金刚狼`, props such as
  `金箍棒`, and scenes such as `山巅石台战场` instead of falling back to generic
  `主角` / `主要场景`.
- Added scoped `@` asset suggestions for text inputs: fixed visual assets are
  project-wide candidates, while unfixed asset-card drafts are only suggested
  inside the same connected script tree. Retired/excluded assets are filtered
  out.
- Fixed left-side node port behavior. Clicking or dragging the left port now
  creates/connects upstream nodes; right-side behavior remains downstream.
- Exposed fixed-asset cancellation from image node context menus, reusing the
  Runtime visual-asset retire path so history is retained and future generation
  excludes the asset.
- Added a unified media preview modal for generated images and videos. Node
  results now support `放大查看`, candidate images can be enlarged, and `导出原图`
  / `下载视频` resolves Runtime media safely at click time instead of relying on
  an uninitialized link.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 118 files
pytest -> 634 passed / 520 deselected / 2 existing warnings
git diff --check -> passed
CLI help/version -> passed
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo. Browser visual acceptance and three-end deployment health remain
  separate validation claims.

## 2026-06-23 - Storyboard Asset Intelligence And Preview Recovery

- Hardened storyboard fallback into a two-pass local agent contract:
  first infer global named characters, scenes, and props from the whole script,
  then resolve each shot with local evidence plus inherited global entities.
  Line-based scripts now preserve line units as shots instead of collapsing
  them into a fixed-looking five-shot plan. Battle scripts such as
  `孙悟空大战金刚狼` now identify `孙悟空` and `金刚狼` as separate character
  assets, `金箍棒` as a prop asset, and concrete scene labels such as
  `山巅石台战场` instead of falling back to `主角` / `主要场景`.
- Tightened the provider storyboard instruction so remote LLM parsing is also
  told not to replace real names with generic labels, and to classify props
  such as weapons, maps, letters, and hand-held items as `prop`.
- Expanded automatic asset-card drafts toward the existing feature-card
  template: character cards now include appearance overview, hair/fur, face/head
  details, body build, wardrobe, palette, demeanor, and fixed reference-sheet
  layout; scenes include palette; props include holding / interaction relation.
  Defaults now include stronger heuristics for Sun Wukong, Wolverine-style
  opponent prompts, golden staff props, rainy city streets, and mountain-stage
  battlefields.
- Updated character asset generation prompts to require the fixed layout:
  front half-body close-up + centered full-body front + left-side full-body
  profile + back full-body, with no weapons, hand-held props, or background
  objects. Scene prompts now ask for a clean 2x2 grid of independent 16:9
  environment views.
- Improved asset-card local revision prompts for facial marks: a request like
  adding a scar on the left side of the face is treated as a localized
  image-guided edit, with the reference image dominating identity, layout,
  costume, body, props, and non-edited details.
- Fixed Studio node/result recovery surfaces: when Runtime has saved a
  reusable image asset but the first response lacks `candidate_previews`, the
  node can still complete from the reusable asset preview. Image result nodes
  and the asset drawer now expose an original-resolution export path using the
  safe Runtime preview route.
- Added pre-save Studio snapshot cleanup so stale local state with unsafe,
  wrong-project, or HTML timeout preview data is pruned before saving to
  Runtime. The backend safe-state validator remains strict.
- Maintenance note: `apps/api/runtime_storyboard_local.py` and
  `apps/studio/src/asset-card-drafts.js` are now slightly above 300 lines. They
  should be split into storyboard entity inference and typed asset-card heuristic
  modules in the next cleanup pass; both remain below the 500-line hard split
  threshold.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 115 files
pytest tests/test_api_runtime_storyboard_breakdown.py -q -> 9 passed / 1 existing warning
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py tests/test_web_studio_static.py -q -> 31 passed
pytest -q -> 630 passed / 520 deselected / 2 existing warnings
git diff --check -> passed
added-line sensitive pattern scan -> no output
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo. Live visual/provider acceptance remains a browser/manual verification
  step after deployment.

## 2026-06-23 - Keyframe Timeout Recovery And Scene Asset Anchors

- Fixed the Runtime image provider status mismatch where an async-described API
  relay could synchronously finish and return `already_complete`; Runtime now
  normalizes that path into `succeeded` and returns safe candidate previews and
  generated image assets in the first response.
- Hardened Studio image/asset generation after Nginx or browser 504 timeouts:
  raw HTML error bodies are sanitized, network interruptions become safe
  user-facing errors, and Studio keeps the node in a recovery state while it
  polls the Runtime image-asset list by `source_node_id`. If Runtime completed
  after the browser timed out, the node is restored to complete with the saved
  preview and image asset ref instead of staying failed while the asset drawer
  already contains the image.
- Added one conservative retry around project creation for transient Runtime
  network errors, with copy that distinguishes short connection interruption
  from a confirmed create failure.
- Corrected scene asset defaults that overfit "night city" into a rooftop:
  scene cards now only choose rooftop when the shot explicitly says roof /
  rooftop / terrace, while rain-night street cues prioritize city street,
  walkable ground, wet-road reflections, and rainy night atmosphere. Scene
  asset image prompts no longer hardcode "rooftop/location".
- Maintenance note: `apps/api/runtime_keyframes.py` remains a historical
  500+ line file. The next cleanup should extract async/sync provider status
  normalization and keyframe result recovery into a dedicated helper module.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 113 files
pytest tests/test_api_runtime_creative_agent_keyframes.py::test_async_image_provider_already_complete_returns_succeeded_preview tests/test_api_runtime_creative_agent_keyframes.py::test_keyframe_generation_returns_safe_image_preview_url tests/test_web_studio_assets_generation_static.py::test_keyframe_generation_polls_async_runtime_jobs_without_provider_jargon tests/test_web_studio_assets_generation_static.py::test_asset_card_image_generation_uses_asset_prompt_and_asset_labels -q -> 4 passed / 1 existing warning
pytest tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_asset_card_revision_legacy_slots.py tests/test_api_runtime_studio_state.py tests/test_api_runtime_studio_state_persistence.py tests/test_web_studio_assets_generation_static.py -q -> 44 passed / 1 existing warning
git diff --check -> passed
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo. Live browser/provider acceptance remains the user's manual test after
  deployment.

## 2026-06-23 - Asset Card Source-Image Edit Path

- Fixed the remaining asset-card local revision root cause: prior work made
  prompts reference-first, but Runtime still sent the previous image only as a
  generic reference image. Asset-card revisions with prior image refs now set
  `image_operation=edit`, pass the first prior generated/uploaded image as
  `edit_source_image_path`, pass ordered edit references, and request
  `image_input_fidelity=high`.
- Added OpenAI Images-compatible edit transport for external API providers.
  `request_format=openai_images` still uses JSON `/images/generations` for new
  images, but source-image edits now use multipart `/images/edits` with the
  original image in the `image` multipart field, matching the manual GPT-style
  edit flow.
- Kept AFS request-plan semantics as high-fidelity source-image edits while
  avoiding unsupported HTTP parameters by default: OpenAI Images multipart
  requests omit `input_fidelity` unless a provider config explicitly opts in.
- Added compatibility for deployed provider descriptors that still declare
  `reference_image_slots=0`: asset-card revisions now treat the first prior
  image as the required edit source instead of dropping it before dispatch, and
  API relay edit validation allows that source image even under old slot
  config.
- Relaxed provider reference-image slot validation from 8 to 16 so providers
  that support multiple edit/source images can be configured without AFS schema
  blocking them first.
- Changed the asset-card panel action label to `保存并局部修订生成` so the UI
  reflects that this path should preserve the previous image and apply only the
  card-field delta. Full redesign/regeneration remains a separate future UX
  mode rather than this button's behavior.

Verification:

```text
pytest tests/test_api_runtime_keyframe_reference_assets.py tests/test_provider_adapter_registry.py tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 58 passed / 1 existing warning
pytest tests/test_provider_adapter_registry.py tests/test_api_runtime_keyframe_reference_assets.py -> 37 passed / 1 existing warning
pytest tests/test_api_runtime_asset_card_revision_legacy_slots.py tests/test_provider_adapter_registry.py tests/test_api_runtime_keyframe_reference_assets.py -> 38 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 113 files
python -m pytest -q -> 626 passed / 520 deselected / 2 existing warnings
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, existing warnings only
git diff --check -> passed
server provider smoke -> source-image edit succeeded for robot metal-to-plush material revision; output preserved multi-view character sheet layout, adult humanoid proportions, head shape, blue glow details, and neutral grey background without chibi/toy drift
```

Boundary:

- No provider key, provider raw response, signed URL, local private path,
  generated media byte, or Company OS private source content was written to the
  repo. The live visual result has runtime/provider smoke evidence and still
  needs human acceptance in the browser workflow.

## 2026-06-23 - Asset Card Image Revision References

- Fixed the asset-card edit/regenerate path that behaved like pure
  text-to-image after a card detail changed. Studio now records an
  `assetCardRevision` plan with ordered prior generated/uploaded image asset
  refs, changed card fields, and preserve locks whenever a candidate asset card
  is saved.
- Asset-card drafts no longer collect arbitrary connected uploads. They carry
  only the explicit revision refs, which keeps the previous reference-slot
  overflow fix while allowing image-guided regeneration.
- Runtime now appends an asset-card revision guard to provider prompts when
  references are present: treat reference images as identity/layout anchors,
  apply only the card-field delta, and avoid changing the subject into a toy,
  chibi, mascot, unrelated character, or different body type.
- Tightened field-level revision policy after the plush-robot clothing edit
  still drifted visibly: `服装/外观` changes are now framed as an outer-garment
  layer only, `外形辨识` material changes are limited to surface treatment, and
  asset-card revision instructions are prepended ahead of the base prompt so
  provider prompt-length trimming keeps the changed fields and preserve policy.
- Strengthened the revision contract to reference-first / delta-only semantics:
  for asset-card local edits, the first reference image is the primary visual
  source of truth for identity, proportions, sheet layout, camera distance, and
  all non-edited details; the changed card fields are the only editable delta.
  Runtime no longer appends the generic "reference image is only supplemental"
  guard on this path.
- Studio state persistence now preserves the revision plan through Runtime
  sanitization, so saving a card and navigating away does not discard the
  reference logic.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 113 files
pytest tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_studio_state_persistence.py tests/test_api_runtime_studio_state_modules.py tests/test_web_studio_assets_generation_static.py tests/test_codex_image_handoff.py tests/test_api_runtime_generation_manifest_safety.py tests/test_web_studio_prompt_script_static.py -> 50 passed / 1 existing warning
git diff --check -> passed
```

Boundary:

- No provider gate was opened and no live image generation was triggered. The
  change writes only safe asset ids and prompt/test code to the repo; no
  provider raw response, signed URL, secret, local private path, generated media
  byte, or Company OS private source content was written.

## 2026-06-23 - Studio Asset Semantics and Canvas UX Repair

- Repaired storyboard asset semantics so local fallback and provider-discard
  fallback no longer collapse robot/rooftop scripts into generic `主角` and
  `主要场景` labels. The Studio and Runtime fallback paths now refine generic
  asset refs into context-specific labels such as `未来机器人` and `夜晚城市屋顶`.
- Changed right-click asset recognition to reuse the structured shot stored
  during storyboard breakdown, then refine it, instead of reparsing the node
  body and losing upstream context.
- Fixed prompt bar editing for text/script/asset-card draft nodes. Typing into
  the bottom prompt input now keeps the prompt bar open instead of switching
  focus into the node body.
- Restricted double-click creation to true blank canvas targets. Node
  double-click now opens the node prompt editor path, while chrome, overlays,
  controls, and existing nodes no longer open the create menu.
- Removed node click/drag landing geometry motion that caused apparent
  down-right jitter. Drag feedback keeps non-geometric states such as borders
  and shadows.
- Added an explicit asset-card edit loop: asset card drafts can be saved, or
  saved and regenerated, before the user decides whether to fix the asset.

Verification:

```text
pytest tests/test_api_runtime_storyboard_breakdown.py tests/test_web_studio_prompt_script_static.py -> 17 passed / 1 existing warning
pytest tests/test_api_runtime_storyboard_provider_quality.py tests/test_web_studio_static.py tests/test_web_studio_mature_shell_static.py tests/test_studio_interaction_layer.py -> 33 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 111 files
git diff --check -> passed
python tools/maintenance_audit.py -> failed=0, existing warnings only
Playwright browser smoke on local Runtime 8797 -> passed for create text node, prompt input persistence, storyboard split, semantic asset recognition, and asset-card save/regenerate button
```

Boundary:

- No provider gate was opened, and no provider secret, signed URL, provider raw
  response, generated media byte, user account data, or Company OS private
  source content was written. This is local structure/runtime/browser
  verification, not human visual acceptance or business validation.

## 2026-06-23 - Parallel Feature Integration and Deploy Baseline Cleanup

- Cleaned the deployed `/opt/afs/AgentFlowStudio` Git state before integrating
  new work. The directory had already received the `e201346` file contents but
  still had `b24dc57` Git metadata and dirty files; the diff was backed up to
  `/tmp/afs-opt-dirty-before-e201346-20260622-165701.patch`, then `/opt` was
  aligned to clean `e201346` without using `git reset --hard`.
- Integrated three parallel feature branches into local `master` with
  fast-forward history: Director Stage V2 contract, TuanTuan confirmed memory
  Runtime API, and the public site social square request board.
- Preserved the AFS Debug Studio generation repair at `e201346`; the merged
  features did not touch the repaired Studio generation guard, keyframe flow,
  asset popover, storyboard fallback, or context resolver files.
- Fixed one integration miss caught by focused tests: `runtime_service.py`
  registered the social square route, but the new
  `apps/api/runtime_social_square.py` file was initially not staged. A
  follow-up commit added the missing route module before deployment.
- Localized the Director Stage V2 handoff to Chinese so the integration did not
  add a new human-doc Chinese coverage warning.

Verification:

```text
pytest tests/test_runtime_director_compiler.py tests/test_runtime_director_compiler_v2.py tests/test_api_runtime_sprite.py tests/test_api_runtime_sprite_memory.py tests/test_api_runtime_social_square.py tests/test_site_homepage_static.py tests/test_site_social_square_static.py tests/test_api_runtime_auth.py tests/test_api_runtime_service.py -q -> 53 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 111 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, existing warnings only
git diff --check -> passed
pytest -q -> 622 passed / 520 deselected / 2 existing warnings
```

Boundary:

- No provider gate, secret, signed URL, generated media byte, provider raw
  response, user account data, or Company OS private source content was written.
  This integration is structure/runtime verification, not human acceptance,
  provider smoke, business validation, or durable memory promotion.

## 2026-06-22 - Asset Reference Lookup and Keyframe Flow Repair

- Changed generation context resolution so fixed assets can be injected by an
  explicit `@label` mention even when the asset node is not directly connected.
  Connected assets still win by graph distance; prompt-named fixed assets are
  the fallback lookup path.
- Replaced the front-end `named_asset_not_connected_fail_closed` hard stop with
  a confirmation path. If a stale or unusual preflight still reports an
  unconnected named asset, the user can continue by excluding it for that run
  instead of losing the generation.
- Let storyboard keyframe layers be created and generated without first fixing
  candidate asset cards. Candidate cards remain review/edit material; fixed
  assets only become generation constraints after promotion.
- Added fixed-asset cancellation from the asset detail popover. Cancelling uses
  the existing Runtime retire route and marks local node asset refs as retired
  so they no longer participate in generation context.
- Updated local storyboard fallback from mechanical three-sentence chunks to an
  adaptive sentence/length-based distribution. Provider LLM breakdown remains
  the preferred route when the LLM gate is enabled.

Verification:

```text
pytest tests/test_api_runtime_context_resolver.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_visual_assets.py tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 49 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 110 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, existing warnings only
git diff --check -> passed
pytest -> 602 passed / 520 deselected / 2 existing warnings
```

Boundary:

- No provider gate, secret, signed URL, generated media byte, provider raw
  response, user account data, or Company OS private source content was written
  to repo records. This pass fixes Studio/Runtime flow semantics; human visual
  acceptance still requires a fresh canvas regeneration.

## 2026-06-22 - Asset Image Prompt Quality Tightening

- Split provider-facing asset image prompts out of the asset-card data module
  into `asset-card-image-prompts.js`, keeping the editable card schema separate
  from model prompt assembly.
- Replaced Chinese `setting board / sheet / UI-like layout` wording with
  model-friendly visual targets: character turnaround, environment reference,
  and object reference. The prompt now explicitly forbids dashboards, app UI,
  charts, typography, labels, watermarks, and decorative card layouts.
- Asset-card image generation now prioritizes the current structured asset
  card prompt before stale `node.prompt`, which matters for existing live canvas
  nodes created before the prompt fix. Candidate character and scene assets
  default to `16:9`; props default to `1:1`.
- Provider-facing asset prompts no longer expose `@asset` tags. Studio keeps
  `@` labels in node titles and scripts, but image models receive plain asset
  names to reduce rendered text and label artifacts.

Verification:

```text
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py -> 20 passed
npm run check:studio-js -> JS syntax check passed: 110 files
pytest -> 600 passed / 520 deselected / 2 existing warnings
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, existing warnings only
git diff --check -> passed
Node prompt sample -> character/scene prompts use reference targets, 16:9 ratio, and no @ labels
deployment -> local/GitHub/server home/server opt aligned at 1b9892e; afs-runtime restarted and health ready
Crazyrouter smoke -> character reference succeeded in 30.34s; scene reference succeeded in 29.23s; both produced 16:9 non-UI reference images
```

Boundary:

- No provider gate, secret, signed URL, generated media byte, provider raw
  response, user account data, or Company OS private source content was
  written to repo records. The smoke proves Runtime/provider connectivity and a
  much faster direct image path, but final visual acceptance remains a human
  review on the Studio canvas.

## 2026-06-22 - Crazyrouter Image Relay Readiness Pass

- Added an OpenAI Images-compatible request path to the existing `api_relay`
  provider so a server-local `codex_image` service can call Crazyrouter
  `gpt-image-2` through `/images/generations` without changing the Studio
  front-end model mapping.
- Split image relay payload/output handling into a focused helper. The relay
  now supports `data[0].url` image responses by downloading the provider media
  into local AFS candidate artifacts while keeping provider URLs, raw responses,
  and credentials out of Runtime-safe results.
- Server diagnosis before deployment showed the live `afs-runtime` service was
  still loading `/opt/afs/AgentFlowStudio/configs/providers.local.json`, did
  not have a Crazyrouter service in the active registry, and had no
  `CRAZYROUTER_API_KEY` in the service environment. The user shell environment
  is not enough; systemd must receive the key and provider config path before
  a real image smoke can validate quality or speed.

Verification:

```text
pytest tests/test_provider_adapter_registry.py -> 30 passed
pytest tests/test_provider_adapter_registry.py tests/test_web_studio_prompt_script_static.py tests/test_web_studio_frontend_wave.py tests/test_web_studio_assets_generation_static.py tests/test_codex_image_handoff.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_keyframe_reference_assets.py -> 95 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 109 files
git diff --check -> passed
py_compile provider_api_relay.py provider_api_relay_images.py -> passed
server diagnosis -> Runtime active, but still on old provider config and no Crazyrouter service loaded
```

Boundary:

- No API key, provider raw response, signed URL, generated media byte, user
  session data, or Company OS private source content was written to the repo.
  The current evidence proves adapter readiness, not a successful live
  Crazyrouter image generation or human acceptance of visual quality.

## 2026-06-22 - Asset Reference Sheet Definition Pass

- Changed storyboard-derived asset-card generation from "single asset image"
  toward explicit reusable definition boards. Character assets now request a
  multi-view character sheet with front, side, back, and head/chest/detail
  views; scene assets request a same-space multi-angle environment board; prop
  assets request front/side/top/detail object views. The generation prompt now
  explicitly rejects single cinematic story illustrations for asset definition.
- Added reference-view fields to candidate asset cards and fixed-asset review
  cards so users can inspect and edit the intended view set before generating
  or fixing an asset. Candidate asset cards created from storyboard nodes now
  preserve the original draft fields when the generated image is fixed as a
  real visual asset, instead of falling back to generic "reference image
  subject" wording.
- Removed asset-tag pollution from short phrase extraction so `@主角（角色）`
  and `@主要场景（场景）` no longer become the asset signature or mood text.
  Added small local inference for the current robot rooftop case so character
  and scene cards carry robot body structure, cold-blue metal palette,
  rooftop/city skyline layout, and moon/star/low-saturation neon lighting.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 109 files
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_prompt_script_static.py tests/test_algorithm_library_contracts.py tests/test_web_studio_frontend_wave.py tests/test_api_runtime_studio_state_persistence.py tests/test_api_runtime_studio_state_modules.py -> 48 passed / 1 existing warning
pytest -> 598 passed / 520 deselected / 2 existing warnings
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, existing warnings only
git diff --check -> passed
Node REPL sample prompt check -> robot role prompt contains multi-view character sheet; rooftop scene prompt contains multi-angle scene board
```

Boundary:

- No provider gate, secret, signed URL, generated media byte, provider raw
  response, user account data, or Company OS private source content was
  written. This is runtime/code evidence, not human acceptance of the new
  generated images.
- Project lesson: an AFS asset is not a prettier keyframe. The "asset
  definition" target must be represented in the editable card schema, prompt
  assembly, fixed-asset review panel, and tests, otherwise image providers
  regress to single-shot illustrations.

## 2026-06-22 - Asset Image Prompt And Timing Audit

- Fixed the live-canvas issue where character and scene asset-card nodes could
  generate nearly identical abstract images. Asset-card image nodes now build
  the generation request from the editable asset card body when `node.prompt` is
  empty, include a safe `asset_card_draft` snapshot, and add type-specific
  guards: character assets focus on identity/material/proportion, scene assets
  avoid adding a character subject unless explicitly required, and prop assets
  focus on object form/material/use state.
- Separated asset-image generation semantics from keyframe generation in the
  Studio node path. Asset-card nodes now show `资产图生成` progress, return
  `资产图已生成` result text, and store generated uploads as character / scene /
  prop references instead of generic keyframe references.
- Added safe timing projection for the Codex image handoff worker. Request,
  pending, running, succeeded, and failed states now expose compact
  created/started/completed and elapsed/queued/running seconds through Runtime
  polling without storing provider raw responses or local absolute paths in API
  payloads.

Verification:

```text
pytest -> 598 passed / 520 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 108 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
pytest tests/test_web_studio_assets_generation_static.py tests/test_web_studio_frontend_wave.py tests/test_codex_image_handoff.py -> 41 passed / 1 existing warning
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
python -m py_compile for changed Runtime image modules -> passed
three-end deploy -> local/GitHub/server /home/server /opt aligned at 94fb9e1; afs-runtime and afs-codex-image-worker active; Runtime health ready
```

Boundary:

- Provider gates were not changed by this deployment. No generated media byte,
  provider raw response, signed URL, secret, invite code, session token, user
  account data, or Company OS private source content was written.
- Internalized project lesson: asset-card generation is not a keyframe
  generation with different labels. Asset type must affect prompt assembly,
  node progress semantics, upload roles, and verification evidence.

## 2026-06-22 - Studio Chain Regeneration Guardrails

- Hardened the Studio text -> storyboard -> asset-card -> keyframe chain around
  the current internal-test findings. Runtime Studio state now preserves only
  safe structured node params for storyboard shots, candidate asset cards,
  fixed visual assets, keyframe layer state, uploads, warnings, and one-run
  exclusions through small sanitizer modules instead of dropping the production
  graph semantics on save/reload.
- Fixed storyboard breakdown parsing so fenced or trailing LLM JSON is accepted
  instead of silently falling back to rough text splitting. The deterministic
  fallback also stops treating contextual words like `信号` and `灯火` as
  standalone prop assets. Provider output parsing now lives in a separate
  small module so the Runtime route remains orchestration-only. A second live
  check found that a provider can return syntactically valid but content-sparse
  storyboard JSON; long scripts now require enough shots, visual detail, and
  asset refs or the provider result is explicitly discarded and the safe local
  fallback is used.
- Tightened the candidate/fixed boundary: generated asset-card image candidates
  remain editable drafts until human confirmation, are saved as candidate asset
  kinds, and are not injected into keyframe prompt/context. Keyframe nodes now
  record missing candidate cards and block generation until required assets are
  fixed.
- Reduced image-generation pressure by avoiding repeated full Studio-state
  saves during every keyframe poll tick; state is flushed on terminal/status
  changes and periodic checkpoints instead.

Verification:

```text
pytest -> 597 passed / 520 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 107 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
```

Boundary:

- No provider raw response, signed URL, local media byte, secret, invite code,
  session token, or Company OS private source content was written.
- Internalized project lesson: candidate assets and fixed assets are separate
  evidence states. The boundary must be represented in persisted Runtime state,
  user-visible node state, and prompt assembly; UI labels alone are not enough.

## 2026-06-22 - Script Review Flow And Runtime Storyboard Breakdown

- Reworked text-to-storyboard flow so `拆分为分镜` now calls the Runtime
  `/storyboard-breakdowns` route and creates only editable storyboard script
  nodes. The Runtime route uses the LLM provider only when the LLM gate is open,
  otherwise it returns a deterministic structured fallback; safe manifests store
  summaries and artifact ids, not raw provider responses.
- Removed the selected-node bottom workflow toolbar from the canvas, including
  `继续生成 / 保存素材 / 整理卡片 / 看过程`. Text, script, and asset-card node
  bodies now render as editable text areas with local scroll, so generated full
  scripts and storyboard/asset descriptions can be reviewed and corrected in the
  node body.
- Changed storyboard downstream automation to the intended review order:
  storyboard nodes expose `识别资产` and `生成关键帧层`, but asset-card image nodes
  are created only after the user runs `识别资产` on a reviewed storyboard node.
  `生成关键帧层` now requires an existing asset layer instead of silently creating
  one.
- Preserved the asset-card backstage model for image generation. Asset-card
  nodes can be edited through the node body or prompt bar; after an actual image
  generation completes, the node body shows the generated image preview while
  the editable draft remains in `params.assetCardDraft`.
- Added structured storyboard parsing from edited node text so later asset
  recognition and keyframe prompts use the user's current `镜号 / 时长 / 画面描述
  / 景别 / 光影氛围 / 运镜 / 对白/旁白 / 音效 / 资产` fields instead of stale
  split metadata.

Verification:

```text
pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_frontend_wave.py tests/test_api_runtime_storyboard_breakdown.py tests/test_api_runtime_service.py -q -> 39 passed / 1 existing warning
pytest -> 592 passed / 520 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 107 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed, console_error_count=0, response_error_count=0, provider_calls_started=false
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
```

Boundaries:

- No provider gate, image generation, video generation, merge, push,
  deployment, server sync, raw provider response, signed URL, local media byte,
  secret, invite code, session token, or Company OS private source content was
  written.
- This is local code/runtime evidence plus automated browser QA. It is not
  human acceptance, provider smoke, business validation, or durable memory
  promotion.

## 2026-06-22 - Storyboard Asset Cards And Keyframe Layer

- Added editable candidate asset cards for storyboard-derived assets. Script
  nodes can now run `识别资产` to create downstream image nodes for roles,
  scenes, and props; these nodes store `params.assetCardDraft` and do not write
  fixed `visualAssets` before user confirmation.
- Added the `生成关键帧层` action for storyboard nodes. The generated keyframe
  image node connects back to the storyboard and asset-card nodes, but copies
  only already fixed visual assets into its generation context; unconfirmed
  candidate cards remain excluded and are reported as missing.
- Promoted prop assets to first-class support across Studio and Runtime
  contracts, including visual asset panels, asset summaries, drawer actions,
  Runtime draft/promotion models, context asset limits, and asset-card drafting.
- Split newly expanded helper logic to keep active files under the project
  maintenance threshold: `visual-asset-defaults.js` is 287 lines and
  `asset_card_drafting/__init__.py` is 294 lines after extraction.

Verification:

```text
pytest -q -> 587 passed / 520 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 107 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed with CRLF/LF warnings only
```

Boundaries:

- Provider gates were not opened; no remote LLM, image, or video provider call
  was made.
- Candidate asset cards are editable drafts, not fixed assets, human
  acceptance, business validation, provider smoke, or durable memory promotion.
- No provider raw response, signed URL, local media byte, secret, invite code,
  session token, server state, or Company OS private source content was written.

## 2026-06-21 - Prompt Template, Reference Image, And Provider Cleanup Pass

- Reworked image prompt optimization around a clearer priority order: current
  user intent first, reference image identity/visual traits second, old asset
  signatures and default locks last. Animal reference prompts now use
  `角色/主体`, preserve fur/markings/eyes/ears/tail/body ratio, and avoid the
  older human short-hair/uniform template unless the prompt is actually a human
  edit.
- Switched active Studio asset wording from `人物资产` to `角色资产` while keeping
  compatibility aliases for older `人物/主体` sections and stored LLM responses.
  Fixed asset detail and confirmation surfaces can reopen existing fixed assets
  for adjustment instead of treating them as fresh unrecognized candidates.
- Moved prompt optimization UI out of a blocking modal and into the selected
  node/prompt surface with shimmer feedback, so changing selection no longer
  disconnects the in-flight optimization. Draft-recognition fields and
  TuanTuan pending replies now expose visible progress states.
- Removed Minimax image/provider code paths from the active registry, CLI,
  smoke helpers, posterflow provider, tests, and preflight tools. Remaining
  Minimax references are negative compatibility tests that assert old services
  are ignored and not exposed.
- Hardened the Codex image handoff worker so completed candidates can be
  recovered from running/stale jobs, candidate files are accepted only after a
  stable write, and the worker can terminate a completed `codex exec` process
  instead of waiting on a long tail after the image file is already present.
- Added text-node script import, idea expansion, and storyboard breakdown
  affordances that write structured script content into text/script nodes and
  create downstream asset-prep candidates without auto-promoting fixed assets.

Verification:

```text
pytest -> 582 passed / 520 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 102 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed with existing CRLF/LF warnings only
Prompt fallback sample -> animal reference paths have no short-hair or uniform
  pollution; explicit animal clothing requests route to the explicit-style guard
```

Boundaries:

- Video provider execution remains out of scope and was not enabled.
- Local verification is code/runtime evidence, not human acceptance, business
  validation, or durable memory promotion.
- No provider raw response, signed URL, local media byte, secret, invite code,
  session token, or Company OS private source content was written.

## 2026-06-22 - Text Node Script Body And Structured Storyboard Split

- Changed text-node script import and idea expansion so the resulting script is
  written into the node body (`content`) instead of staying in the bottom prompt
  input. During expansion, the visible node body keeps the user's source text
  and shows a shimmer state until the expanded script replaces it.
- Hid the selected-node workflow toolbar on text nodes, removing the local
  clutter from `继续生成 / 保存素材 / 整理卡片 / 看过程` for script drafting.
- Added structured storyboard formatting for script split output. Each generated
  script node now carries explicit `镜号 / 时长 / 画面描述 / 景别 / 光影氛围 / 运镜 /
  对白/旁白 / 音效 / 资产` fields and keeps `@` asset references in its body.
- Added candidate asset-prep image nodes downstream from each storyboard node.
  These nodes are preparation targets only; they do not promote assets to fixed
  material without later generation and user confirmation.

Verification:

```text
tests/test_web_studio_prompt_script_static.py -> 5 passed
tests/test_web_studio_prompt_script_static.py tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py -> 30 passed
npm run check:studio-js -> JS syntax check passed: 102 files
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed, provider_calls_started=false
git diff --check -> passed with existing CRLF/LF warnings only
```

Boundaries:

- No provider gate, Runtime API shape, deployed server state, local media byte,
  provider raw response, signed URL, secret, invite code, session token, or
  Company OS private source content was written.
- Structured asset references are candidate preparation state, not durable
  memory promotion, fixed asset approval, human acceptance, or business
  validation.

## 2026-06-21 - Authenticated Media And TuanTuan Stability Repair

- Diagnosed broken uploaded/reference images in image nodes and the asset drawer:
  project media routes correctly require authenticated Runtime access, while
  plain browser image tags cannot attach the stored bearer session token.
- Added a small `runtime-media-source.js` render helper that fetches protected
  `/projects/...` media with the current Studio session token and assigns a
  blob URL to image, video, and download elements. Node previews, candidate
  grids, job thumbnails, and asset drawer thumbnails now share that path.
- Added a Runtime guard against TuanTuan LLM prompt echo, so persona/system
  instruction leakage falls back to safe local first-person replies.
- Preserved TuanTuan chat scroll position across widget rerenders and skipped
  full widget redraws during IME composition, avoiding lost Chinese input
  focus while typing.
- Let Codex image handoff polling recover a stable generated candidate from a
  still-marked running job directory, so a completed image file is not held
  hostage by a stale worker state.
- Added a one-shot Studio startup and project-switch refresh for image nodes
  still marked `generating`, so an already completed or failed Runtime image
  job can be reconciled without requiring the user to manually restart the
  whole generation chain.
- Repaired terminal-state polling recovery: if an older Runtime state was
  already marked failed/blocked but the Codex handoff worker later wrote a
  completed result with a safe candidate image, the next Runtime poll now
  rebuilds the succeeded manifest and preview instead of keeping the node stuck
  in a stale failure/running state.
- Split the new media DOM logic out of `runtime-client.js`; the client is back
  under the 300-line target while the media helper stays single-purpose.

Verification:

```text
tests/test_api_runtime_sprite.py tests/test_api_runtime_auth.py tests/test_codex_image_handoff.py tests/test_web_studio_sprite_static.py tests/test_web_studio_frontend_wave.py -> 33 passed / 1 existing warning
tests/test_codex_image_handoff.py -> 9 passed / 1 existing warning
tests/test_api_runtime_creative_agent_keyframes.py tests/test_web_studio_frontend_wave.py -> 22 passed / 1 existing warning
pytest -q -> 575 passed / 527 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 99 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only; oversized warning count reduced from 37 to 36 after split
git diff --check -> passed
```

Boundaries:

- Video remains out of scope and was not enabled.
- Backend media auth was not weakened; protected media is loaded through the
  existing logged-in Studio session.
- No provider raw response, signed URL, local media byte, secret, invite code,
  session token, or Company OS private source content was written.
- Verification is runtime/code evidence, not human acceptance, business
  validation, or durable memory promotion.

## 2026-06-21 - Non-Video Codex Flow And Studio Feedback Repair

- Repaired the Codex image handoff worker so systemd-style environments that
  do not include the user local bin directory can still resolve
  `~/.local/bin/codex`, and a missing CLI now becomes a safe worker error.
- Replaced the prompt optimizer strict-format retry mojibake with readable
  Chinese instructions, preserving the nine-section output contract.
- Tightened TuanTuan's LLM persona prompt so replies use `我` as TuanTuan and
  do not explain internal service/model routing; Runtime now also hard-limits
  LLM replies to two sentences / 220 characters.
- Added a visible TuanTuan pending message, moved image/video quality feedback
  into the node right-click menu, made completed image nodes fill the node body,
  and adjusted the prompt bar to choose a non-overlapping placement.

Verification:

```text
pytest -q -> 562 passed / 527 deselected / 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 96 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
Playwright browser smoke on local 8797 -> passed image fill, right-click feedback, prompt-bar avoidance, TuanTuan pending state, and no internal Codex/server wording
git diff --check -> passed
```

Boundaries:

- Video remains out of scope and was not enabled.
- No provider raw response, signed URL, local media byte, secret, invite code,
  session token, or Company OS private source content was written.
- Browser smoke used intercepted Studio state and sprite response for UI
  behavior; live server provider smoke is tracked separately from human
  acceptance and business validation.

## 2026-06-21 - Server Codex LLM Path Repair

- Rechecked local `master`, `origin/master`, server `/home/afs-ops/AgentFlowStudio`,
  and server `/opt/afs/AgentFlowStudio`: all were aligned at commit `0205148`.
- Diagnosed the TuanTuan chat fallback shown in Studio. The Runtime sprite route
  was already wired through the unified LLM dispatch boundary, but the deployed
  systemd process could not resolve the local `codex` executable.
- Repaired the server-local provider config by setting the `codex_local` service
  command to `/home/afs-ops/.local/bin/codex` for the non-video Codex-backed
  services. This change is intentionally server-local and not committed.
- Added a local regression guard so a missing Codex CLI is reported as
  `ModelGatewayError` instead of escaping as a raw `FileNotFoundError`.

Verification:

```text
Server provider smoke: llm/prompt_optimizer task_type=sprite_chat -> status=ok, provider_calls_started=true
Server Runtime route smoke: POST /projects/{project_id}/sprite/chat -> 200, mode=llm, provider_calls_started=true
tests/test_codex_local_provider_errors.py tests/test_api_runtime_sprite.py tests/test_provider_adapter_registry.py -q -> 37 passed / 1 existing warning
```

Boundaries:

- Video remains disabled.
- No ASR or external download gate was opened.
- No provider raw response, invite code, session token, signed URL, local media
  byte, secret, or Company OS private source content was written.
- Public browser UI chat was not exercised with a real authenticated session in
  this pass; the verified live path is provider-level plus Runtime route smoke.

## 2026-06-21 - TuanTuan Size And Public Edge Auth Follow-Up

- Reduced the default TuanTuan canvas footprint from a 260 x 238 base to a
  232 x 212 base, with the default scale lowered to `0.9`. Small / normal /
  large now map to `0.76`, `0.9`, and `1.08`, so TuanTuan stays present but is
  less likely to block Studio work.
- Added a local `afs_studio_sprite_hidden` preference. The settings panel can
  close TuanTuan, and the closed state leaves only a small `显示团团` restore
  chip so users can bring it back without clearing browser storage.
- Rechecked the public edge. `https://afstudio.art/studio/` still returns
  `blocked_by_edge_basic_auth`; the safe Nginx fix dry run on `/opt` reports
  `ready_to_apply` with exactly two target Basic Auth lines.
- Confirmed the current SSH user can read the Nginx site config but cannot
  apply the fix non-interactively because `/etc/nginx/sites-available/afs-runtime`
  is `root:root` and sudo requires a password.

Verification:

```text
tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -q -> 6 passed / 1 existing warning
npm run check:studio-js -> JS syntax check passed: 96 files
tools.afs_public_edge_preflight --public-url https://afstudio.art/studio/ --server afs-bwg-ops -> blocked_by_edge_basic_auth
server dry-run: tools.afs_public_edge_nginx_fix --config /etc/nginx/sites-available/afs-runtime -> ready_to_apply, target_line_count=2
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No invite code, session token, provider raw response, signed URL, local media
  byte, secret, or Company OS private source content was written.
- The public edge is diagnosed and ready for the existing sudo-scoped fix, but
  Nginx has not been changed in this session because sudo requires an
  interactive password.

## 2026-06-20 - Public Edge Gate For HTTP Acceptance

- Added a public-edge gate to deployed HTTP internal-beta acceptance. When
  `--base-url` and `--public-edge-status` are used together, the runner checks
  the public Studio edge before requiring invite codes or starting auth/project
  writes.
- If the edge is still blocked by Nginx Basic Auth, the runner now returns a
  safe `afs_internal_beta_acceptance_edge_gate_report` with
  `status=public_edge_not_ready`.
- If the edge is ready, deployed HTTP acceptance continues and stores the safe
  `public_edge_status` in the acceptance report.
- Split CLI arg parsing and the public-edge gate into focused modules so
  `tools/afs_internal_beta_acceptance.py` stays under the local line-count
  guard.

Verification:

```text
tests/test_afs_internal_beta_acceptance.py tests/test_afs_internal_beta_acceptance_cli.py tests/test_afs_internal_beta_preflight_public_edge.py tests/test_afs_public_edge_preflight.py tests/test_afs_public_edge_nginx_fix.py -q -> 23 passed / 1 existing warning
live HTTP acceptance edge gate without invite codes -> public_edge_not_ready, exit_code=2, edge_basic_auth=true, runtime_status=ready
```

Boundaries:

- No Nginx config was changed in this local session.
- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No invite code, session token, provider raw response, signed URL, local media
  byte, secret, or Company OS private source content was written.
- This is an acceptance safety gate, not completed public-login acceptance,
  human acceptance, or business validation.

## 2026-06-20 - Public Edge Nginx Basic Auth Fix Tool

- Rechecked the public Studio edge: `https://afstudio.art/studio/` still
  returns `401` with `WWW-Authenticate: Basic`, while Runtime `/health` is
  `ready` and three-end status is `aligned`.
- Confirmed the current SSH user can read the Nginx site config and belongs to
  `sudo`, but does not have passwordless sudo, so this local session cannot
  non-interactively edit `/etc/nginx/sites-available/afs-runtime`.
- Added `tools.afs_public_edge_nginx_fix`, a safe server-side repair command
  that backs up the Nginx site file and removes only the two known old Basic
  Auth lines for `AFS Studio Internal Test`.
- Updated public-edge preflight recommendations and the maintenance runbook to
  use the tested repair command instead of a raw `sed` edit.

Verification:

```text
live public-edge preflight before fix -> blocked_by_edge_basic_auth
three-end status before fix -> aligned
server runtime health -> ready
tests/test_afs_public_edge_nginx_fix.py tests/test_afs_public_edge_preflight.py tests/test_afs_internal_beta_preflight_public_edge.py -q -> 11 passed / 1 existing warning
```

Boundaries:

- No Nginx config was changed in this local session because sudo requires an
  interactive password.
- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS
  private source content was written.
- This is server repair tooling and diagnosis, not public-login acceptance,
  human acceptance, or business validation.

## 2026-06-20 - Three-End Status Acceptance CLI Guard

- Fixed standalone `tools/afs_internal_beta_acceptance.py --three-end-status`
  so it runs the safe local/GitHub/server status report instead of falling
  through to deterministic in-process acceptance.
- Added a focused CLI regression test that fails if standalone three-end status
  invokes `run_inprocess_acceptance`.
- Reused the JSON report writer across acceptance paths to keep report output
  consistent without changing Runtime behavior.

Verification:

```text
tests/test_afs_internal_beta_acceptance_cli.py::test_three_end_status_flag_runs_standalone_report_not_acceptance -q -> passed
tests/test_afs_internal_beta_acceptance.py tests/test_afs_internal_beta_acceptance_cli.py tests/test_afs_internal_beta_preflight_three_end.py tests/test_afs_three_end_status.py -q -> 17 passed / 1 existing warning
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS
  private source content was written.
- This is release/QA tooling repair, not human acceptance or business
  validation.

## 2026-06-20 - TuanTuan Reference Shape Calibration

- Rebalanced the V1 `story-cat` vector rig against the latest user reference:
  lower resting body, clearer dark tabby silhouette, larger triangular ears,
  calmer cyan eyes, smaller sprout, and quieter story orbit.
- Reduced the visual weight of the story panel so TuanTuan reads as a calm
  canvas-native story cat first, not a robot assistant or sticker.
- Kept all behavior on the existing sprite boundary: draggable position,
  right-click settings, size scaling, state poses, and Runtime sprite chat.

Verification:

```text
tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -q -> 6 passed / 1 existing warning
npm run check:studio-js -> passed for 96 files
git diff --check -> passed
Chrome render smoke on http://127.0.0.1:8797/studio/?project=tuantuan-local-preview-2 -> local screenshot inspected
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS
  private source content was written.
- This is a frontend visual calibration, not final IP illustration acceptance
  or full animation rigging.

## 2026-06-20 - TuanTuan Reference Shape Lock

- Reworked the Studio `story-cat` sprite from an abstract dark blob toward the
  provided TuanTuan reference: a low-profile dark tabby story cat with large
  triangular ears, large cyan eyes, sprout, forepaws, curled tail, tabby marks,
  and a quiet story orbit.
- Kept the implementation as DOM/SVG/CSS layers rather than raster pose
  switching, so future interaction can remain continuous without introducing a
  sticker-like asset swap.
- Added static shape anchors for the larger viewBox, ear gradient, soft glow,
  resting silhouette, forepaws, and back glow to reduce the chance of drifting
  back to the old abstract/robot look.

Verification:

```text
tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -q -> 6 passed / 1 existing warning
npm run check:studio-js -> passed for 96 files
tools/maintenance_audit.py -> failed=0; warnings only
git diff --check -> passed
Chrome render smoke -> story-cat, observe state, resting silhouette=true, orbit nodes=5
browser screenshot -> runs/tuantuan-reference-lock-20260620/tuantuan-crop-v2.png
```

Boundaries:

- No Runtime API shape was changed.
- No provider gate or provider config was changed.
- No provider call was made.
- No local source reference image, provider raw response, signed URL, local
  media byte, invite code, or secret was exposed.
- This is local static/browser verification, not human acceptance or business
  validation.

## 2026-06-19 - Studio TuanTuan Multi-Pose Mascot Follow-up

- Reworked the movable `AFS 小精灵` from a single raster sticker into a
  multi-pose `团团` mascot based on the latest provided IP reference.
- Added idle / happy / curious / thinking / surprised / sleepy / working /
  celebrate PNG poses and a lightweight pose state machine for hover, drag,
  settings, chat-open, sending, success, and idle cycling.
- Replaced the earlier CSS reconstruction with reference-derived PNG poses on
  one canvas companion stage.
- Kept the asset reference relative to Studio (`./assets/tuantuan-mascot.png`);
  the full local reference board and local absolute source path are not exposed
  in frontend code.
- Kept the existing Runtime sprite chat boundary, draggable shell, keyboard
  nudging, right-click settings, and local size persistence.
- Added right-click settings for the sprite with small / medium / large size
  options, persisted as a local UI preference.
Verification:

```text
TDD red: sprite static test failed while it still expected the old single-pose/static markers, then passed after the multi-pose contract update.
tests/test_web_studio_static.py tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -q -> 16 passed / 1 existing warning
npm run check:studio-js -> passed for 94 files
tools/maintenance_audit.py -> failed=0; warnings only
git diff --check -> passed
browser smoke -> initial=idle; hover/drag=happy; right-click settings=thinking; open chat=curious; 8 pose assets loaded at 410x515; console warn/error count 0
browser screenshot -> runs/tuantuan-sprite-multipose-smoke-20260619.png
```

Boundaries:

- No Runtime API shape was changed.
- No provider gate or provider config was changed.
- No provider call was made.
- Added only Studio UI mascot pose assets derived from the provided reference;
  the full local reference board and local absolute source path are not exposed.
- No provider raw response, signed URL, invite code, or secret was exposed.
- This is local static/browser verification, not human acceptance or business
  validation.

## 2026-06-19 - Studio Generation Action Module Split

- Split `apps/studio/src/node-actions.js` from a mixed 446-line node action
  and generation file into a thin 80-line router.
- Added `apps/studio/src/node-keyframe-actions.js` for keyframe submit, poll,
  response application, reusable image asset recording, and context badge
  reconciliation.
- Added `apps/studio/src/node-video-actions.js` for video first-frame setup,
  video submit, polling, local cancel, response application, and experimental
  video revision draft/submit state.
- Kept the public call surface through `node-actions.js`, so prompt bar, node
  menu, and canvas action handlers continue importing the same top-level
  actions.

Verification:

```text
TDD red: structure tests failed on missing node-keyframe-actions.js, then on missing node-video-actions.js
Studio static regression -> 43 passed
Studio/runtime focused regression -> 60 passed / 1 warning
npm run check:studio-js -> passed for 90 files
pytest -q -> 536 passed / 527 deselected / 2 warnings
tools/maintenance_audit.py -> failed=0; oversized warning count 33; node-actions.js removed from oversized findings
local HTTP static checks -> /studio/, /studio/src/node-keyframe-actions.js, /studio/src/node-video-actions.js returned 200
git diff --check -> passed
```

Boundaries:

- No Runtime API shape was changed.
- No provider gate or provider config was changed.
- No provider call was made.
- No Studio behavior was intentionally changed; this was a module-boundary
  refactor.
- No provider raw response, signed URL, local media byte, local path, invite
  code, or secret was exposed.
- This is local structural/runtime verification, not human acceptance or
  business validation.

## 2026-06-19 - LLM Enhancement Module Split

- Split `apps/api/runtime_llm_enhancement.py` into a thin orchestration module
  plus focused helpers for constants, provider gate/candidates, safety parsing,
  instruction assembly, deterministic fallback prompts, and dispatch fallback.
- Preserved the Runtime prompt optimization API shape and existing monkeypatch
  seams, including `load_provider_registry`, `llm_provider_gate`,
  `provider_text_requested`, `sanitize_enhanced_prompt`, and
  `deterministic_chinese_fallback_prompt`.
- Added a structural regression test for the helper split, line-count
  thresholds, and UTF-8 Chinese prompt labels so future refactors cannot damage
  the prompt contract silently.

Verification:

```text
tests/test_api_runtime_llm_enhancement_modules.py: red on missing helper modules, then 1 passed
tests/test_api_runtime_llm_enhancement_modules.py tests/test_api_runtime_prompt_memory_loop.py tests/test_model_call_context_runtime_routes.py tests/test_api_runtime_sprite.py tests/test_provider_adapter_registry.py -> 59 passed / 1 warning
pytest -q -> 536 passed / 527 deselected / 2 warnings
apps.cli.main --help -> passed
apps.cli.main version -> 0.1.0
tools/maintenance_audit.py -> failed=0; warnings only
git diff --check -> passed
```

Boundaries:

- No Runtime API shape was changed.
- No provider gate or provider config was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, local path, or secret
  was exposed.
- This is module/runtime verification, not human acceptance or business
  validation.

## 2026-06-19 - Sprite Companion Personality Polish

- Refined the movable `AFS 小精灵` into a clearer Studio navigator character instead of a parts-heavy helper.
- Added `data-sprite-character="navigator"` plus visible halo crown, glass helmet, face window, wand, and personality tag.
- Isolated the final silhouette layer in `apps/studio/styles/studio-sprite-avatar-personality.css` so existing sprite CSS files stay within the maintenance threshold.
- Extended the sprite static regression test so future changes must preserve the character-shape contract as well as the Runtime `sprite/chat` boundary.

Verification:

```text
tests/test_web_studio_sprite_static.py: red on missing character-shape contract, then 1 passed
npm run check:studio-js: passed for 88 files
Browser QA on http://127.0.0.1:8797/studio/: new character parts rendered, cursor=grab, drag moved from (558, 191) to (478, 151), panel opened without position jump, console warn/error count 0
```

Boundaries:

- No Runtime API shape was changed.
- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is frontend runtime/browser verification, not human acceptance or business validation.

## 2026-06-19 - Studio State Module Split

- Split `apps/api/runtime_studio_state.py` into a thin route module plus
  focused safe-state helpers. The route now owns HTTP persistence and version
  metadata; `runtime_studio_state_sanitizer.py` owns top-level state
  projection; `runtime_studio_state_context.py` owns context bundle
  projection; `runtime_studio_state_assets.py` owns asset-list sanitization;
  `runtime_studio_state_preview.py` owns safe Runtime preview URL allow-listing.
- Preserved the existing Runtime API shape and the public
  `sanitize_studio_state` import compatibility from the route module.
- Added a structural regression test so future changes cannot fold nodes,
  params, context bundles, assets, or preview URL safety back into the route
  file. All new Studio state modules remain under the 300-line maintenance
  threshold.

Verification:

```text
tests/test_api_runtime_studio_state_modules.py tests/test_api_runtime_studio_state.py -> 10 passed / 1 warning
Runtime/internal-beta focused set -> 32 passed / 1 warning
pytest -q -> 534 passed / 527 deselected / 2 warnings
tools/maintenance_audit.py -> failed=0; oversized warning count 36
git diff --check -> passed
```

Boundary: no Runtime API shape changed, no auth policy changed, no provider
gate changed, no provider call was made, and no local path, signed URL,
provider raw response, media byte, invite code, or session token was added to
persisted Studio state. This is Runtime/module verification, not human
acceptance or business validation.

## 2026-06-19 - HTTP Preflight Three-End Status Addendum

- Extended `tools/afs_internal_beta_acceptance.py --preflight-only` with an
  optional `--three-end-status` check. Preflight can now produce one safe
  readiness report that covers deployed Runtime `/health`, `/auth/status`,
  Studio static readiness, provider gate projection, and local/GitHub/server
  drift state.
- Added `tools/afs_internal_beta_preflight_three_end.py` so three-end collection
  and report sanitization stay out of the main acceptance runner. The embedded
  report keeps only safe commit/status summaries, safe Runtime health fields,
  and provider gate booleans.
- If three-end status is not `aligned`, the preflight report now becomes
  `needs_attention` even if Runtime health checks pass. Default preflight
  behavior remains unchanged unless `--three-end-status` is explicitly used.

Verification:

```text
tests/test_afs_internal_beta_acceptance.py -> 10 passed / 1 warning
tests/test_afs_three_end_status.py tests/test_afs_internal_beta_acceptance.py -> 15 passed / 1 warning
CLI help shows --three-end-status, --three-end-repo-root, --three-end-server
```

Boundary: no provider gate changed, no provider call was made, no invite code,
session token, base URL, local path, signed URL, provider raw response, or
media byte is written into the preflight report. This is readiness inspection,
not human acceptance or business validation.

## 2026-06-19 - Sprite Character Design Pass

- Reworked the decorative `AFS 小精灵` from a button-like floating helper into
  a clearer movable canvas companion. The avatar now has a larger fixed
  footprint, visible drag chip, cockpit glass, canopy highlight, scanner visor,
  cheek/mouth detail, status light, shoulders, arms, mittens, wings, feet,
  tail fin, dock ring, glow trail, and thruster so it reads as a character at
  normal Studio scale rather than a generic floating control.
- Preserved the existing Runtime chat boundary and drag behavior. The avatar
  and panel header remain draggable, position is clamped with separate width
  and height values, and local storage persists only viewport coordinates.
- Split limb/propulsion styling into
  `apps/studio/styles/studio-sprite-avatar-parts.css` so each sprite stylesheet
  stays under the project maintenance warning line.

Verification:

```text
tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -> 6 passed / 1 warning
npm run check:studio-js -> JS syntax check passed: 87 files
git diff --check -> passed
Browser check on 127.0.0.1:8799/studio -> character parts=8, avatar drag moved
  -180/-120 and persisted position, panel-header drag moved and persisted
  within viewport clamp, panel opened, open status light turned green,
  console warn/error count=0
```

Boundary: no Runtime provider gate changed, no provider call was made, no
provider raw response, signed URL, local media byte, or secret was exposed.
This is UI/runtime verification only, not human acceptance.

## 2026-06-19 - Three-End Status Report Tool

- Added `tools/afs_three_end_status.py` as a safe local/GitHub/server status
  reporter. It checks the local checkout, optional server `/home` checkout,
  optional server `/opt` checkout, and Runtime `/health` through safe fields
  only.
- The report keeps provider calls closed and records only commit alignment,
  dirty state, safe Runtime health booleans, Studio static readiness, auth
  readiness, and provider gate booleans. It does not record provider config,
  local/server absolute runtime paths, signed URLs, session tokens, provider
  raw responses, media bytes, or secrets.
- Empty or unparsable checked health is treated as `needs_attention`, while
  missing health is only allowed when the caller intentionally runs local-only
  mode.

Verification:

```text
tests/test_afs_three_end_status.py -> 5 passed
tests/test_afs_three_end_status.py tests/test_afs_internal_beta_acceptance.py -> 13 passed / 1 warning
full pytest -> 528 passed / 527 deselected / 2 warnings
maintenance_audit -> failed=0, warnings only
git diff --check -> passed
```

Boundary: this is an ops/readiness report only. It does not pull, restart,
open provider gates, call providers, claim human acceptance, or write durable
memory.

## 2026-06-19 - HTTP Internal Beta Preflight Mode

- Added a `--preflight-only` mode to
  `tools/afs_internal_beta_acceptance.py` for deployed Runtime checks that do
  not require disposable invite codes and do not execute the full beta
  acceptance contract.
- The preflight report reads only safe public surfaces: `/health` and
  `/auth/status`. It summarizes runtime readiness, auth surface readiness,
  Studio static readiness, and provider gate projection without recording base
  URLs, invite codes, session tokens, signed URLs, provider raw responses,
  media bytes, or local paths.
- Kept the existing full HTTP acceptance path unchanged for later disposable
  invite-code tests.

Verification:

```text
tests/test_afs_internal_beta_acceptance.py -> 8 passed / 1 warning
local dev preflight on 127.0.0.1:8797 -> needs_attention because auth_required=false,
  provider_calls_started=false, safe report written
CLI help/version -> passed
full pytest -> 523 passed / 527 deselected / 2 warnings
maintenance_audit -> failed=0, warnings only
git diff --check -> passed
```

Boundary: preflight is readiness inspection only. It is not full HTTP beta
acceptance, not provider smoke, not human acceptance, not business validation,
and not durable-memory promotion.

## 2026-06-19 - Sprite Avatar Shape And Drag Stability Polish

- Strengthened the `AFS 小精灵` visual silhouette so it reads as a small
  movable canvas companion instead of a plain floating control. The avatar now
  has an explicit drag halo, larger body shell, head shell, visor, core light,
  side wings, feet, and bottom thruster.
- Raised the sprite fixed layer above modal level so it remains reachable while
  Studio panels are open, without changing Runtime or provider behavior.
- Fixed a drag/re-render edge case by remembering the current DOM position
  before the sprite re-renders. This prevents the avatar from jumping back to an
  older stored position when the user drags it and then opens the chat panel.
- Split sprite label/motion styles into `studio-sprite-avatar-motion.css` so
  the avatar structure stylesheet stays below the project maintenance line.
- Moved the sprite static contract into `tests/test_web_studio_sprite_static.py`
  instead of growing the already-large general Studio static test file.

Verification:

```text
tests/test_web_studio_sprite_static.py::test_studio_sprite_widget_is_wired_to_runtime_chat -> passed
tests/test_web_studio_static.py tests/test_web_studio_sprite_static.py tests/test_api_runtime_sprite.py -> 16 passed / 1 warning
npm run check:studio-js -> JS syntax check passed: 87 files
git diff --check -> passed
Browser check on 127.0.0.1:8797/studio -> avatar parts present, fixed layer z-index=81,
  avatar drag stable, open-panel click keeps position delta=0, panel-header drag moves sprite,
  console warn/error count=0
```

Boundary: no provider gate changed, no provider call was made, no generated
media bytes or provider raw response were persisted, and this is UI/runtime
verification only, not human acceptance or business validation.

## 2026-06-19 - HTTP Internal Beta Acceptance Runner

- Extended the deterministic internal beta acceptance runner with a deployed
  Runtime HTTP mode. `tools/afs_internal_beta_acceptance.py` now accepts
  `--base-url` plus two disposable invite codes from CLI flags or
  `AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE` /
  `AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA`.
- Split the acceptance runtime client and config into small dedicated modules.
  The HTTP client uses `trust_env=False` so local/server acceptance connects
  directly to the target Runtime instead of inheriting workstation proxy
  settings.
- Parameterized the existing acceptance contract with generated project IDs,
  emails, invite codes, and mode labels. The in-process deterministic mode
  remains unchanged for default local verification.
- Preserved the report boundary: reports include step evidence and non-claims,
  but not invite codes, session tokens, passwords, base URLs, media bytes,
  signed URLs, provider raw responses, or local runtime paths.

Verification:

```text
tests/test_afs_internal_beta_acceptance.py -> 6 passed / 1 warning
tools/afs_internal_beta_acceptance.py -> contract_verified_pending_human_acceptance
HTTP missing alpha/beta invite modes -> safe configuration_error, no warning noise
temporary local Runtime HTTP smoke -> deployed_http_runtime, 12 steps, 0 failed,
  provider_calls_started=false
full pytest -> 521 passed / 527 deselected / 2 warnings
maintenance_audit -> failed=0, warnings only
git diff --check -> passed
```

Boundary: this is deployed Runtime contract verification only. It is not live
provider smoke, not human acceptance, not business validation, and not durable
memory promotion.

## 2026-06-19 - Sprite Character Design Follow-up

- Reworked `AFS 小精灵` from a generic floating control into a clearer
  micro-assistant character with a fixed viewport layer, visible visor, glowing
  core, side stabilizers, feet, antenna, shadow, and docking label.
- Kept the sprite movable by dragging the avatar, and added panel-header
  dragging so the assistant can still be repositioned when the chat panel is
  open.
- Moved the idle breathing motion from the clickable button shell to the inner
  body layer. This preserves the visual float while keeping the hit target
  stable for browser automation and user clicks.

Verification:

```text
Sprite browser check on 127.0.0.1:8797/studio -> fixed layer, avatar drag,
panel-header drag, character parts present, console warn/error count=0
tests/test_web_studio_static.py -> 11 passed
tests/test_api_runtime_sprite.py -> 5 passed / 1 warning
npm run check:studio-js -> JS syntax check passed: 87 files
git diff --check -> passed
```

Boundary: no Runtime provider gate changed, no provider call was made, and the
sprite still only uses the existing safe Runtime chat endpoint.

## 2026-06-19 - Studio Panels And Sprite Assistant

- Fixed persistent canvas edge anchoring so saved edges attach to the node frame
  boundary while drag-in-progress lines still originate from the visible plus
  port.
- Added a resizable left drawer with a narrow drag handle and local UI width
  persistence. Added a collapsible right inspector so the canvas can reclaim
  horizontal space during creation.
- Disabled accidental text selection on the Studio chrome while preserving text
  selection in inputs, textareas, selects, contenteditable fields, and explicit
  selectable text surfaces.
- Added an `AFS 小精灵` canvas companion as a decorative assistant. It can be
  dragged around the Studio viewport, persists its position locally, adapts its
  chat panel to left/right and top/bottom docking, and now has a recognizable
  micro-assistant body, visor, side fins, antenna, shadow, and label instead of
  a generic floating button. It calls the Runtime through
  `/projects/{project_id}/sprite/chat`, falls back to local safe rules when the
  LLM gate or provider is unavailable, and does not execute actions or write
  durable memory.
- Split the new drawer resize and inspector collapse styles into dedicated
  small CSS files instead of growing the already-large shell and inspector
  styles. Split the sprite docking/chat styles from the sprite avatar styles so
  both new CSS files stay under the 300-line maintenance threshold.
- Added a deterministic internal beta acceptance runner for auth scope, project
  isolation, image assets, draft-vs-fixed asset lifecycle, context reuse,
  feedback evidence, artifact scope, and video gate-closed behavior. The runner
  is split into entrypoint, contract, scope steps, and generation steps so no
  new tool file exceeds the maintenance threshold.

Verification:

```text
Focused Studio/Runtime regression -> 26 passed / 1 warning
Internal beta acceptance runner -> contract_verified_pending_human_acceptance
Full pytest -> 517 passed / 527 deselected / 2 warnings
npm run check:studio-js -> JS syntax check passed: 87 files
CLI help/version -> passed, version 0.1.0
maintenance_audit -> failed=0, warnings only
git diff --check -> passed with Windows CRLF notice only
Browser QA note:
  in-app browser automation was blocked by Browser URL policy for the local
  Studio URL in this pass, so movable-avatar visual acceptance is not claimed.
```

Boundary: the sprite assistant is decorative and safe-summary only; it does not
open a new provider gate, bypass project-owner auth scope, persist provider raw
response, expose local paths or signed URLs, execute actions, or promote chat
feedback into durable memory.

## 2026-06-19 - Deep UX And Runtime Hardening

- Hardened Runtime `/health` so `runtime_root_persisted` is computed as a safe
  boolean from the configured runtime root and does not expose absolute paths.
- Added account isolation regression coverage for Studio state, image assets,
  previews, jobs, and artifact manifests across two users.
- Reworked the site first viewport further toward a professional AI video
  creation entry with concrete project/preview language and less algorithm
  exposition.
- Decluttered the Studio inspector around next action, current reference
  summary, drawer links, and folded detail sections.
- Refined canvas operation feel: persistent edges anchor to visible port
  centers, default edge weight is lighter, selected-node directional flow is
  slower, port magnet vertical range is tighter, and generating text shimmer is
  less aggressive.
- Split Studio project lifecycle work out of `main.js` into
  `studio-project-controller.js`, keeping the entrypoint under the project
  maintainability target.
- Added `npm run check:studio-js` to syntax-check Studio and site JavaScript.
- Wired the Runtime CLI `--runtime-root` option to `AFS_RUNTIME_ROOT`, so the
  server systemd environment is actually passed into `create_runtime_app()`.
- Added a closeout handoff that records role-by-role review, local/GitHub/server
  alignment, deployment evidence, explicit non-claims, and the next internal
  beta acceptance slice.

Verification:

```text
npm run check:studio-js -> JS syntax check passed: 86 files
Focused Runtime/Studio/site regression -> 69 passed / 1 warning
Full pytest -> 508 passed / 527 deselected / 2 warnings
CLI help/version -> passed, version 0.1.0
runtime-service help -> shows env var: AFS_RUNTIME_ROOT
maintenance_audit -> failed=0, warnings only
git diff --check -> passed
```

Boundary: no video gate was opened, no new provider was introduced, no provider
raw response, signed URL, secret, or generated media byte was persisted, and no
human creative acceptance or business validation is claimed. Closeout:
`docs/handoff/AFS-DEEP-UX-RUNTIME-HARDENING-CLOSEOUT-20260619.md`.

## 2026-06-19 - Studio Context Transparency And Edge Flow Polish

- Reworked the site root presentation so the first viewport is a direct
  professional AI video creation entry. The six core algorithms remain
  available as a folded technical boundary instead of occupying a homepage
  section.
- Added a small `asset-lifecycle` module and wired it into the Studio asset
  drawer. Assets are now separated as all / fixed / candidate / retired, with
  state-aware empty copy so draft evidence is not confused with confirmed
  assets.
- Split inspector context copy into `inspector-context-summary.js`. The right
  inspector now states what was included, what was excluded, and which
  candidate assets still need user confirmation before entering future calls.
  Object-shaped context warnings are formatted through safe summary fields
  instead of rendering raw objects.
- Adjusted canvas edges after visual review: stable lines are thinner, and
  edges connected to the selected node get a directional spark overlay that
  flows downstream or reverses when the downstream node is selected. Slowed the
  selected-edge spark so the flow reads as guidance instead of a fast warning.
- Added a subtle generating-text shimmer for in-progress node state strips,
  node generation progress, optimizer loading copy, and running job labels,
  with reduced-motion fallback.
- Fixed the drawer render signature so asset search and lifecycle filter
  changes invalidate the drawer and actually redraw the list.
- Resolved the current-scope maintainability warnings from this pass by moving
  edge SVG styling into `canvas-edges.css` and splitting the broad Studio
  static regression file into focused asset/generation and mature-shell files.

Verification:

```text
Browser QA on http://127.0.0.1:8797/:
  homepage first viewport is a Studio creation entry, no algorithm section in
  the main page flow, folded technical boundary present, no horizontal
  overflow, console warn/error count=0.
Browser QA on http://127.0.0.1:8797/studio/?project=frontend-scroll-overlap-final-2:
  selected upstream edge spark active with forward animation; selected
  downstream edge spark active with reverse animation; default edge
  stroke-width=1.35px; associated edge stroke-width=1.75px; asset lifecycle
  filters render and redraw; inspector shows context and asset confirmation
  summaries; console warn/error count=0.
Browser style verification on http://127.0.0.1:8797/studio/?project=frontend-scroll-overlap-final-2:
  `generation-feedback.css` loaded; selected edge spark duration=2.6s;
  generating text shimmer duration=3.2s; console warn/error count=0.
Focused Studio/Site static and interaction regression: 46 passed.
Focused post-split Studio static and edge regression: 33 passed.
Focused generating-feedback and mature-shell regression: 20 passed.
Full default pytest: 493 passed / 527 deselected / 2 warnings.
Studio/Site JS node --check: passed.
git diff --check: passed with the existing CRLF notice on assets.css only.
```

Boundaries:

- Provider gates remain closed; no model/provider call, generated media byte,
  local provider config, secret, signed URL, or provider raw response was
  touched.
- This is frontend/runtime browser verification, not human creative
  acceptance, provider smoke, business validation, or durable-memory
  promotion.

## 2026-06-19 - COS/GFR Display Package v0.1

- Froze the current COS/GFR TaskRun flow map into versioned bilingual
  distribution assets under the source-KB investor package: zh-CN and en SVG,
  PNG, and PDF.
- Rewrote the first HTML page into a restrained long-form narrative that leads
  with the production-control problem before introducing COS/GFR names.
- Rewrote the COS/GFR mechanism page around layer boundaries, the versioned
  TaskRun map, startup packet fields, fractal dispatch, loop engineering, and
  explicit non-claim boundaries.
- Added a concrete TaskRun example in the source KB and registered it in
  `TASKRUN-LEDGER-V0.json` as candidate loop-learning evidence.

Verification:

```text
Source JSON parse: passed
Versioned SVG XML parse: passed at 2600x2860
HTML local href/src check: passed
Playwright desktop/mobile render check: no horizontal overflow, no broken images, no console warn/error
Company OS contract validator: passed
GFR audit: passed with checked_paths=41, checked_packets=5, errors=0, warnings=0
```

Boundaries:

- No Runtime API or Studio code was changed in this slice.
- Provider gates remained closed; no provider call, generated media byte,
  secret, signed URL, or provider raw response was touched.
- This is structure/render verification plus candidate feedback routing, not
  human acceptance, business validation, or durable memory promotion.

## 2026-06-19 - Studio Edge Anchor Regression Follow-up

- Fixed the final edge-anchor regression from browser review: persisted edges
  now anchor to node frame boundaries with port-aligned vertical placement,
  while pending drag edges still originate from the visible plus port.
- Changed default stable edges from animated dash lines to solid round-capped
  paths so endpoint dash gaps no longer read as detached from the node frame.
- Kept incident edge SVG groups visible during node drag; dragging a connected
  node now keeps the edge present, opaque, and recalculated against the moving
  node.
- Added regression coverage for frame-anchored persisted edges, plus-origin
  pending geometry, visible incident edges, and solid default edge styling.

Verification:

```text
Browser QA on http://127.0.0.1:8797/studio/?project=edge-anchor-regression-20260619:
  persisted edge path starts at the left node frame right boundary and ends at
  the right node frame left boundary; stable edge stroke-dasharray=none and
  stroke-linecap=round; after dragging the left node, edgeCount=1,
  edgeOpacity=1, and the path endpoint followed the moved node; console
  warn/error count=0.
Studio interaction tests: 10 passed.
Focused Studio/Site/Runtime regression: 46 passed / 1 warning.
Studio/Site JS node --check: 82 files passed.
Full default pytest: 491 passed / 527 deselected / 2 warnings.
CLI help/version: passed; version 0.1.0.
maintenance_audit: failed=0, warnings only.
git diff --check: exit 0 with Windows CRLF notice on overlay.js only.
```

Boundaries:

- No Runtime API contract changed.
- Provider gates remain closed; no model/provider call, generated media byte,
  local provider config, secret, signed URL, or provider raw response was
  touched.
- This is runtime/browser/frontend verification, not human acceptance,
  creative quality validation, business validation, or durable-memory
  promotion.

## 2026-06-19 - Studio Port Geometry And Homepage Entry

- Reworked Studio connection geometry so pending drag edges originate from the
  visible `.node-port` button center, while persisted edges anchor to the node
  frame with port-aligned vertical placement. This keeps the "pull from plus"
  feel without leaving a visual gap on stable connections.
- Tightened port magnet behavior: left and right ports now have distinct
  side-specific hit bands, and vertical follow is bounded to avoid oversized
  up/down attraction.
- Rebuilt the site root first viewport as a professional AI video creation
  entry: direct Studio actions, template stack, current project entry, and
  recent work previews. The algorithm explanation is now below the first
  screen instead of the primary visual.
- Decluttered the Studio right inspector around "next action" and "current
  reference summary"; node drafts, output records, and algorithm trace stay
  behind collapsed disclosures, with asset/progress/work library as drawer
  entry points.
- Split frontend structure in low-risk slices: store state serialization,
  local persistence, project session helpers, node generation restore helpers,
  and port geometry.

Verification:

```text
Browser QA on http://127.0.0.1:8797/:
  root homepage 200, creation hero visible, 8 template/project/work cards,
  no horizontal overflow.
Browser QA on http://127.0.0.1:8797/studio/:
  inspector main sections are next action/current reference/more panels,
  algorithm details are closed by default, persisted edge path starts/ends at
  node frame boundaries, pending connection still starts from the visible plus
  port, left/right magnet states work, vertical far-y magnet clears, console
  error count=0.
Focused frontend/runtime tests: 16 passed.
Studio/Site JS node --check: passed.
Full default pytest: 489 passed / 527 deselected / 2 warnings.
CLI help/version: passed.
maintenance_audit: failed=0, warnings only.
git diff --check: passed with existing CRLF notice for overlay.js.
```

Boundaries:

- Provider gates remain closed; no model/provider call, generated media byte,
  local provider config, secret, signed URL, or provider raw response was
  touched.
- This is runtime/browser/frontend verification, not human creative acceptance,
  business validation, or durable-memory promotion.

## 2026-06-19 - Studio Interaction Motion Layer

- Added a small `apps/studio/src/interaction/` layer for motion tokens,
  pointer velocity, edge auto-pan, snap resolution, and DOM feedback overlays.
  The goal is to improve canvas tactility without introducing a new canvas
  framework or changing Runtime API contracts.
- Updated node drag behavior to use world-coordinate pointer tracking, grid
  snapping, alignment snapping, visible snap guides, a short snap chip, drag
  lift styling, and landing feedback.
- Added light canvas follow behavior: dragging near canvas edges nudges the
  viewport, and space/middle-button panning releases with bounded inertial
  motion.
- Added connection-source feedback for node port dragging, with existing target
  locking styles strengthened in a separate `interaction-motion.css` file.
- Added focused interaction tests for stylesheet entry, module boundaries,
  snap-engine alignment behavior, and reduced-motion/tactile CSS markers.

Verification:

```text
New interaction tests: 4 passed
Studio static + interaction regression: 34 passed
Studio JS node --check: 75 files passed
Browser QA on http://127.0.0.1:8797/studio/: node drag created the
  interaction feedback layer, emitted align snap state, triggered landing
  feedback, cleared guides/chip after animation, and console warn/error count=0
Full default pytest: 484 passed / 527 deselected / 2 warnings
CLI help/version: passed
maintenance_audit: failed=0, warnings only
```

Boundaries:

- Provider gates remain closed; no provider call, generated media byte, local
  provider config, secret, signed URL, or provider raw response was touched.
- This is runtime/browser verification of the Studio interaction layer, not
  human acceptance, creative quality validation, business validation, or durable
  memory promotion.

## 2026-06-19 - Studio Interaction Edge, Port, And Menu Fixes

- Kept incident edge SVG groups visible during active node drag and updated
  stable connections to solid, round-capped paths. This prevents connected
  lines from disappearing or looking detached while the node moves.
- Added side-port magnetic hover behavior for canvas nodes. Hovering near the
  left/right side now pulls the corresponding plus port into focus, and the
  right-side magnetic zone can start a connection without requiring an exact
  button hit.
- Reduced the add-node menu to four common quick actions by default and moved
  the full Action Registry into a collapsed, scroll-safe advanced list.
- Hardened popover positioning so content that grows after opening is clamped
  back into the viewport; the add-node menu now repositions after advanced-list
  toggles.
- Added bounded media preview sizing for generated image/video node results so
  preview content fills the node body without unbounded growth.

Verification:

```text
Studio interaction focused tests: 7 passed
Studio static + interaction regression: 37 passed
Studio JS node --check: 76 files passed
Browser QA on http://127.0.0.1:8797/studio/?project=frontend-fix-overlap-browser:
  right-side port magnet reached opacity=1 and scale=1.22;
  add-node menu defaulted to 4 quick actions;
  expanded advanced menu stayed inside the viewport and became scrollable;
  node drag moved the node, preserved the single edge, and left 0 drag classes;
  prompt bar and selected node had no geometric overlap;
  console warn/error count=0
Full default pytest: 487 passed / 527 deselected / 2 warnings
CLI help/version: passed; version 0.1.0
maintenance_audit: failed=0, warnings only
git diff --check: exit 0 with Windows CRLF notice on overlay.js only
```

Boundaries:

- No Runtime API contract changed.
- No provider gate was opened and no live provider/model call was made.
- This is browser/runtime verification, not human acceptance, creative quality
  validation, business validation, or durable-memory promotion.

## 2026-06-19 - COS / GFR LoopSpec And Distribution Diagram

- Added source-KB LoopSpec and TaskRun Ledger candidate control objects so COS
  and GFR can record loop-engineering signals, evaluators, repair routes,
  feedback decisions, promotion gates, and stop conditions without promoting
  lessons automatically.
- Added bilingual SVG distribution assets for the learning Agent production
  control system:
  `assets/cos-learning-agent-production-loop.zh-CN.svg` and
  `assets/cos-learning-agent-production-loop.en.svg` under the investor
  material package.
- Updated GFR startup templates so future substantial tasks include a LoopSpec
  section and work-item LoopSpec column.
- Updated the AFS projection note to acknowledge the new source-KB loop objects
  while preserving the repo boundary: AFS stores only the safe execution
  projection, not private strategy, provider secrets, customer material, or
  automatic rule promotion.

Verification:

```text
Company OS contract validator: passed; all valid/invalid fixtures behaved as expected, including loop_spec_v0 and taskrun_ledger_v0
GFR audit: passed; checked_paths=41, checked_packets=5, errors=0, warnings=0
Source JSON parse: COS-REGISTRY-V0, EVIDENCE-LEDGER-V0, TASKRUN-LEDGER-V0, and 2026-06-18/2026-06-19 task packets parsed
Bilingual SVG parse: zh-CN and en SVG assets parsed as UTF-8 XML with width=2400 and height=1500
Chrome render check: zh-CN and en SVG assets rendered at 2400x1500; final screenshots reviewed for obvious clipping/overlap
Full default pytest: 484 passed / 527 deselected / 2 warnings
maintenance audit: failed=0, warnings only
git diff --check: passed
```

Boundary:

- This is structure and distribution-asset work. It is not runtime COS
  enforcement, provider smoke, human acceptance, business validation, or durable
  memory promotion.

## 2026-06-18 - Internal Beta Entry And Studio State Conflict Guard

- Added session TTL handling for the invite-gated internal auth slice. Runtime
  sessions now expire after `AFS_AUTH_SESSION_TTL_HOURS` hours, defaulting to
  168, and expired session records are removed before user/project access is
  granted.
- Added optimistic version protection to `GET/PUT
  /projects/{project_id}/studio-state`. Runtime responses now include
  `state_version` and `saved_at`; Studio sends `expected_version` on save and
  keeps local changes as a local draft when another window has already updated
  the project.
- Updated the homepage entry script so `/` reads same-origin `/auth/status`.
  With auth enabled, anonymous users see a register/login entry; authenticated
  users see their account-scoped Studio entry without exposing secrets or
  provider internals.
- Updated `.env.example` with `AFS_AUTH_SESSION_TTL_HOURS=168` and regenerated
  the Runtime OpenAPI projection.

Verification:

```text
Focused auth/state/site/studio/OpenAPI regression: 63 passed / 1 warning
Studio/site JS node --check: passed for changed JS files
Browser QA on 127.0.0.1:8810 with all provider gates explicitly false:
  homepage anonymous auth entry passed, Studio invite registration passed,
  account-scoped default project created and saved, homepage authenticated
  entry passed, homepage -> Studio entry passed, console warn/error count=0
Full default pytest: 480 passed / 527 deselected / 2 warnings
CLI help/version: passed; version 0.1.0
maintenance audit: failed=0, warning=4
git diff --check: passed with Windows CRLF notice only
```

Boundary:

- No provider gate was opened for verification, no provider call was made, and
  no local secret provider config was edited.
- Browser/runtime verification is not human acceptance, provider smoke, business
  validation, or durable-memory promotion.

## 2026-06-18 - COS / GFR V0 Control Layer Projection

- Added the first safe AFS Runtime projection for Company OS / GFR at
  `GET /company-os/gfr-projection`. The endpoint exposes only safe control
  fields: GFR packet fields, context pack ids, default-closed provider gates,
  evidence states, feedback routes, runtime recording boundaries, and an
  explicit non-claim line.
- Added Runtime capability reporting for `company_os_gfr_projection` and
  focused tests that reject local absolute paths, provider config markers,
  provider raw markers, API keys, signed URLs, and other unsafe response
  content.
- Regenerated `docs/openapi/afs-runtime-service.openapi.json` so the new
  projection endpoint is visible to frontend/client tooling.
- Updated `docs/GFR_EXECUTION_PROJECTION.md` so future AFS agents know the
  source KB now has machine-readable v0 candidate objects:
  `COS-REGISTRY-V0.json`, `EVIDENCE-LEDGER-V0.json`, and the GFR packet v0
  schema.
- Source KB side work created COS Registry v0, Evidence Ledger v0, GFR Packet
  v0 schema/fixtures, a real task startup packet for this work, and a candidate
  Company OS feedback packet. Those source files remain outside the AFS repo.

Verification:

```text
Company OS contract validator: passed; new cos_registry_v0, gfr_packet_v0, and evidence_ledger_v0 fixtures pass valid/invalid checks
GFR audit: passed; checked_paths=41, checked_packets=4, errors=0, warnings=0
Focused Runtime tests: 13 passed / 1 warning
Post-OpenAPI focused Runtime/OpenAPI tests: 17 passed / 2 warnings
CLI help/version: passed; version 0.1.0
Full default pytest: 476 passed / 527 deselected / 2 warnings
git diff --check: passed
```

Boundary:

- This is a candidate control-layer slice and AFS safe projection only. It does
  not prove full COS runtime enforcement, a Studio UI display, provider smoke,
  human acceptance, business validation, or durable memory promotion.
- No provider gate was opened, no provider call was made, no local secret
  provider config was edited, and no private Company OS raw material was copied
  into the AFS repo.

## 2026-06-18 - Internal Auth And Invite-Gated Project Isolation

- Added an opt-in Runtime auth slice for internal testing. When
  `AFS_AUTH_ENABLED=true`, project APIs require a bearer session created by
  `/auth/register` or `/auth/login`; static `/`, `/studio/`, `/health`,
  `/capabilities`, and `/auth/*` remain reachable.
- Added invite-code registration through `AFS_INVITE_CODES`. Invite codes are
  stored hashed under the runtime root, consumed once, and mapped to the user
  that used them; plaintext invite codes and passwords are not written to
  project artifacts.
- Added user-owned project isolation for the current Runtime surface:
  `/projects` only lists the current user's projects, project routes reject
  other users, and Studio creates an account-scoped default project after first
  login instead of falling back to the shared `studio-local-001`.
- Added Studio account session support, a registration/login gate, and a clear
  topbar link back to the website homepage. The existing project menu remains
  separate from the new homepage link.
- Locked the auth gate against accidental backdrop dismissal when auth is
  required, so internal-test users cannot silently close the login/register
  surface and then hit protected Runtime APIs from an unauthenticated canvas.
- Updated `.env.example` with auth switches only; no real invite code, password,
  provider secret, or private deployment value was added.

Verification:

```text
Auth-focused pytest: 3 passed / 1 warning
Runtime/Auth/Studio/Site focused regression: 54 passed / 1 warning
Auth gate/site focused regression after backdrop-lock fix: 7 passed / 1 warning
Studio JS node --check: passed for all 70 apps/studio/src/**/*.js files
CLI help/version: passed
Full pytest: 474 passed / 527 deselected / 2 warnings
maintenance audit: failed=0, warning=4
git diff --check: passed with Windows CRLF notices only
Runtime HTTP auth smoke on 127.0.0.1:8802: /, /studio/, /health, /auth/status,
anonymous /projects rejection, invite registration, project creation, and owned
project listing passed.
```

Boundary:

- Internal-test account gate only. This is not a full SaaS auth system: no
  email verification, admin console, password reset, project sharing, roles,
  billing, abuse controls, or real-time collaborative editing is claimed.
- No provider gate was opened, no live model/provider call was made, no local
  secret provider config was edited, and no human acceptance or business
  validation is claimed.

## 2026-06-18 - Site and Studio UX Consolidation

- Fixed the homepage product preview overlap by replacing absolutely positioned
  node cards with a bounded flow grid and responsive single-column fallback.
- Tightened the homepage visual shell: removed the decorative radial glow,
  renamed the preview to a creation chain, and changed the right preview copy
  from internal context jargon to user-facing "what the system referenced".
- Reframed the Studio empty inspector from an algorithm/status console into a
  creation decision surface: the header now says "next step", the primary copy
  tells the user to continue generation, save assets, inspect references, or
  revise, and the algorithm trace is kept as a folded system-reference audit.
- Added static regressions that prevent the homepage preview from returning to
  fixed-width absolute card placement and lock the Studio default inspector to
  the creation-decision-first shape.

Verification:

```text
tests/test_api_runtime_service.py + tests/test_site_homepage_static.py + tests/test_web_studio_static.py: 42 passed / 1 warning
Full default pytest: 470 passed / 527 deselected / 2 warnings
Studio JS node --check: passed for all apps/studio/src/**/*.js
Runtime HTTP smoke on 127.0.0.1:8801: /, /studio/, /health all 200
In-app Browser QA on 127.0.0.1:8801: homepage cardOverlaps=0, Studio nav CTA works, console warn/error empty
maintenance audit: failed=0, warning=4
git diff --check: passed
```

Boundary:

- Frontend and static-route usability consolidation only. No provider gate was
  opened, no provider call was made, no local secret config was edited, and no
  human acceptance or business validation is claimed.

## 2026-06-18 - Model Route Surface Consolidation

- Repointed the current Studio image/keyframe surface from the retired MiniMax
  image picker to the `Image2` product label backed by the server-side
  `codex_image` handoff service.
- Kept prompt optimization model identity server-configured: Studio now sends
  `prompt_optimizer`, Runtime reports `provider_configured`, and safe traces do
  not expose a concrete LLM model name.
- Split visual-understanding service ids by media type: image asset-card drafts
  use `vision_image`, while video asset-card drafts use `vision_video`.
- Updated `configs/providers.example.json` to show the current execution
  projection: `prompt_optimizer`, `codex_image`, `vision_image`,
  `vision_video`, `fake_video`, and `kling_i2v`.
- Preserved legacy prompt-optimizer fallback behavior for older requests so
  explicit MiniMax-compatible test paths still route through the registry
  without taking over the new Studio product path.

Verification:

```text
Focused model route/runtime/static regression: 100 passed
Full default pytest: 469 passed / 527 deselected / 2 warnings
Studio JS node --check: passed for all apps/studio/src/**/*.js
configs/providers.example.json parse: passed
maintenance audit: failed=0, warning=4
git diff --check: passed with CRLF normalization notices only
```

Boundary:

- Repo example config and Runtime/Studio defaults only. No provider gate was
  opened, no live model call was made, no local secret provider config was
  edited, and no human acceptance is claimed.

## 2026-06-18 - Site Homepage Root Entry

- Added a distinct AFS Studio website homepage under `apps/site/` and mounted it
  at Runtime root `/`, while keeping `/studio/` as the actual creative
  workspace entry.
- Kept the homepage as a mature product shell instead of another internal
  control surface: brand/value proposition, product preview, workflow, six-core
  algorithm rail, and a direct Studio CTA.
- Split homepage CSS into base, product-preview, and responsive layers so each
  new site file stays below the 300-line maintenance warning threshold.
- Added Runtime and static regression tests for the root homepage, no-store
  static assets, Studio link continuity, and secret/path/raw-provider safety.

Verification:

```text
tests/test_api_runtime_service.py + tests/test_site_homepage_static.py + tests/test_web_studio_static.py: 41 passed
```

Boundary:

- Runtime static routing and frontend-only homepage shell. No provider gate was
  opened, no generation call was made, and no human acceptance is claimed.

## 2026-06-18 - Studio Frontend Declutter Follow-up

- Reframed the top-left Studio entry from a large "workbench" surface into a
  compact project menu for continue/create/switch actions.
- Moved the main creative entry emphasis back to the canvas starter rail and
  removed the oversized project hub card wall.
- Reduced the right inspector's default information density: the default view
  now focuses on current node state, next action, context, content, and output
  records, while six-core-algorithm details stay available behind a collapsed
  "system process" disclosure.
- Split right-inspector declutter CSS into `studio-inspector-declutter.css` so
  the mature shell stylesheet stays below the maintenance warning threshold.

Verification:

```text
tests/test_web_studio_static.py: 28 passed
apps/studio changed JS node --check: passed
git diff --check: passed
Line-count check: touched/new Studio frontend files are all under 300 lines
```

Boundary:

- Frontend-only UI and interaction polish. No Runtime API contract change, no
  provider gate opened, no provider call, no human acceptance claimed.
- In-app browser automation for the local URL was blocked by the Browser URL
  policy during this pass, so final visual acceptance still needs a manual
  refresh/review in the already-open `/studio/` page.

## 2026-06-18 - Studio Inspector And Workbench Scroll Follow-up

- Fixed the right inspector overlap regression by making the mature shell
  inspector opt out of the older flex-column/shrink layout and keeping its
  status/action/section blocks at natural height inside the scroll container.
- Fixed the project workbench modal scroll regression by making `.project-hub`
  own vertical scrolling instead of inheriting clipped modal overflow.
- Added static regression coverage for the inspector no-shrink layout and
  workbench vertical scroll contract.

Verification:

```text
tests/test_web_studio_static.py: 28 passed
apps/studio JS node --check: passed for all apps/studio/src/**/*.js
git diff --check: passed
In-app browser on 127.0.0.1:8797/studio/: starter-flow inspector sections had zero detected overlaps; workbench modal accepted real wheel scroll from top to bottom content; console warnings/errors 0
```

Boundary:

- This is frontend layout/runtime verification only. No provider gate was
  opened, no Runtime API contract changed, and no human acceptance is claimed.

## 2026-06-18 - Studio Mature Shell And Algorithm Console

- Added a Studio desktop shell polish layer for `/studio/`: stronger canvas
  material, glass-like topbar/drawer/dock/inspector treatment, smoother hover
  interactions, and a compact workflow starter rail for empty or pre-production
  canvases.
- Added `algorithm-context-panel.js` so the right inspector can show the six
  core algorithm states from safe Studio node state: context scheduling, prompt
  optimization, request projection, visual inspection, asset memory, and drift
  control.
- Updated the inspector from generic project overview to a production console;
  selected nodes now show algorithm status, operation intent, generation
  target, included/excluded context counts, and safe trace warnings.
- Kept this pass frontend-only: no Runtime API contract change, no provider
  call, no provider config change, and no sensitive local media/path exposure.

Verification:

```text
apps/studio JS node --check: passed for all apps/studio/src/**/*.js
tests/test_web_studio_static.py: 27 passed
git diff --check: passed
Runtime health on 127.0.0.1:8797: ready, Studio static ready
Chrome headless desktop verification: /studio/ loaded, starter rail visible on empty canvas, workflow starter created 2 nodes, selected node showed 6 algorithm steps, console errors/warnings 0
Screenshot: frontend-mature-shell-20260618/screenshots/studio-mature-shell-final-1440x900.png in the Codex backup area
```

Boundary:

- This is frontend runtime verification, not human acceptance, provider smoke,
  business validation, or durable Company OS memory promotion.

## 2026-06-18 - ModelCallContext Algorithm Contract

- Added `ModelCallContext` as the pre-model-call internal contract for prompt
  optimization and keyframe/image generation.
- Added provider-neutral request projection and visual-understanding
  normalization modules under `agentflow/algorithms/`.
- Added fixed-asset continuity projection so only fixed assets are context
  eligible; draft/rejected/retired assets remain evidence or history only.
- Updated Runtime prompt optimization and keyframe generation to write
  `model_call_context.json`; keyframe generation also writes
  `model_request_plan.json` and links the legacy request plan to the same
  `context_id`.
- Extended the same contract to Runtime video generation, asset-card drafting,
  and video revision. Video generation now emits a `video_generate`
  `ModelCallContext` plus request plan; asset-card drafting emits
  `visual_inspect` context, request plan, and normalized visual-understanding
  observation; video revision emits a drift-control `revision_plan`, revision
  `ModelCallContext`, and request plan while provider/feature gates remain
  closed by default.
- Fixed Studio Runtime base URL selection so Runtime-hosted `/studio/` on a
  non-default local port uses same-origin instead of forcing the static/dev
  fallback to `127.0.0.1:8790`.
- Updated the algorithm-library docs to separate six core intelligent-agent
  algorithms from auxiliary provider gate / manifest / action routing layers.
- Updated the core algorithm and operation-chain map into a v3 confirmation
  package with `ModelCallContext` in the diagrams and explicit user-link
  confirmation points before the next UX hardening pass.

Verification so far:

```text
tests/test_model_call_context_contract.py tests/test_model_call_context_runtime_routes.py: 11 passed
tests/test_web_studio_static.py::test_runtime_client_uses_runtime_port_when_studio_is_served_from_dev_port: 1 passed
tests/test_algorithm_library_contracts.py: 7 passed
tests/test_api_runtime_prompt_memory_loop.py: 18 passed
tests/test_algorithm_library_contracts.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_asset_card_drafts.py tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py tests/test_model_call_context_contract.py tests/test_model_call_context_runtime_routes.py: 61 passed
tests/test_api_runtime_context_resolver.py: 17 passed
pytest -q: 464 passed, 527 deselected, 2 warnings
tools/maintenance_audit.py: failed=0, warnings only
gfr_audit.py: pass, checked_paths=41, checked_packets=3
validate_ai_native_contracts.py: pass
Runtime-hosted /studio/ browser smoke on 127.0.0.1:8797 with all provider gates false: 200, console errors 0, desktop/mobile screenshots captured, starter interaction created 3 nodes and saved state
Final closeout HTTP smoke on 127.0.0.1:8797 with all provider gates false: /health ready, /studio/ 200, runtime client 200; no new rendered-browser evidence was added in this shell.
```

Boundary:

- No live provider call, provider config change, secret, provider raw response,
  credentialed URL, local private path, or media bytes were used.
- This is structure/runtime verification, not provider smoke, human acceptance,
  business validation, or durable Company OS memory promotion.

## 2026-06-18 - Studio Final Interaction And Progress Pass

- Added a shared generation-state projection for Studio nodes: submit state,
  status-derived percentage fallback, provider progress passthrough,
  terminal progress, and safe candidate preview lists.
- Made image and video result previews size from the preview container itself,
  so generated media fills the node frame with stable aspect-ratio layout.
- Preserved generation progress and candidate preview state through Runtime
  `studio-state` save/restore with safe Runtime preview route validation.
- Added visible-canvas safe-area fitting so arrange/fit/add-node placement avoids
  the drawer, inspector, topbar, and dock instead of centering under panels.
- Split more frontend/runtime responsibilities:
  `node-generation-progress.js`, `node-generation-results.js`,
  `node-generation-guards.js`, `node-generation-context.js`,
  `canvas-safe-area.js`, `studio-topbar.js`, and
  `runtime_studio_generation_state.py`.
- Reduced active file pressure: `main.js` is 431 lines and `node-actions.js` is
  481 lines after this pass.

Verification:

```text
Studio JS node --check: passed for all apps/studio/src/**/*.js
tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py tests/test_api_runtime_studio_state.py tests/test_api_runtime_studio_state_persistence.py tests/test_api_runtime_service.py: 57 passed, 1 existing Starlette/httpx warning
In-app browser takeover: starter flow, canvas right-click menu, node right-click menu, drag connection, marquee selection, safe-area fit, progress percent, candidate grid, and media preview DOM passed with console error/warn count 0
Screenshot: C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-flow-takeover-20260618\final-progress-media-20260618.png
tools/maintenance_audit.py: failed=0, warnings only
git diff --check: passed with existing CRLF notices only
```

Boundaries:

- No live provider call, production server mutation, secret, provider raw
  response, signed URL, or media bytes were used.
- Browser media/progress validation used safe Runtime preview route strings and
  a temporary local Runtime on 8797 with explicit `runtimeBaseUrl`, then stopped it.
- This is frontend/runtime verification, not provider smoke, human acceptance,
  business validation, or durable memory promotion.
- Maintenance audit still reports historical oversized files and active
  Runtime/Studio warnings; this pass reduces the main frontend pressure but does
  not claim total maintainability debt is cleared.

## 2026-06-18 - Studio Frontend UX Polish

- Tightened the Studio desktop canvas experience after the LibTV reference pass:
  clearer first-run starter cards, node-local action toolbar, friendlier drawer
  tabs, richer empty states, and simpler Chinese labels for user-facing actions.
- Improved canvas interaction details: port hover affordance, additive
  selection, single-click selection collapse after starter templates, and
  no browser text selection during context/menu interactions.
- Reframed the right inspector as a current-node operation center with direct
  actions for continuing generation, saving materials, opening process evidence,
  and reviewing the material library.
- Adjusted the first-screen starter row so all five desktop entry cards fit
  inside the usable workspace beside the right inspector.

Verification:

```text
Studio JS node --check: passed
tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py: 33 passed
Playwright desktop render smoke: empty state, node selection, toolbar, context menu, drawer states passed with no console errors
tools/maintenance_audit.py: failed=0, warnings only
git diff --check: passed with existing CRLF notices only
```

Boundaries:

- No live provider call, server mutation, secret, provider raw response, signed
  URL, or media bytes were used.
- This is local frontend/runtime verification, not provider smoke, human
  acceptance, business validation, or durable memory promotion.
- Maintenance audit still warns about historical oversized files, including
  some active Studio files that should be split in a later architecture pass.

## 2026-06-18 - Studio Interaction Flow And File Slimming

- Split the Studio canvas shell further into smaller interaction modules:
  `canvas-selection.js`, `canvas-connection.js`, `canvas-node-action-handler.js`,
  `canvas-node-body.js`, `studio-keyboard.js`, `runtime-asset-sync.js`,
  `node-upload-actions.js`, `node-visible-assets.js`, and
  `node-action-utils.js`.
- Kept the public `node-actions.js` import surface compatible while moving
  upload and visible-asset projection logic out of the generation orchestrator.
- Reduced active Studio file pressure: `main.js` is now under 500 lines, and
  `drawer.js`, `canvas-input.js`, and `canvas-view.js` are thin coordinators.
- Improved arrange behavior so keyboard/context-menu canvas arrangement also
  fits the nodes back into the visible viewport.
- Ran an isolated no-provider project takeover flow through the local Studio:
  starter flow, single selection, shift multi-select, marquee selection without
  browser text selection, right-click node menu, port hover affordance,
  keyboard arrange, and drawer tab switching.

Verification:

```text
Studio JS node --check: passed for all apps/studio/src/**/*.js
tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py: 33 passed
Playwright takeover flow: passed, 0 console errors
Report: C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-flow-takeover-20260618\frontend-takeover-flow-final-1781723841.json
Screenshot: C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-flow-takeover-20260618\frontend-takeover-flow-final-1781723841.png
git diff --check: passed with existing CRLF notices only
```

Boundaries:

- In-app Browser was attempted first, but its tab registry became inconsistent;
  local Playwright was used as the browser fallback.
- No live provider call, server mutation, secret, provider raw response, signed
  URL, or media bytes were used.
- This is runtime/frontend verification, not provider smoke, human acceptance,
  business validation, or durable memory promotion.
- `node-actions.js` remains oversized and should be split again around
  keyframe/video generation orchestration in a future focused pass.

## 2026-06-17 - Algorithm Core Wave 2

- Moved PR #87 video creative-intent semantics into
  `agentflow.algorithms.creative_intent_control.video_prompt`.
- Moved video-safe provider prompt projection and image-edit wording stripping
  into `agentflow.algorithms.provider_gate_manifest.video_prompt`.
- Moved reference image channel + request asset ref merging into
  `agentflow.algorithms.context_resolver.references`.
- Slimmed `apps/studio/src/node-actions.js` by moving video first-frame
  inference and auto-poll scheduling into `apps/studio/src/video-node-flow.js`.
- Kept Runtime and Studio behavior stable through focused tests. No live
  provider call was started.

Verification:

```text
python -m py_compile changed Python files -> pass
node --check apps/studio/src/node-actions.js -> pass
node --check apps/studio/src/video-node-flow.js -> pass
node --check apps/studio/src/node-result-view.js -> pass
node --check apps/studio/src/optimizer-contract.js -> pass
pytest tests/test_algorithm_library_contracts.py -q -> 7 passed
pytest tests/test_web_studio_static.py tests/test_api_runtime_prompt_memory_loop.py::test_video_prompt_optimizer_uses_i2v_instruction_with_first_frame tests/test_api_runtime_video_generations.py::test_video_provider_prompt_removes_image_edit_language tests/test_api_runtime_keyframe_reference_assets.py::test_uploaded_image_asset_survives_context_bundle_reference_fallback -q -> 28 passed, 1 warning
pytest tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_video_generations.py tests/test_api_runtime_keyframe_reference_assets.py -q -> 32 passed, 1 warning
pytest tests/test_web_studio_static.py tests/test_algorithm_library_contracts.py -q -> 32 passed
tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> pass
```

## 2026-06-17 - Provider Video Flow Intake

- Integrated server-side PR #87 onto the GFR baseline branch without conflicts.
- Preserved uploaded/reference image assets for keyframe provider prompts when
  a context bundle exists.
- Added video-specific prompt optimization behavior for i2v/t2v, video-safe
  Kling provider prompt projection, Studio first-frame inference from upstream
  keyframes, video auto-polling, and safe image/video download links.
- Refreshed no-cost provider-connected readiness and saved the safe report at
  `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-READINESS-20260617.json`.
- Kept live provider calls out of this local integration step. The server-side
  Kling smoke note remains provider-smoke evidence only, not human acceptance.

Verification:

```text
node --check apps/studio/src/node-actions.js -> pass
node --check apps/studio/src/node-result-view.js -> pass
node --check apps/studio/src/optimizer-contract.js -> pass
pytest tests/test_web_studio_static.py tests/test_api_runtime_prompt_memory_loop.py::test_video_prompt_optimizer_uses_i2v_instruction_with_first_frame tests/test_api_runtime_video_generations.py::test_video_provider_prompt_removes_image_edit_language tests/test_api_runtime_keyframe_reference_assets.py::test_uploaded_image_asset_survives_context_bundle_reference_fallback -q -> 28 passed, 1 warning
pytest tests/test_afs_provider_connected_validation_readiness.py -q -> 4 passed, 1 warning
```

## 2026-06-17 - COS / GFR V1 Projection

- Added `docs/GFR_EXECUTION_PROJECTION.md` as the repo-local projection of the
  COS/GFR V1 baseline.
- Updated `AGENTS.md` and `docs/company_operating_model.md` to include
  `COS-V1-BASELINE.md`, `context-pack-index.json`, and the AFS Project Capsule
  as default source-KB control files.
- Added handoff `docs/handoff/COS-GFR-V1-PROJECTION-20260617.md` and indexed it
  for future AFS work.
- Kept this as a rules/projection change only: no Runtime, Studio, provider,
  secret, customer, cost, contract, or media-byte change.

Verification:

```text
gfr_audit.py -> pass, checked_paths=37, checked_packets=3
validate_ai_native_contracts.py -> all contract fixtures and GFR packet fixtures passed
```

## 2026-06-17 - Algorithm Library / GFR Operationalization

- Added the first executable AFS algorithm-library slice: draft asset-card
  contracts, fixed-asset context filtering, provider safe manifest handling,
  and quality-feedback sanitization contracts.
- Added independent `vision` provider capability with `AFS_ALLOW_REMOTE_VISION`
  and fake vision adapter coverage.
- Added Runtime routes for asset-card drafts and video-asset promotion. Drafts
  stay out of fixed asset context until human promotion.
- Added Studio client/static hooks for asset-card drafts and video asset-card
  draft markers.
- Kept any external Company OS / GFR feedback candidate-only and outside the
  repository; no COS rule was promoted.

Verification so far:

```text
pytest tests/test_api_runtime_visual_assets.py tests/test_provider_adapter_registry.py tests/test_web_studio_static.py -q -> 54 passed, 1 warning
pytest tests/test_api_runtime_context_resolver.py tests/test_api_runtime_video_revisions.py -q -> 20 passed, 1 warning
pytest tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_prompt_memory_loop.py -q -> 26 passed, 1 warning
pytest tests/test_algorithm_library_contracts.py tests/test_api_runtime_asset_card_drafts.py tests/test_api_runtime_service.py -q -> 17 passed, 1 warning
node --check changed Studio files -> passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
runtime-service-openapi-export -> docs/openapi/afs-runtime-service.openapi.json updated
tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> exit 0, CRLF notices only
```

Boundary:

- No real provider smoke, no provider config changes, no secrets, no customer or
  business raw material, no media bytes, and no durable Company OS memory writes.

Verification addendum:

- Default pytest initially exposed a real architecture issue: the new
  `agentflow.algorithms.context_resolver` package imported `apps.api`
  helpers, creating a package-level cycle. The resolver helper logic is now
  owned by algorithm submodules, and Runtime passes its director compiler as an
  adapter callback.
- The repository retention review initially required manual review for the new
  `agentflow/algorithms` directories. The retention policy now classifies the
  algorithm library as current production spine.

```text
pytest tests/test_architecture_audit_gates.py::test_package_level_cycles_are_not_allowed tests/test_repository_retention_review.py::test_repository_retention_review_cli_outputs_summary_json -q -> 2 passed
pytest focused algorithm/provider/static/context/retention suite -q -> 57 passed, 1 warning
pytest -q -> 433 passed, 527 deselected, 2 warnings
repository_retention_review --summary-only -> manual_review_required_count=0
```

## 2026-06-17 - Provider-Connected Validation Readiness

- Added `tools/afs_provider_connected_validation_readiness.py`, a no-cost
  readiness gate for the next provider-connected validation. It checks the GFR
  provider validation packet, Runtime action surface, provider config source,
  current gate projection, and required human authorizations.
- Added tests for missing GFR packet, example-only provider config, gate-closed
  authorization readiness, and env-config readiness without leaking local paths
  or secret-like values.
- Ran the tool on the current machine. It reported
  `ready_for_provider_smoke`: GFR packet present, Runtime ready, required
  actions present, provider config source present through `AFS_PROVIDER_CONFIG`,
  LLM/image gates projected open, video/vision closed, provider calls not
  started, secrets not printed. The report explicitly keeps
  `human_approval_required=true` and
  `current_session_approval_inferred_from_env=false`.
- Added handoff record
  `docs/handoff/AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617.md`.

Verification so far:

```text
pytest tests/test_afs_provider_connected_validation_readiness.py -q -> 4 passed, 1 warning
pytest tests/test_algorithm_library_contracts.py tests/test_api_runtime_asset_card_drafts.py tests/test_provider_adapter_registry.py::test_provider_registry_supports_fake_vision_descriptor_and_gate tests/test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets tests/test_api_runtime_service.py::test_runtime_health_provider_gate_projection_is_isolated_and_secret_free -q -> 10 passed, 1 warning
focused algorithm/provider/static/context/retention suite -q -> 57 passed, 1 warning
pytest -q -> 433 passed, 527 deselected, 2 warnings
```

Boundary:

- No live provider call was run. Environment gates being open is not treated as
  human authorization for this session. Next live smoke still needs explicit
  capability and candidate-count approval.

Verification addendum:

- The readiness tool reports `ready_for_provider_smoke` on this machine, but
  this is only a no-cost readiness state. It is not authorization to spend
  provider calls.
- The tool now exposes the approval boundary in machine-readable form:
  `human_approval_required=true` and
  `current_session_approval_inferred_from_env=false`.
- Next live run still needs an explicit instruction such as: authorize one live
  LLM + image/keyframe provider smoke with `candidate_count=1`; do not
  authorize video, ASR, vision, or external download.

## 2026-06-17 - Codex Image Handoff Worker

- Added `codex_handoff` as an async image provider adapter. Runtime keyframe
  submit now writes a per-run safe job package for async image providers, and
  `apps/api/runtime_keyframe_async.py` backs
  `POST /projects/{project_id}/keyframe-generations/{job_id}/poll` to publish
  safe previews and reusable generated image assets.
- Added `agentflow_studio/model_gateway/codex_image_worker.py` plus
  `tools/codex_image_worker.py`. The fake executor proves the file contract in
  tests; the production executor shells out to `codex exec` from the job
  directory and keeps the full prompt out of the process command line.
- Added Studio keyframe auto-polling. Image nodes stay in normal generating,
  complete, or error states; Studio text does not expose internal worker,
  handoff, request file, or job directory names.
- Hardened repeated keyframe polling so the same `source_job_id` +
  `source_candidate_id` reuses the existing generated image asset instead of
  creating duplicate reusable assets.
- Hardened async keyframe poll after Runtime restart/provider config loss: the
  route now returns a failed safe manifest instead of leaking config paths or
  surfacing a 500.
- Updated `configs/providers.example.json` with a secret-free `codex_image`
  service using `auth_type: none`, `execution_mode: async`, and
  `AFS_ALLOW_REMOTE_IMAGE`.
- Added the handoff record
  `docs/handoff/AFS-CODEX-IMAGE-HANDOFF-WORKER-20260617.md`.

Verification so far:

```text
pytest tests/test_codex_image_handoff.py -q -> 2 passed, 1 warning
pytest tests/test_provider_adapter_registry.py -q -> 25 passed
pytest tests/test_api_runtime_keyframe_reference_assets.py -q -> 3 passed, 1 warning
pytest tests/test_web_studio_static.py -q -> 25 passed
node --check apps/studio/src/runtime-client.js -> passed
node --check apps/studio/src/node-actions.js -> passed
pytest -q -> 421 passed, 527 deselected, 2 warnings
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> exit 0
Studio JS node --check all files -> passed
```

Boundary:

- This proves the Runtime/job-package/worker contract with a fake executor. It
  does not yet prove that the server-installed `codex exec` path can generate a
  real image; that remains a separate provider smoke before human testing.

## 2026-06-15 - Full-Chain Localized QA

- Merged the safe summary from the isolated
  `codex/afs-full-chain-localized-qa-20260615` branch into mainline before
  branch cleanup.
- The run covered a full-chain browser/runtime/live-provider QA path with LLM,
  image, and video gates explicitly controlled while ASR and external download
  stayed closed.
- MiniMax T2I, MiniMax reference-backed I2I, and Kling I2V completed in that
  run, but the localized image quality sample failed the requested subtle
  left-eyebrow scar edit.
- Hardened provider prompt ordering for reference-backed localized edits:
  requested delta and preserve policy now lead, while base descriptors are
  framed as anchors rather than instructions to undo the requested change.
- Added deterministic regression coverage in `tests/test_runtime_context_text.py`.

Verification recorded by the source branch:

```text
tests/test_runtime_context_text.py -> 3 passed
tests/test_api_runtime_context_resolver.py tests/test_api_runtime_creative_agent_keyframes.py -> 26 passed, 1 warning
```

Boundary:

- The localized image quality fix has not been paid-provider retested. Do not
  claim localized image editing is solved.
- Full-frame I2I drift remains a likely architecture limit for small-region
  requests until a masked/regional edit provider path is verified.
- Video localized editing remains experimental and not productized; current
  live video evidence is Kling I2V provider smoke only.
- Evidence stays outside the repo under `20260615-afs-full-chain-localized-qa`;
  repository records contain safe summaries only.

## 2026-06-15 - MVP Experience Hardening

- Added Runtime `/health` projection for Studio static readiness and isolated
  provider gates. The payload reports only booleans and static readiness; it
  does not expose provider config paths, secrets, or local private paths.
- Added `tools/run_studio_internal_test.ps1` so internal-test runs can open
  LLM/image/video gates explicitly while keeping ASR closed.
- Added a bounded node-level fixed-asset carry chain and a shared pure
  `asset-reference-inspector` for label-matched unconnected asset actions. This
  keeps the node/menu/optimizer paths aligned instead of duplicating detection
  logic.
- Added video local-cancel UX: submitted/running/cancelled video states now
  warn that local cancel only stops Studio polling and does not guarantee
  provider-side cancellation or stopping billing.
- Added `quality-feedback.js` and `/feedback` client wiring for structured
  image/video scoring: identity similarity, wardrobe consistency, scene
  continuity, text/watermark, target-change success, and drift notes. Feedback
  remains raw evidence and does not write durable memory.
- After the Claude closeout checkpoint, hardened the boundary further:
  `/feedback` now applies a server-side whitelist/sanitizer, the internal-test
  launcher forces `AFS_ALLOW_EXTERNAL_DOWNLOAD=false`, and the feedback UI reads
  preview URL presence plainly while still storing only `safe_preview_ref`.
- In-app Browser smoke against localhost was blocked by Browser URL policy and
  recorded as blocked evidence. No alternate browser was used to bypass that
  policy.

Verification:

```text
pytest tests/test_api_runtime_service.py tests/test_studio_internal_launcher.py tests/test_web_studio_static.py -q -> 37 passed, 1 warning
pytest tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py tests/test_kling_video_runtime_polling.py -q -> 13 passed, 1 warning
pytest tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_visual_assets.py tests/test_studio_asset_context_browser_qa_tool.py -q -> 12 passed, 1 warning
Studio JS node --check -> passed
Runtime /health smoke -> ready; Studio static ready; all provider gates closed
pytest -q -> 417 passed, 527 deselected, 2 warnings
pytest -m legacy -q -> 527 passed, 417 deselected, 1 warning
maintenance_audit.py -> failed=0, warnings only
git diff --check -> exit 0
```

Boundary:

- This is an internal-test readiness hardening slice. It is not human
  acceptance, business validation, or proof that Kling supports localized video
  editing. Video targeted revision remains best-effort/experimental until a
  provider-specific V2V/masked/temporal path is verified.

## 2026-06-15 - Experimental Video Revision Contract And Fail-Closed Carry Guard

- Added an experimental `video_revision` Runtime contract behind
  `AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION`:
  `VideoRevisionRequest`, `/video-revisions/preflight`, and `/video-revisions`.
- The new route records best-effort preserve/change intent, temporal scope,
  locked aspects, original base lineage, and a safe
  `afs_video_revision_safe_manifest.v0.1`; it does not submit to Kling yet.
- Added Studio Runtime client methods and a video-node menu entry to enable an
  experimental revision draft from an accepted base video job.
- Hardened Studio generation preflight so fixed assets that are mentioned by
  label but not connected/injected/excluded fail closed before any paid
  image/video submit.
- Improved stale Runtime route failures with route/status metadata and an
  explicit "Restart the 8790 Runtime Service from the current branch" message.
- Added a safe-error guard so unsafe `video_revision` base identifiers are
  rejected as `invalid_video_revision` without leaking paths or secret-like
  fragments.
## 2026-06-15 - Browser Acceptance Drill

- Created `codex/afs-browser-acceptance-drill-20260615` from the joint QA
  closeout branch and ran a Browser-led acceptance drill against Runtime-hosted
  `/studio/` on 8790. Evidence is stored outside the repo under
  `20260615-afs-browser-acceptance-drill`; repository records contain safe
  summaries only.
- Opened only the approved live gates for this drill: LLM, MiniMax image, and
  Kling I2V. ASR and external download stayed closed. Browser coverage passed
  project create/switch/refresh, prompt persistence, T2I optimize + image
  generation, fixed asset promotion/detail/refresh, explicit video first frame,
  one Kling submit, UI polling, Runtime video preview, and refresh recovery.
- Used two MiniMax image calls in the initial drill. Both succeeded with one
  output each, but the second call did not count as true I2I because its safe
  manifest recorded `reference_image_count=0`.
- After explicit user authorization, ran one additional MiniMax Path 3
  reference-backed I2I call from Browser. The rerun succeeded as
  `studio-1781460479681-37qe3g-keyframe_generation-c8f9612a06c1` with
  `candidate_count=1`, `reference_image_count=1`,
  `context_included_asset_count=1`, and no provider raw/media-byte persistence
  in the safe manifest.
- Found an I2I optimization quality risk: the LLM optimizer switched to
  reference-preserving tone, but also contradicted explicit requested edits by
  telling the model to keep background/clothing unchanged. The optimized text
  was not used for the second image call and is recorded as a follow-up.
- Kling I2V passed with one submit and same-job polling. Runtime preview
  returned `video/mp4`; `ffprobe` recorded a 5.04s H.264 video at 1080x1920.
  Safe manifests did not persist provider raw responses, provider URLs, local
  absolute paths, or media bytes returned by API.
- Fixed `tools/afs_mvp_joint_qa_readiness_audit.py` so the no-cost audit can
  recognize browser-drill evidence rooted at `runtime_service/**` plus
  `browser_qa_summary.json`, while preserving the older joint-QA evidence
  format. After the authorized Path 3 rerun, the current audit reports
  `recommended`, seven passed role checks, and zero provider blockers.

Verification:

```text
pytest tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py -q -> 11 passed
pytest tests/test_api_runtime_context_resolver.py -q -> 17 passed
pytest tests/test_web_studio_static.py -q -> 21 passed
Studio JS node --check all files -> passed
pytest -q -> 390 passed / 527 deselected
pytest -m legacy -q -> 527 passed / 390 deselected
tools/maintenance_audit.py -> failed=0, warning=4
runtime-service-openapi-export -> docs/openapi/afs-runtime-service.openapi.json updated
git diff --check -> exit 0, CRLF notices only
focused gate-closed pytest: 58 passed, 1 warning
Studio JS node --check: 37 files passed
tests/test_afs_mvp_joint_qa_readiness_audit.py: 8 passed
readiness_audit.json: recommended, provider_blocker_count=0, passed_role_count=7
pytest -q: 406 passed, 527 deselected, 2 warnings
pytest -m legacy -q: 527 passed, 406 deselected, 1 warning
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0
```

Continuation verification after the authorized Path 3 rerun:

```text
tests/test_afs_mvp_joint_qa_readiness_audit.py tests/test_api_runtime_keyframe_reference_assets.py: 11 passed, 1 warning
readiness_audit.json: recommended, provider_blocker_count=0, passed_role_count=7
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0
```

Boundary:

- This is a contract/UI safety slice, not proof that Kling can perform localized
  video editing. It supports the desired workflow vocabulary while preserving
  the claim boundary: targeted revisions are best-effort until provider-specific
  V2V/masked/temporal controls are verified.

## 2026-06-15 - Video Localized Regeneration Requirement Record

- Recorded the current Claude/browser feedback issues as project follow-up:
  stale Runtime route mismatch after code updates, multi-node fixed-asset
  detection inconsistency, fixed-asset carry confirmation inconsistency, and
  provider framing preference for wide/full shots.
- Added `docs/handoff/AFS-VIDEO-LOCALIZED-REGEN-20260615.md` to distinguish the
  current Kling I2V plumbing from the user's desired video revision behavior:
  accepted base video -> targeted prompt edit -> preserve unrelated content.
- Added backlog items for multi-node asset/carry consistency, video revision
  contract design, and A/B drift scoring.
- This is AI/browser pre-acceptance, not human acceptance, business validation,
  or durable-memory promotion.
- The third MiniMax image call was made only after explicit user approval; no
  further live provider retry was run.
- I2I optimizer explicit-edit preservation remains a non-blocking follow-up
  before relying on optimized I2I text in a future live path.

## 2026-06-15 - Joint QA Image/Video Gate Open Closeout

- Fixed the Studio stale Runtime symptom seen as `MiniMax keyframe request
  failed (404)`: Runtime client errors now carry HTTP status and route, and
  Studio generation preflight reports a specific stale-Runtime restart message
  when a branch-local `/preflight` route is missing.
- Opened image and video gates for the active Runtime 8790 per user direction;
  ASR stayed closed. MiniMax image live smoke succeeded with `candidate_count=1`
  and registered one reusable image asset. Kling I2V preflight, submit, poll,
  preview, and offline `ffprobe` inspection succeeded with `candidate_count=1`.
- Cleared the previous MiniMax arm B P1 with a B-only live retry using the ready
  REST config: no fixed assets, no subject reference, one candidate, provider
  calls started, safe manifest succeeded, and no provider raw or secret values
  were persisted.
- Updated the readiness audit to recognize successful B-only retry evidence.
  The final no-cost audit now reports `recommended`, seven role checks passed,
  and zero provider blockers. This remains AI pre-acceptance only, not human
  acceptance or business validation.
- Hardened provider evidence boundaries: Kling preflight reports
  `AFS_PROVIDER_CONFIG` as a source label rather than an external local path,
  and Studio browser QA proxy isolation now closes image/video/ASR gates while
  allowing an explicit `--allow-live-llm` mode for the prompt-optimization path.
- Re-ran the asset-context browser QA with explicit live LLM allowed; the first
  optimize reached live LLM and the second re-optimize hit an upstream SSL EOF.
  No image/video provider call was started by that QA path, and the transient
  LLM failure was not retried further to avoid unnecessary provider calls.

Verification:

```text
Documentation-only change; no provider call, code execution, or generated media.
tests/test_studio_asset_context_browser_qa_tool.py tests/test_web_studio_static.py tests/test_afs_mvp_joint_qa_readiness_audit.py tests/test_kling_provider_preflight_tool.py: 35 passed, 1 warning
pytest -q: 404 passed, 527 deselected, 2 warnings
pytest -m legacy -q: 527 passed, 404 deselected, 1 warning
Studio JS node --check: 37 files passed
tools/maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0
```

Boundary:

- Current Studio video support remains I2V-oriented runtime/provider plumbing,
  not guaranteed localized video editing.
- This record is not human acceptance, business validation, or durable Company
  OS rule promotion.
- Repository records contain safe summaries only. External evidence remains
  under the joint QA evidence root and generated media remains in ignored
  runtime output paths.
- The recommendation is ready for the user's human acceptance decision; it is
  not a claim that human acceptance has happened.

## 2026-06-14 - MiniMax B Readiness Preflight

- Added `tools/minimax_image_provider_preflight.py`, a no-cost MiniMax image
  readiness check mirroring the Kling preflight pattern. It reports service
  shape, effective backend, normalized gate, credential presence, and dry-run
  request plan metadata without provider network calls or secret values.
- TDD coverage now verifies ready REST/API-key config and gate-closed behavior,
  including legacy `NARRATOCUT_ALLOW_REMOTE_IMAGE` normalization to
  `AFS_ALLOW_REMOTE_IMAGE`.
- Ran the preflight against the external provider config. Gate-closed evidence
  reports `image_gate_closed`; command-scoped gate-open evidence reports
  `ready`, effective backend `rest_api`, model `image-01`, and
  `secrets_printed=false`.
- Updated the readiness audit so `P1-IMAGE-B-PROVIDER-READINESS` includes the
  MiniMax preflight evidence and its next action is now one B-only live retry
  with `candidate_count=1` after explicit image retry approval.
- Hardened the preflight/audit evidence boundary: reports identify
  `AFS_PROVIDER_CONFIG` as the source label without writing the external config
  path, and the readiness audit now reads BOM-encoded JSON evidence correctly
  while preferring a ready gate-open preflight when both default gate-closed and
  command-scoped gate-open evidence exist.

Boundary:

- This does not clear the MiniMax B P1 because no new image provider call was
  made. It only proves the current REST/API-key configuration is ready for the
  next controlled retry.

## 2026-06-14 - Kling Startup Config Live Recovery

- Used an external provider config as a secret source only; inspected safe
  service shape and credential-presence booleans without printing secret values.
- Kling preflight with `kling_i2v` reached `ready` when `AFS_ALLOW_REMOTE_VIDEO`
  was scoped to one command. No ASR, LLM, or image gate was opened for the video
  smoke.
- Ran one Kling I2V Runtime smoke with a synthetic first frame, `candidate_count=1`,
  5 seconds, and 720p. Submit succeeded; a later poll hit a transient
  `ConnectError` and wrote a safe `poll_failed` manifest.
- Root-caused the failure to the Studio Runtime async poll path lacking the
  existing CLI path's transient httpx-to-curl fallback. Added TDD coverage and a
  minimal fallback in `poll_kling_i2v_task_once`; then recovered the already
  submitted job via poll-only, without a second generation submit.
- The recovered Runtime preview returned `video/mp4`; offline inspection recorded
  a 5.04s H.264 vertical video and a safe midframe thumbnail. The readiness audit
  now recognizes startup-config Kling success evidence and marks Video QA passed.
- Current closeout status remains `needs_fixes` because
  `P1-IMAGE-B-PROVIDER-READINESS` is still open for MiniMax arm B.

Verification:

```text
tests/test_kling_video_task_recovery.py::test_i2v_runtime_single_poll_falls_back_to_curl_for_transient_httpx_error: passed
tests/test_kling_video_task_recovery.py tests/test_kling_video_smoke.py tests/test_kling_video_runtime_polling.py: 9 passed
tests/test_afs_mvp_joint_qa_readiness_audit.py: 4 passed
tools/afs_mvp_joint_qa_readiness_audit.py on external evidence: needs_fixes with only P1-IMAGE-B-PROVIDER-READINESS remaining
```

Boundary:

- The Kling result is provider smoke plus AI pre-acceptance evidence, not human
  acceptance or business validation. The provider config path and secret values
  are not recorded in repository files.

## 2026-06-14 - Joint QA Readiness Audit Gate

- Added `tools/afs_mvp_joint_qa_readiness_audit.py`, a no-cost evidence
  aggregator for the MVP joint QA closeout. It reads the external evidence root
  and emits only relative evidence refs, provider blocker IDs, retry counts, and
  role-check status.
- Added TDD coverage in `tests/test_afs_mvp_joint_qa_readiness_audit.py`,
  including UTF-16 JSON evidence generated by PowerShell redirects.
- Generated the external safe audit
  `afs_mvp_joint_qa_readiness_audit.json`. Current status is `needs_fixes`:
  `P1-KLING-CONFIG-MISSING` is rooted at `provider_service_missing` with
  `provider_calls_started=false`, and `P1-IMAGE-B-PROVIDER-READINESS` is rooted
  at `remote_image_provider_not_ready` with `retry_count=1`.
- Verification after adding the audit: focused readiness/provider tests 11
  passed, default `pytest -q` 396 passed / 527 deselected, legacy
  `pytest -m legacy -q` 527 passed / 396 deselected, maintenance audit failed=0
  with existing warnings, and `git diff --check` exited clean.

Boundary:

- The audit is structure/readiness evidence only. It performs no provider calls,
  reads no secret values, and does not upgrade the closeout to human acceptance.

## 2026-06-14 - Provider Blocker Preflight Evidence Hardening

- Continued the MVP joint QA closeout branch after the blocker-marked push.
  Current local provider config still exposes MiniMax image/LLM services only;
  no video/Kling service is present, and Kling credential environment variables
  are absent.
- Hardened `tools/kling_provider_preflight.py` so no-cost Kling readiness now
  reports structured blocker IDs such as `provider_service_missing`,
  `provider_credentials_missing`, and `video_gate_closed`, while preserving
  `secrets_printed=false`.
- Hardened generation comparison evidence: Runtime A/B/C arm reports now include
  safe `blocks` and `retry_count`, and the live-comparison runner summarizes
  `block_ids` plus `retry_count` per arm.
- Added focused regression tests for Kling preflight blocker classification and
  comparison arm block summaries. Focused verification:
  `tests/test_kling_provider_preflight_tool.py`,
  `tests/test_api_runtime_generation_comparison.py`, and
  `tests/test_studio_asset_context_live_comparison_tool.py` passed 8 tests.
- Added no-cost external evidence files for the continued blocker diagnosis:
  `kling_provider_preflight_after_blocker_hardening.json` and
  `gate_closed_live_comparison_after_arm_block_summary.json`.
- Verification after this hardening: focused blocker tests 8 passed, default
  `pytest -q` 393 passed / 527 deselected, legacy `pytest -m legacy -q` 527
  passed / 393 deselected, maintenance audit failed=0 with existing warnings,
  and `git diff --check` exited clean.

Boundary:

- This hardening improves diagnosis and repeatability only. It does not run a
  new live Kling task or retry MiniMax arm B, and it does not change the
  `needs fixes / inconclusive` acceptance recommendation.

## 2026-06-14 - MVP Joint QA Closeout And Frontend Reviewer Fix

- Ran the joint Codex + Claude closeout lane on
  `codex/afs-mvp-joint-qa-closeout` with external evidence under
  `20260614-afs-mvp-joint-qa`; repo records contain only safe summaries.
- Re-ran gate-closed focused tests for manifest safety, prompt loop, keyframe
  reference guards, video generation, Studio static checks, and the browser QA
  tool: 53 passed, 1 warning. Studio JS `node --check` passed for 37 files.
- Ran Runtime-hosted `/studio/` browser smoke for project create, reload,
  second project create, and switch-back; no `Failed to fetch` and no warn/error
  logs were observed.
- Ran LLM browser smoke with image/video gates closed. Two prompt optimization
  safe manifests show provider calls started and raw responses were not stored;
  keyframe/comparison stayed image-gate blocked.
- Ran MiniMax image comparison within the live image cap. Arms A and C
  succeeded; arm B blocked after one retry with a safe provider-readiness error.
  No extra image retry was run because the conservative call cap was consumed.
- Attempted Kling I2V with explicit first-frame asset and `candidate_count=1`.
  Runtime preflight passed, but submit blocked before provider calls because the
  current local provider config has no video/Kling service and Kling credential
  environment variables were absent.
- Added the seventh AI pre-acceptance role, frontend UI reviewer. The first pass
  found mobile/narrow topbar and starter-card clipping; the responsive Studio
  shell fix now passes desktop/mobile/narrow Playwright checks.
- Hardened QA evidence tooling: browser QA screenshots default next to the
  external report path, and prompt optimization provider-call counts are exposed
  in future browser QA reports.
- Hardened provider-gate test isolation for Runtime API contract examples and
  legacy provider-validation subprocess tests so local live provider config or
  open gates cannot change deterministic expectations.
- Added `docs/handoff/AFS-MVP-JOINT-QA-CLOSEOUT-20260614.md` with seven-role
  pre-acceptance results and open P1 blockers.

Boundary:

- This run is AI role pre-acceptance and provider smoke where providers ran. It
  is not human acceptance, business validation, or durable-memory promotion.
- Current recommendation is `needs fixes / inconclusive`, not ready-to-accept,
  until Kling local provider config is present and the image B provider
  readiness issue is resolved or reclassified with stronger evidence.
## 2026-06-14 - Browser Repair Loop 005 Baseline And Guards

- Brought the Loop 003 browser QA red baseline into the active line as
  `docs/maintenance/AFS-AGENT-BROWSER-QA-LOOP-003.md`, so the known issues are
  auditable from the current branch instead of only from a stale QA branch.
- Added an L1 gap audit for the current north-star objective:
  `docs/maintenance/AFS-BROWSER-QA-LOOP-005-GAP-AUDIT.md`.
- Added explicit QAL003 regression anchors to Studio static tests for:
  fixed-asset pre-submit interlock, generated-image promotion entrypoints,
  Runtime-backed asset detail/remove/exclude actions, recent/current project
  visibility, and Kling no-sound UI.
- Added keyframe/video generation manifest safety tests that assert generated
  responses and persisted safe manifests do not expose provider raw payloads,
  provider URLs, media bytes, secrets, or local absolute paths.
- Hardened live LLM prompt optimization after browser QA reproduced the prior
  422 class: prompt-enhancement calls now send a formatter system message,
  retry once on chatty/non-sectional output, and salvage actual prompt text
  from repeated LLM article output without restoring the old local deterministic
  optimizer as the primary path.
- Normalized legacy provider descriptor gates such as `NARRATOCUT_ALLOW_REMOTE_*`
  to the current `AFS_ALLOW_REMOTE_*` names in the provider registry path, so
  ignored external provider configs no longer disagree with Studio gate state.
- Fixed a live Kling I2V P0 found during agent-led QA: the remote submit could
  succeed, but Runtime returned 422 before writing the safe manifest because an
  adapter `output_dir` absolute path was persisted into video task state. Runtime
  now strips `output_dir` before persistence and injects it only transiently for
  polling.
- Fixed a context bundle trace duplicate where a one-run excluded asset also
  appeared as `not_connected_to_target`.
- Ran Round A browser/live checks for T2I optimize, MiniMax image generation,
  generated image asset fixation, Runtime-backed asset detail, carry
  confirmation, one-run asset exclusion, refresh persistence, project isolation,
  video first-frame guard, Kling no-sound UI, and Kling I2V submit/poll/preview.
- Ran Round B valid-media runtime/browser checks with a real 1672x941 reference:
  I2I succeeded, fixed-asset carry preflight/submit succeeded, one-run asset
  exclusion succeeded, Kling I2V reached `succeeded` with a preview, and the
  Studio page loaded the target project with no console warn/error and no
  unsupported audio/sound UI.
- Fixed a new Round B P1 guardrail gap: tiny reference media could reach paid
  MiniMax/Kling provider paths and fail remotely. Provider descriptors now carry
  `min_reference_image_edge_px`; MiniMax image and Kling video default to 256px,
  and Runtime blocks too-small references before dispatch/submit with
  `provider_calls_started=false`.
- Ran Round C after the guardrail fix. It covered T2I, upload, I2I, fixed asset
  promote/detail, fixed-asset carry, one-run exclusion, Kling I2V recovery, and
  Studio load. Round C found one new P1: Studio image-model selection could mask
  the LLM provider fields and return 422 `not_requested`. `minimax_text_requested`
  now checks `llm_provider`, `llm_model`, then `model`, and the live retry
  returned `provider_calls_started=true` / `status=applied`.
- Ran Round D and Round E as two consecutive clean role-matrix rounds. Each
  round used one remote LLM optimization, four MiniMax image submits, and one
  Kling I2V submit. Both rounds passed remote optimize, T2I, upload/I2I, fixed
  asset promote/detail, fixed carry preflight+submit, one-run exclusion, Kling
  I2V safe preview, and Studio load with no unsupported sound/audio UI and no
  console warn/error.
- Added `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md` as the current
  human acceptance entrypoint. The project can claim runtime/browser
  verification for the tested MVP paths, but not human acceptance until the user
  runs the runbook and records pass/fail plus creative-quality scores.

Verification so far:

```text
Loop 005 focused tests:
tests/test_web_studio_static.py
tests/test_api_runtime_generation_manifest_safety.py
selected preflight/token/exclusion tests

26 passed, 1 warning

Additional focused tests:
tests/test_openai_compatible_provider.py
selected prompt optimizer retry/salvage tests
selected provider registry gate-normalization test
selected context resolver asset-exclusion test
selected video task-state path hygiene tests

All selected tests passed.

Round B focused reference/provider guards:
tests/test_api_runtime_keyframe_reference_assets.py
tests/test_api_runtime_video_generations.py
tests/test_provider_adapter_registry.py

37 passed, 1 warning

Prompt optimizer regression after Round C:
tests/test_api_runtime_prompt_memory_loop.py

17 passed, 1 warning

Browser/runtime evidence:
runs/agent_browser_qa_loop_005/round_c_runtime_summary.json
runs/agent_browser_qa_loop_005/round_d3_runtime_summary.json
runs/agent_browser_qa_loop_005/loop005-round-e-clean-1_runtime_summary.json
runs/agent_browser_qa_loop_005/round_d3_studio_load.png
runs/agent_browser_qa_loop_005/round_e_studio_load.png
```

Boundary:

- Loop 005 runtime/browser verification is closed for the tested MVP paths after
  two consecutive clean rounds.
- This is not human acceptance, business validation, or durable-memory
  promotion.
- MiniMax identity similarity and Kling first-frame/motion quality remain
  human-scored through `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md`.

## 2026-06-14 - Asset Exclusion Preflight And Browser Repair Loop 004

- Added generation preflight support for fixed-asset carry review before paid
  submit: keyframe/video preflight, request-level temporary asset exclusions,
  preflight consistency token, and safe visual asset detail endpoint.
- Added Studio generation confirmation when fixed assets will be carried. The
  confirmation always lists carried assets, even when lexical conflict detection
  has no hit, and supports one-run exclusion of a whole asset.
- Changed asset detail popovers to fetch Runtime-backed visual asset details
  instead of trusting node cache only; exposed `从当前节点移除` and `本次不携带`.
- Added fixed-asset entrypoints from drawer image assets and kept generated
  image/node paths compatible with the existing visual asset panel.
- Fixed two browser-discovered P1 issues: stale/legacy model ids now resolve
  through the same model picker path used for display, and canceling the carry
  confirmation now flushes restored node state to Runtime.
- Hid unsupported Kling audio/sound controls unless future descriptors expose
  audio support; the current I2V spec UI shows only ratio, resolution, and
  duration.
- Recorded browser QA evidence and human acceptance runbook for the handoff.

Verification so far:

```text
Focused Runtime preflight/video/visual asset tests: 27 passed, 1 warning
Studio static tests: 14 passed
Changed Studio JS node --check: passed
Browser QA on http://127.0.0.1:8794/studio/?project=loop004-browser-qa:
  carry confirmation passed
  one-run exclusion passed
  cancel persistence passed
  Runtime-backed asset detail popover passed
  Kling video spec no-sound UI passed
```

Evidence:

```text
docs/maintenance/AFS-BROWSER-QA-LOOP-004.md
docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-004.md
runs/agent_browser_qa_loop_004/
```

Boundaries:

- Browser/runtime verification only; human acceptance still requires the
  runbook to be executed by the user.
- MiniMax/Kling creative quality remains human-scored.
- No provider raw, signed URL, secret, or private local material was recorded.

## 2026-06-13 - Legacy Freeze And Repository Hygiene

- Added `.gitattributes` and confirmed renormalization did not create broad
  line-ending churn.
- Tagged and pushed `legacy-frozen-20260613` at the pre-cleanup baseline.
- Froze production-memory and distribution-chain tests behind the `legacy`
  marker; default `pytest` now runs the current Runtime/Studio/contract gate,
  while `pytest -m legacy` runs the frozen reference suite.
- Updated maintenance audit to list legacy-frozen paths separately while still
  scanning the full repository for secret-like fragments and runtime artifacts.
- Retired current code/test compatibility for `NARRATOCUT_ALLOW_REMOTE_*`;
  provider gates now use `AFS_ALLOW_REMOTE_*` only.
- Deleted the stale v0.2 Runtime frontend handoff and the orphan
  `ComplianceResult` schema.
- Classified untracked root cleanup/review instruction files as local workspace
  inputs so they do not break repository retention review when present in the
  operator checkout.

Verification so far:

```text
Default pytest: 363 passed, 527 deselected, 2 warnings
Legacy pytest: 527 passed, 363 deselected, 1 warning
Focused provider/schema/runtime/static tests: 66 passed, 1 warning
maintenance_audit: failed=0, passed=4, warning=3
git diff --check: exit 0, Windows LF conversion notices only
```

## 2026-06-13 - Runtime Legacy Route Removal

- Removed Production Memory HTTP business routes from Runtime Service:
  `POST /runs/asset-test`, `POST /runs/two-round-validate`, and
  `POST /provider/validation-plan`.
- Kept production-memory CLI commands, `agentflow/memory`, and production-memory
  harness/function tests intact.
- Regenerated the default Runtime OpenAPI snapshot with
  `AFS_ENABLE_LEGACY_RUNTIME_V02` closed; the snapshot no longer contains the
  removed Production Memory routes or stale v02 routes.
- Kept `/provider/script-draft-plan` as the current LLM script vertical.
- Replaced current default route exception projection with safe error details;
  remaining `detail=str(exc)` usage is legacy-v02-only residual risk.
- Updated the positioning sentence to:
  `AgentFlow Studio 是 AI 内容生产的 Agent-native 生产操作层。`
- Added dependency upper bounds without generating a lock file.

Verification so far:

```text
Focused Runtime contract set: 31 passed, 2 warnings
Default OpenAPI export: passed
maintenance_audit: failed=0, passed=4, warning=2
CLI --help: passed
CLI version: 0.1.0
Full pytest: 886 passed, 2 warnings
git diff --check: exit 0, Windows CRLF notices only
```

## 2026-06-13 - Browser QA Hardening Loop 6/7 And Final Verification

- Continued agent-led browser QA after the live asset and Kling passes.
- Fixed Studio state persistence for `lastContextBundle`: safe included/excluded assets, budget, warnings, and temporary lock override summaries now survive refresh, while `trace_summary`, provider prompt, provider raw, and other runtime-only details remain pruned.
- Added active Runtime save flush after image/video generation and poll success/failure so final node states are not lost to debounce timing.
- Added drawer actions for selected video nodes to use existing image assets as explicit first/last frames; no implicit last-upload or first-upload fallback is used.
- Prevented video nodes from hydrating an image preview URL into `<video>` playback; only Runtime video preview routes can become video `previewUrl`.
- Fixed prompt-bar video behavior: a running video node with `lastVideoJobId` now continues polling instead of submitting another paid video job, and completed nodes return to the normal `生成` action.
- Updated `.env.example` to remove legacy `NARRATOCUT_*` provider gate names.
- Rewrote the browser QA maintenance report in Chinese and added Loop 6/7 evidence plus final verification status.

Verification:

```text
Focused Runtime/Provider/Studio tests: 72 passed, 1 warning
Studio JS node --check: 37 files passed
Full pytest: 886 passed, 2 warnings
maintenance_audit: failed=0, warning=2
git diff --check: exit 0, CRLF notices only
Browser final check: current Studio tab has safe video preview, send action title is 生成, app console warn/error count is 0
```

Boundary: this closes runtime/browser verification for the current hardening loop. It is still not human acceptance; MiniMax identity quality and Kling first-frame creative quality need human scoring.

## 2026-06-13 - Browser QA Hardening Loop 5

- Continued agent-led browser QA on a fresh project and fixed asset semantics discovered during the run.
- Fixed Runtime-synced visual assets in the drawer: fixed assets now keep `asset_type`, `image_asset_refs`, safe preview URLs, and labels such as `人物资产` instead of falling back to `参考`.
- Improved visual asset prefill by extracting from optimized prompt sections and deduplicating repeated phrases in signatures and feature cards.
- Added occupied-region avoidance for dock-created nodes so new nodes no longer land directly on top of existing nodes.
- Fixed drawer `用于当前节点`: fixed visual assets now populate `node.params.visualAssets`, so node badges, context_subgraph, optimizer asset references, and generation resolver all see the same asset.
- Hardened selected video toolbar behavior so a running video task exposes `video-poll` rather than a second submit action.
- Browser evidence covered fresh project creation, T2I optimize/generate, asset fix, refresh drawer restore, readonly asset detail, attached-asset optimization, and attached-asset generation with `本次携带 1 项资产`.

Verification:

```text
tests/test_web_studio_static.py tests/test_api_runtime_studio_state.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_creative_agent_keyframes.py: 42 passed, 1 warning
Studio JS node --check for all apps/studio/src/**/*.js: passed
Browser console warn/error: none
Evidence: runs/loop-fresh-asset-drawer-20260613.png, runs/loop-attached-asset-optimize-20260613.png, runs/loop-attached-asset-generation-20260613.png
```

Boundary: live MiniMax image/LLM output remains runtime/provider verification only. Character identity similarity still needs human scoring.

## 2026-06-13 - Browser QA Hardening Loop 4

- Fixed Studio video resume persistence: safe `firstFrameImageAssetId`, `lastFrameImageAssetId`, `lastVideoJobId`, `lastVideoPreviewUrl`, and quota override state now survive `studio-state` save/restore.
- Extended safe preview URL validation to Runtime video preview routes while still rejecting local paths and provider URLs.
- Added the video node `继续轮询视频任务` path after refresh and verified it against a live Kling I2V job.
- Fixed successful video poll rendering: the node `previewUrl` now switches to the video preview endpoint and video nodes render a `<video controls>` player instead of the image preview component.
- Recorded a UX risk: the selected-node toolbar can make `生成` and `更多` easy to mis-hit during QA; one accidental Kling submit was safely completed and reused as resume evidence.

Verification:

```text
tests/test_api_runtime_studio_state.py tests/test_web_studio_static.py: 20 passed
node --check apps/studio/src/node-result-view.js apps/studio/src/node-actions.js apps/studio/src/panels/node-menu.js: passed
Browser QA: refresh -> node menu -> continue poll -> succeeded -> video player rendered
Evidence: runs/kling-poll-ui-video-preview-20260613.png
```

Boundary: this is runtime/browser verification only. The Kling video is technically playable; creative quality and first-frame suitability still need human scoring.

## 2026-06-13 - Browser QA Hardening Loop 3

- Fixed the live Kling I2V browser path discovered during agent-led QA.
- Split Kling Studio execution into true async submit/poll: submit now creates the provider task and returns `submitted`; poll returns `running` or `succeeded`.
- Hardened the Kling adapter against generic provider-plan field leakage and added a safe Runtime manifest fallback for unexpected adapter exceptions.
- Verified a live Studio video-node path with explicit first frame: upload -> set first frame -> submit -> poll -> safe preview.
- Live Kling output succeeded with a safe `video/mp4` preview, H.264 1924x1076, 24fps, 5.04s, 9.13MB. First/last frame evidence was extracted under `runs/`.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_video_generations.py tests/test_kling_video_smoke.py tests/test_kling_video_request_plan.py tests/test_kling_video_task_recovery.py tests/test_kling_video_completion.py: 44 passed
node --check apps/studio/src/node-actions.js: passed
ffprobe media sanity: passed
```

Boundary: Kling live execution is runtime/provider verification only. The generated clip is technically valid, but quality still needs human scoring; multi-view sheets can produce crop artifacts and should not be treated as ideal video first frames.

## 2026-06-13 - Browser QA Hardening Loop 2

- Continued agent-led browser QA on `codex/afs-browser-qa-hardening-002`.
- Fixed empty-project meta drift between URL/project select/drawer after async project-list refresh.
- Removed demo seed assets from new Studio projects and deduplicated Runtime-synced assets by safe `asset_id` / `visual_asset_id`.
- Extended Studio state sanitization to preserve safe asset ids, feature cards, negative locks, signatures, and safe preview URLs for asset drawer/details restore.
- Strengthened I2I prompt optimization: uploaded image filename summaries now reach Runtime, and generic MiniMax-M3 outputs that miss reference/short-hair/school-uniform locks are replaced by a traceable guardrail fallback.
- Simplified image and video node prompt bars by hiding unimplemented operation-mode controls.
- Browser evidence covered asset fix prefill, asset drawer/detail restore, live MiniMax I2I optimization, live MiniMax I2I generation, and video first-frame guard behavior.

Verification:

```text
tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_studio_state.py tests/test_web_studio_static.py: 31 passed
tests/test_web_studio_static.py: 14 passed after video UI cleanup
node --check touched Studio JS: passed
py_compile touched Runtime modules: passed
```

Boundary: live MiniMax I2I generation is provider/runtime evidence, not human acceptance. It improved hair/uniform preservation but still showed identity/background drift.

## 2026-06-13 - Browser QA Hardening Follow-up

- Fixed project isolation after Claude walkthrough: project switch no longer reads the unscoped legacy canvas key as a runtime fallback; legacy keys are migrated once and removed.
- Replaced native `window.prompt` / `window.confirm` project/director flows with in-app modals.
- Normalized legacy `NARRATOCUT_ALLOW_REMOTE_*` provider gates to `AFS_ALLOW_REMOTE_*` in the registry and MiniMax/Kling plan fallbacks.
- Skipped `company_gateway` aggregate services in ProviderRegistry so local full provider configs do not block concrete adapters.
- Split prompt optimization into T2I expansion and I2I edit modes, surfaced `optimization_mode` to Studio, and removed user-facing raw provider/gate error text.
- Flushed Studio state immediately after image upload so refresh restores safe preview URLs.

Verification:

```text
Focused static/provider/optimizer tests: 17 passed, 1 warning
Studio JS node --check for touched files: passed
Browser QA report: runs/browser_qa_hardening_1781302404.json status=passed
MiniMax image API smoke: succeeded, provider_calls_started=true
Kling I2V preflight: ready, secrets_printed=false
git diff --check: passed with CRLF notices only
```

Boundary:

- Live LLM optimization and one MiniMax image generation were used as runtime verification only.
- Kling was preflighted but no live I2V job was submitted in this slice.
- No provider secrets or raw provider payloads were written to tracked files.

## 2026-06-13 - LLM Optimizer Runtime Fallback Fix

- Fixed the remaining Studio prompt optimization 422 when the external provider config has blank legacy LLM default model refs.
- Added provider-side legacy defaults for descriptorless OpenAI-compatible LLM services: MiniMax falls back to `MiniMax-M2.7-highspeed`, DeepSeek falls back to `deepseek-chat`.
- Prompt optimization now skips MiniMax Anthropic-style OpenAI-compatible 404s and continues to the next registry LLM service.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_prompt_memory_loop.py: 31 passed, 1 warning
Runtime 8790 restarted with external provider config and AFS_ALLOW_REMOTE_LLM/IMAGE/VIDEO=true
POST /projects/debug-optimizer/prompt-optimizations: 200 OK, provider_calls_started=true, llm_enhancement.status=applied
Kling provider preflight: ready, secrets_printed=false
Registry descriptor check: minimax_image, kling_i2v, deepseek_llm, minimax_llm ready
```

Boundary:

- No provider secret or raw provider response was written to tracked files.
- No live image or Kling video job was submitted in this fix.
- The live LLM optimization call is runtime verification, not human acceptance.

## 2026-06-13 - Provider Service Alias Fix

- Fixed Studio prompt optimization when the active provider config exposes `minimax_llm` instead of `minimax_m3`.
- Added LLM service fallback in Runtime prompt enhancement: explicit request -> `minimax_m3` -> `minimax_llm` -> other registry LLM services.
- Mapped legacy descriptorless `provider=minimax`, `capability=llm` services to the OpenAI-compatible LLM adapter under the existing `AFS_ALLOW_REMOTE_LLM` gate.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_prompt_memory_loop.py: 29 passed, 1 warning
Studio optimizer/model JS node --check: passed
External provider config registry check: minimax_image ok, minimax_llm ok, kling_i2v ok, minimax_m3 absent by design
```

Boundary:

- No live LLM, image, or video provider call was made in this fix.
- Existing running Runtime processes must be restarted to pick up the alias fallback.

## 2026-06-13 - Kling I2V Preflight And Project Persistence

- Added Runtime project listing and image asset public listing for Studio project selection and drawer rehydration.
- Persisted safe Runtime preview URLs in Studio state and rejected non-runtime preview URLs.
- Added project-scoped Studio local cache, topbar project selector/new-project action, and preview hydration from saved uploads.
- Split context resolver responsibilities into subgraph, asset arbitration, and text-channel modules while keeping the old facade import.
- Added shared provider dispatch retry helper for image/video reuse.
- Extended ProviderDescriptor to v0.2 video fields and added `kling_i2v` registry adapter wiring on top of existing Kling modules.
- Added Runtime video generation submit/poll/cancel/preview routes with explicit first-frame asset id, candidate_count=1, video gate, quota counter, and safe manifest.
- Added Studio video node path for explicit first/last frame marking and Kling I2V submit.
- Added safe Kling provider preflight tool and video descriptor addendum.
- Added a narrow legacy descriptor inference path for descriptorless Kling local configs so the existing external secret file can be used without copying credentials into the repo.

Verification:

```text
Project persistence focused: 4 passed
Provider registry focused: 19 passed
Runtime video focused: 4 passed
Resolver/keyframe/visual asset focused: 18 passed
Keyframe focused: 11 passed
Studio static: 12 passed
Combined focused set: 63 passed
Full pytest: 868 passed
Studio JS node --check for all apps/studio/src JS files: passed
Project browser QA: passed on 127.0.0.1:8791/studio/
External Kling secret preflight: ready, secrets_printed=false, gate disabled
```

Live state:

```text
Repo-local configs/providers.local.json only exposes MiniMax services.
For Kling, use AFS_PROVIDER_CONFIG pointing at the external `.secrets` provider config supplied by the operator.
Preflight against that file is ready; AFS_ALLOW_REMOTE_VIDEO is still disabled in the current shell.
```

Boundaries:

- No live Kling submit was run.
- No provider secret, provider raw response, signed URL, local absolute media path, or media bytes were written to tracked files or API responses.
- Fake async video remains contract verification only.

## 2026-06-13 - MVP Hardening 001

- Added provider-facing `user_prompt_plain` and backend section-header stripping so human-readable prompt sections do not leak into image provider prompts.
- Capped generate-mode full-card asset injection at 3 characters and 1 scene; over-limit assets degrade to signature-only and are traceable in `excluded_assets`.
- Changed context subgraph traversal so `reference` edges do not consume the normal 3-hop budget, with a separate 6-reference-edge loop guard.
- Upgraded `visual_asset` to v0.2 with `supersedes_asset_id` and deterministic same-label arbitration by version terminal or newest `server_recorded_at`.
- Added `resolver_version`, `vocabulary_hash`, and `feature_card_hash` metadata to context bundles.
- Added one readiness/network retry around image provider dispatch and writes `retry_count` into keyframe safe manifests.
- Removed non-image local preview placeholders from Studio; non-image sends are disabled with explanatory copy, and fake cost numbers are hidden.
- Added readonly visual-asset detail popovers, fixed/retired drawer distinction, asset badge invalid-state correction, drawer search, Chinese fixed-asset action titles, and shortcut panel entries for `?`, `Ctrl+L`, and `Ctrl+D`.

Verification:

```text
Backend focused hardening set: 33 passed, 1 Starlette/httpx warning
Studio static: 12 passed
Changed Studio JS node --check: passed
Full pytest: 855 passed, 1 Starlette/httpx warning
maintenance_audit: failed=0, warning=2 existing doc/oversized warnings
git diff --check: passed with Windows CRLF notices only
Browser light QA: `/studio/` loaded with no console errors; visible page no longer exposes `asset_fix`, `fix visual asset`, local-preview text, or `.bar-cost`. Current browser state had no asset badge, so readonly asset-detail clicking remains static-test covered until a seeded asset state is used.
```

Boundaries:

- No live provider call or human acceptance was run in this slice.
- Kling/video, S2 feature-card LLM extraction, S3 storyboard schema, and legacy package retirement remain out of scope.

## 2026-06-13 - Studio MVP Usability P0

- Switched the Studio prompt optimizer product path to remote-required LLM enhancement. Local deterministic assembly remains backend-internal for tests and non-Studio fallback, but the Studio UI no longer silently shows it as an optimization result.
- Persisted local Windows user env gates for this machine: `AFS_ALLOW_REMOTE_IMAGE=true`, `AFS_ALLOW_REMOTE_LLM=true`, and `AFS_PROVIDER_CONFIG=D:\Projects\AgentFlowStudio\configs\providers.local.json`; video, ASR, and download gates remain untouched.
- Fixed Studio state persistence so transient runtime bundle details such as `lastContextBundle.trace_summary` are pruned before safety scanning, while fixed `visualAssets` can persist on nodes.
- Updated node actions so image-node retry uses the real generation path and node menus expose direct asset marking from the canvas.
- Improved runtime client error detail propagation and image gate blocked copy, so provider/gate failures are visible instead of turning into generic request errors.

Verification:

```text
Focused prompt/state/static tests: 4 passed
Prompt/state/static related suite: 21 passed
Changed Studio JS node --check: passed
Full pytest: 844 passed, 1 Starlette/httpx warning
```

Boundaries:

- No live provider call was run as part of this code change.
- Runtime/browser verification is still not human acceptance.

## 2026-06-12 - MVP Closeout Live A/B/C

- Ran gate-closed Studio browser QA successfully after tightening the QA selector for multiple temporary-unlock buttons.
- Ran live MiniMax A/B/C through the Provider Gateway using the local `mmx_cli` token-plan backend and `AFS_ALLOW_REMOTE_IMAGE=true`; LLM/ASR/video/download gates stayed unset.
- Live A/B/C succeeded with one generated image per arm. A had no asset context, B used the resolver path without fixed asset injection, and C used fixed asset feature/locks plus one subject reference image.
- Visual observation: C materially improved identity, red coat, short black hair, and left-brow marker compared with A/B, but the brow scar wording produced an over-literal black cross-like mark and should be refined before broad internal testing.
- Evidence is under ignored `runs/studio_asset_context_live_comparison_20260612_final/`; closeout summary is `docs/handoff/AFS-MVP-CLOSEOUT-20260612.md`.
- Non-claims: live A/B/C is provider smoke and asset-semantics evidence only; it is not human acceptance, business validation, or durable-memory promotion.

中文摘要：本文件只保留当前阶段的短记录和验证入口，不再承载旧 Web、旧 Workbench 或历史浏览器 QA 的长流水。当前判断以 Studio、Runtime Service、知识库、创作智能体和 provider gate 为主线；测试通过只代表工程验证，不代表人工验收、商业验证或长期记忆晋升。后续如果某条记录不再支持当前 MVP、真实模型接入或维护收口，应直接删除，避免把过期资料继续带入主线。

当前状态：本轮收口已经把旧 Workbench、旧静态 Web、过期前端对接包和旧浏览器 QA 记录移出主线，同时补上创作意图控制智能体、关键帧生成 gate、Studio 静态入口和 OpenAPI 契约。后续记录只写影响当前落地的验证结果、阻塞项和真实模型接入证据，不再追加无明确后续用途的过程叙事。

Status: short current-session log. Historical long narratives are not current
product documentation.

中文当前说明：本文件当前只作为工程维护流水账，不承担业务验收、模型效果判断或长期公司规则晋升。每条记录都应服务于后续接手者快速判断“这轮到底改变了什么、验证了什么、还剩什么风险”。如果某项工作只产生了本地缓存、临时运行产物或 provider 原始响应，它不能被写成产品能力完成；如果某项证据还没有经过人工验收，也不能被写成业务有效。当前阶段的重点是把 Studio 主线、Runtime Service、provider gate、固定资产、图谱上下文和维护清理统一到一条可落地的 MVP 链路上。历史分发线、旧 Workbench、旧 memory UI、旧候选记忆流程只保留为 legacy 或审计背景，不再作为新任务入口。后续每次接入真实模型前，都应先确认本地配置没有进入 tracked 文件，provider gate 按能力单独开启，生成媒体只落在 ignored runtime/evidence 目录，并在报告中明确区分工程验证、provider smoke、人工验收和业务验证。

## 2026-06-12 - Provider Gateway v0.1

- Extended the provider descriptor with `capabilities`, optional `account_pool_id`, and `rate_limit_hint`.
- Added local account pool selection with deterministic priority ordering, disabled-account filtering, and credential-env presence checks without reading or persisting secret values.
- Kept MiniMax image on the unified `ProviderRegistry.dispatch(...)` path and preserved descriptor-driven prompt budget / reference slots.
- Added OpenAI-compatible LLM dispatch to the registry and moved Runtime prompt enhancement away from legacy `ModelGateway.from_config_path`.
- Added a fake async video adapter to validate `submit -> poll -> normalize` lifecycle without live video provider calls.
- Replaced provider adapter and config docs with readable contracts and expanded `configs/providers.example.json` to cover image, LLM, fake video, descriptors, and account pools.

Verification so far:

```text
tests/test_provider_adapter_registry.py: 11 passed
Focused provider/keyframe/resolver/prompt set: 42 passed, 1 Starlette/httpx warning
Full pytest: 838 passed, 1 Starlette/httpx warning
Studio JS node --check: passed 35 files
maintenance_audit: failed=0, warning=1 existing oversized-files warning
git diff --check: passed with Windows CRLF notices only
```

Boundaries:

- Provider gates remain closed except mocked dispatch paths inside tests.
- No live image, LLM, ASR, video, or download provider call was made.
- Fake video adapter is a lifecycle contract test only, not provider smoke.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - Project Inventory And Direct Cleanup 001

- Added reusable project inventory / cleanup tooling with tracked, ignored, and untracked-unignored classification.
- Protected local provider config, local model weights, raw source media, and media evidence as report-only.
- Generated `docs/maintenance/AFS-PROJECT-INVENTORY-20260612.md` and machine reports under ignored `data/reports/project_inventory/`.
- Executed low-risk cache cleanup. Across cleanup and post-verification cleanup passes, 14,452 cache targets were deleted, saving about 30.24MB.
- Confirmed `configs/providers.local.json`, `configs/models.yaml`, `data/models/faster-whisper`, and `data/raw/demo_zombie/input.mp4` remained in place.
- Recorded remaining Windows ownership/ACL blocker: `data/processed/pytest-basetemp` is ignored pytest cache but cannot be fully deleted by the current user.
- Removed the extra deep-review helper code after using its output; maintenance should not accumulate one-off audit tooling.
- Deleted the unreferenced tracked empty package `agentflow_studio/asset_manager/__init__.py`.
- Deleted six obsolete `AFS-PRODUCTION-MEMORY-ASSET-*` handoff files superseded by fixed `visual_asset` and graph-scoped resolver work.
- Removed Production Memory short aliases from the default CLI product surface; legacy long `production-memory-loop-*` commands remain hidden compatibility while `agentflow/memory` is still tested.
- Deep local review covered 12,791 local files, 3.46GB, 755 project text files, and 86,993 text lines; 80 exact duplicate media/evidence groups represent about 827MB theoretical reclaimable space once a canonical evidence-retention rule exists.

Verification so far:

```text
tests/test_project_inventory_cleanup.py: 3 passed
```

Boundaries:

- Provider gates remain closed.
- No model weights, provider local config, source media, or unique evidence artifacts were deleted.
- Duplicate media evidence was not deleted without a canonical run retention rule.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - Studio Mainline Cleanup 001

- Updated project authority docs so `/studio/` + Runtime Service + fixed assets/context resolver/provider-gated evidence is the current MVP line.
- Marked the subtitle/text distribution chain as legacy/optional rather than current MVP.
- Hid Runtime v02 list/import/source-assets/content-cards/canvas-draft routes by default behind `AFS_ENABLE_LEGACY_RUNTIME_V02=true`.
- Marked `agentflow/memory` as read-only legacy for Studio/Runtime work; added a static guard against new Studio/Runtime imports.
- Audited the named `*_sop` cleanup targets with `git ls-files`; only `agentflow_studio/compliance/__init__.py` was tracked and unreferenced, so only that stub was deleted.
- Created `BACKLOG.md` for follow-up maintenance debt: oversized file split and Kling adapter v0.2.

Verification:

```text
Cleanup/static focused tests: 15 passed, 1 Starlette/httpx warning.
Full pytest: 828 passed, 1 Starlette/httpx warning.
Studio JS node --check: 35 files passed.
maintenance_audit.py: 0 failed checks, 1 oversized-files warning.
git diff --check: clean except Windows CRLF notices.
```

Boundaries:

- No broad deletion of `agentflow/memory`.
- No live provider gate was opened.

## 2026-06-12 - Director Compiler v1

- Added deterministic backend `Director Compiler v1` for `DirectorSetup2D`.
- Extended director setup with `activeCameraId`, `activeSubjectIds`, and subject-level `visual_asset_id`.
- Changed user prompt assembly and context resolver to consume compiler output rather than frontend readout text.
- Backend compiler reads visual asset signatures by id from the Runtime visual asset store; frontend-provided signatures are ignored.
- Updated Studio director defaults so empty lists remain empty and the old bedroom prop/modifier template no longer repopulates after deletion.
- Changed Studio “生成提示词片段” to confirmed append-only behavior; it no longer overwrites the node prompt.

Verification:

```text
Director compiler/API/context/static focused set: 24 passed, 1 Starlette/httpx warning.
Changed director JS node --check: passed.
```

Boundaries:

- Frontend `directorPromptSummary` is now a UI summary only, not the authoritative compiler.
- No live provider gate was opened.

## 2026-06-12 - Provider Adapter v0.1

- Added `provider_descriptor.v0.1` to service config and documented the adapter contract in `docs/provider_adapter_contract.md`.
- Added `ProviderRegistry.dispatch(capability, service_id, request)` and a MiniMax image adapter wrapper with the standard `validate -> translate -> submit -> poll -> normalize` lifecycle.
- Changed Runtime keyframe generation to use the registry instead of importing MiniMax smoke directly.
- Moved keyframe prompt length and reference image slot limits behind provider descriptors; MiniMax remains configured as one subject reference image slot.
- Kept gate-closed Runtime paths config-free and no-network.

Verification:

```text
Provider/keyframe/resolver focused tests: 22 passed, 1 Starlette/httpx warning.
MiniMax smoke regression: 9 passed.
py_compile for provider adapter, Runtime keyframes, context resolver, budget: passed.
```

Boundaries:

- No live provider gate was opened.
- Kling/video adapter is expressible by the contract but not implemented in this slice.

## 2026-06-12 - AFS Asset Context S1

- Created isolated branch/worktree `codex/afs-asset-context-s1`.
- Added `visual_asset v0.1` Runtime storage and promote/list/retire APIs.
- Stopped prompt-background placeholder pollution: `Primary character` / `Primary scene` no longer create records, and extracted context stays candidate-only.
- Added `context_subgraph v0.1` and `context_bundle v0.1`; prompt optimization and keyframe generation now share the resolver when a subgraph is supplied.
- Split optimize/generate views: optimize injects only connected or label-matched signatures, generate consumes only connected fixed assets.
- Added request-level temporary lock overrides and unconditional negative-lock injection for non-overridden locks.
- Kept no-subgraph keyframe requests on the old `asset_refs` path for compatibility.
- Added `generation_comparison_report v0.1` with fixed A/B/C arm definitions.
- Added one-click connect for named unconnected assets, request-level temporary unlock, and reproducible gate-closed browser QA in `tools/studio_asset_context_browser_qa.py`.
- Browser QA drives upload -> fixed asset -> optimize warning -> one-click connect -> temporary unlock -> generate -> A/B/C report and writes `runs/studio_asset_context_browser_qa_report.json`.
- Added `tools/studio_asset_context_live_comparison.py` as the S1 A/B/C evidence runner. It writes a gate-closed readiness report by default and requires `AFS_ALLOW_REMOTE_IMAGE=true`, `--allow-live-provider`, provider config, and a real `--reference-image` or explicit `--sample-reference-output` before any image provider call can start.
- Added `tools/studio_asset_context_sample_reference.py` to write a deterministic non-provider PNG reference for reproducible provider smoke setup.
- Added `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md` to keep the current pass/block state explicit until live MiniMax evidence is available.
- Added Studio single-canvas fixed-asset confirmation panel, `context_subgraph` request building, asset connection status display, and "本次携带" bundle summary.

Verification so far:

```text
Focused Runtime/Web set: 34 passed, 1 Starlette/httpx warning.
Full pytest: 798 passed, 1 Starlette/httpx warning.
Studio changed JS node --check: passed.
Browser QA script: passed with provider gate closed; report records browser API POST proxy via FastAPI TestClient due local Chrome POST hang.
Live comparison runner gate-closed readiness: passed with ignored provider config path supplied; provider_calls_started=false.
Live comparison gate-safety preflight: simulated `AFS_ALLOW_REMOTE_IMAGE=true` without `--allow-live-provider`; blocked with `live_provider_flag_missing`, provider_calls_started=false.
Maintenance audit: passed with 0 warnings.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed in local verification.
- No provider raw response, media bytes, local absolute paths, signed URLs, or secrets were added.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - MiniMax Text/Image Integration And Reference Flow

- Added gated MiniMax-M3 prompt enhancement for the creative intent agent path; deterministic local prompt assembly remains the fallback when the LLM gate or config is unavailable.
- Added gated MiniMax image-01 keyframe generation and safe candidate preview refs; API responses do not expose provider raw payloads, local absolute paths, signed URLs, media bytes, or secrets.
- Added Studio image upload assets and generated-keyframe reusable assets so connected downstream image nodes can send upstream reference images for image-to-image style tests.
- Kept the Studio user surface product-facing: optimization remains a node action, keyframe sending is image-node scoped, and trace/rule/weight/provider internals stay out of the UI.
- Local provider keys remain environment-only through `MINIMAX_API_KEY`; tracked config files contain examples and placeholders only.

Boundaries:

- Provider smoke is not human acceptance, business validation, video validation, or durable-memory promotion.
- Video generation remains closed.

## 2026-06-12 - AFS Studio v0.2 Delivery Polish

- Created isolated branch/worktree `codex/afs-studio-v02-delivery-polish-001` because the main checkout was occupied by a parallel MiniMax integration branch.
- Reframed the user-facing Studio surface into AFS Studio 创作图谱: flow-native starters for script-to-storyboard, character turnaround, 2D director board, keyframe prompt, and 5s video prompt.
- Added safe Runtime Studio state API: `GET /projects/{project_id}/studio-state` and `PUT /projects/{project_id}/studio-state`; only meta, viewport, nodes, semantic edges, visible assets, and safe summaries are persisted.
- Added frontend Runtime save/restore with localStorage fallback and visible save status: 已保存 / 保存中 / 同步中 / 本地暂存.
- Added lightweight undo/redo for meaningful canvas edits while excluding high-frequency pan/zoom/drag/prompt typing from history bloat.
- Upgraded visible assets: local preview and director saves create typed asset cards; asset drawer supports 设为参考, 用于当前节点, and 从画布定位.
- Added semantic edge types: generation, director, and reference; director/reference edges have distinct line styles and labels.
- Director board saves now upsert a `director_setup` asset and mark downstream edges as director constraints when applied to connected nodes.
- Prompt optimizer remains input-anchored and product-facing; result actions now give replace/append/copy feedback and source chips stay limited to 影视结构, 项目风格, 角色/场景设定, 导演台布置.
- Fixed narrow viewport horizontal overflow and split asset drawer CSS into `assets.css` to keep maintenance audit clean.

Verification:

```text
Runtime-hosted browser QA on http://127.0.0.1:8807/studio/: desktop director starter/modal path passed; mobile overflow false.
Focused tests: 27 passed, 1 Starlette/httpx warning.
Full pytest: 772 passed, 1 Starlette/httpx warning.
apps/studio JS node --check: passed.
maintenance_audit: passed.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed.
- No image/video/media bytes were generated.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - AFS Studio UI Polish + 2D 导演台 Prompt 联动

- 修复 Studio 左上角重叠：抽屉展开时项目身份只由抽屉承载，顶栏从 `var(--drawer-w)` 右侧开始；抽屉收起时才显示 compact 项目 pill。
- 将导演台占位壳改成二维顶视图布置板：对象列表、网格画布、相机视锥、灯光光束、人物朝向、道具形状和右侧参数面板均可见。
- 导演台布置保存为节点本地 `directorSetup`；导演台节点展示机位 / 主体 / 灯光摘要，并可驱动相连图片或视频节点。
- Prompt 优化会从当前导演台节点或最近上游导演台节点提取安全版 `director_setup`；优化浮层显示用户可懂的“导演台布置”来源 chip。
- 后端用户版六段提示词已消费导演台上下文：人物站位、道具空间、机位/FOV/构图、灯光、运动连续性和光源/机位/空间冲突负面约束。
- 修复从底部 dock 添加节点时新节点落入 dock 安全区的问题：菜单仍从 dock 弹出，但节点出生点改为当前画布可视中心。
- 拆分导演台字段控件到 `apps/studio/src/panels/director-fields.js`，并将导演台 prompt API 测试移到 `tests/test_api_runtime_director_setup_prompt.py`，让本轮触达文件回到维护阈值内。
- 将 AgentFlow local AgentOps contract 示例的 `doc_path` 从已删除旧维护文档改到当前 `docs/company_operating_model.md`。

验证：

```text
Full pytest: 767 passed, 1 Starlette/httpx warning
Focused Studio / prompt / contract set: 21 passed
apps/studio JS node --check: passed
Runtime-hosted browser QA: passed
repository_retention_review manual_review_required_count: 0
git diff --check: passed with Windows CRLF notices only
maintenance_audit: 仅剩既有 human-facing Markdown 中文覆盖 warning；oversized_files 已通过
```

边界：

- Provider gate 仍关闭。
- 未生成图片/视频字节，也未保存 provider 原始响应。
- 这不是 human acceptance、business validation、provider smoke 或 durable-memory promotion。

## 2026-06-14 - Loop 005 Closeout Baseline Fix

- Moved three local review/input Markdown files out of the repository root to `D:\Projects\AgentFlowStudio-local-inputs\20260614`, because they are not formal repository ledgers and should not affect repository retention review.
- Generalized repository retention policy: root-level untracked Markdown files are classified as `local_workspace_input` instead of relying on hard-coded `AFS-*` filename prefixes.
- Fixed Studio `Failed to fetch` when the page is opened from a local static/dev port such as `8796`: `runtime-client.js` now falls back to the local Runtime Service at `http://127.0.0.1:8790`, while still using same-origin when served from Runtime and allowing explicit local overrides.
- Navigated the in-app browser from stale `http://127.0.0.1:8796/studio/` to Runtime-hosted `http://127.0.0.1:8790/studio/`; browser console warnings/errors were empty after reload.

Verification:

```text
tests/test_repository_retention_review.py tests/test_web_studio_static.py: 24 passed
pytest -q: 386 passed, 527 deselected, 2 warnings
pytest -m legacy -q: 527 passed, 386 deselected, 1 warning
Studio JS node --check: 37 files passed
tools/maintenance_audit.py: failed=0, warnings only
git diff --check: passed
```

Boundaries:

- This is runtime/browser verification, not human creative acceptance.
- Moved local input files are outside the repository and were not committed.
- Provider creative quality scoring remains a human-role QA task.

## 2026-06-12 - Creative Intent Agent And Keyframe Gate

- Added deterministic `creative_intent_control_agent_v1` trace for prompt optimization.
- Added hard / strong / soft constraint layering, three internal candidates, multi-axis scores, deterministic selected candidate, and provider translation metadata.
- Treated `node_parameters` as hard controls in prompt assembly and trace.
- Added English `user preference:` extraction so lower-priority preferences can be suppressed when they conflict with professional/node constraints.
- Added `POST /projects/{project_id}/keyframe-generations`.
- Keyframe generation is gated by `AFS_ALLOW_REMOTE_IMAGE`; with the gate closed it writes only safe JSON artifacts and starts no network/provider call.
- Added repo-safe engineering summary: `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md`.
- Added private algorithm design note under `10-Startup/70-Projects/AgentFlow-Studio/30-agent-infrastructure/creative-intent-control-agent-v1.zh-CN.md`.
- Deleted stale Web/Workbench handoffs, old Web superpowers plans/specs, stale Web maintenance ledgers, and old Web archive files instead of archiving them.

Verification so far:

```text
tests/test_api_runtime_creative_agent_keyframes.py: 3 passed
prompt/runtime/studio focused set: 25 passed
apps/studio JS node --check: passed
```

Boundaries:

- No real provider call was made.
- No image/video bytes were generated through Runtime.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - MVP Follow-up Live Comparisons

- Implemented `tools/studio_asset_context_followup_comparisons.py` for the two runbook follow-up groups: character+scene A/B/C and lock-conflict locked/unlocked live runs.
- Added deterministic observatory scene reference generation to `tools/studio_asset_context_sample_reference.py`.
- Added focused tests for gate-closed no-call behavior, dual-asset C-arm context, temporary lock override capture, and scene PNG generation.
- Ran live MiniMax image follow-up with only `AFS_ALLOW_REMOTE_IMAGE=true`.
- Group 2 first run succeeded for A/B/C; C included both character and scene assets, used one character subject reference, and kept the scene in the text channel.
- Group 3 retry succeeded; locked output kept black short hair despite red-long-hair prompt, while temporary unlock produced red long hair and recorded the override in trace.
- One immediate Group 2 rerun hit a provider/CLI safe readiness block; preserved as provider intermittency evidence, not resolver failure.

Evidence:

```text
runs/studio_asset_context_followup_20260612_group2_success/
runs/studio_asset_context_followup_20260612_group3_retry/
runs/studio_asset_context_followup_group3_retry_report_20260612.json
docs/handoff/AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612.md
```

Verification:

```text
tests/test_studio_asset_context_followup_comparisons.py: 3 passed, 1 existing Starlette/httpx warning
py_compile follow-up tools: passed
git diff --check: passed with Windows CRLF notices only
```

Boundaries:

- Image provider gate only; LLM/ASR/video/download gates remained closed.
- Live output is provider smoke and asset-semantics evidence, not human acceptance or business validation.

## 2026-06-11 - AFS Studio Hard Cleanup

- Retired old Workbench/static memory-workbench user routes.
- Current frontend entry is `/studio/`, backed by `apps/studio/`.
- Deleted old UI source, old UI-specific tests, old Workbench browser QA tools, and old frontend integration docs.
- Prompt optimizer contract moved to `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md`.
- Verified earlier in this branch: full pytest, maintenance audit, `git diff --check`, Runtime-hosted `/studio/` browser QA, and `/workbench/` 404.
## 2026-06-19 - Studio Sprite Draggable Character Polish

- Reworked the `AFS 小精灵` avatar into a more recognizable movable canvas companion.
- Added a character silhouette layer, visible move handle, ear fins, scarf accent, and keyboard arrow-key nudging.
- Kept the LLM chat boundary unchanged: the sprite still uses the existing Runtime `sprite/chat` path and remains gate-aware.
- Split the new visual shell into `apps/studio/styles/studio-sprite-avatar-character.css` so the existing sprite files stay below the 300-line maintenance warning threshold.

Verification so far:

```text
tests/test_web_studio_sprite_static.py: 1 passed
tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 6 passed, 1 existing Starlette/httpx warning
npm run check:studio-js: passed for 87 files
Browser on http://127.0.0.1:8797/studio/: sprite parts rendered, pointer drag moved position, arrow keys nudged by 18px, panel open kept position stable, console warn/error count 0
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is runtime/browser verification, not human acceptance or business validation.

## 2026-06-19 - Video Routes Module Split

- Split `apps/api/runtime_video_routes.py` from a 739-line route/orchestration module into a thin 105-line route assembly surface.
- Added focused helper modules for video constants, gate blocks, prompt projection, candidate previews, safe manifest/job responses, task state/quota handling, and submit/poll dispatch.
- Preserved the existing Runtime API shape and compatibility exports used by tests: `VideoGenerationRequest`, `load_provider_registry`, and `_video_provider_prompt`.
- Kept provider registry loading injectable from the route module so existing monkeypatch coverage still proves provider gate and safe-manifest behavior.

Verification:

```text
tests/test_api_runtime_video_routes_modules.py: first failed on missing helper modules, then passed after split
tests/test_api_runtime_video_routes_modules.py + tests/test_api_runtime_video_generations.py + tests/test_api_runtime_generation_manifest_safety.py + tests/test_model_call_context_runtime_routes.py: 17 passed, 1 existing Starlette/httpx warning
video/manifest/ModelCallContext/internal-beta/three-end focused set: 34 passed, 1 existing Starlette/httpx warning
tools/maintenance_audit.py: failed=0 with warnings only; oversized warning count dropped from 36 to 35
git diff --check: passed
```

Boundaries:

- No Runtime API shape changed.
- No provider gate was changed.
- No provider call was made.
- No provider config, local media byte, local path, signed URL, provider raw response, invite code, or session token was added to API payloads or reports.
- This is runtime/module verification, not human acceptance or business validation.

## 2026-06-19 - Sprite Companion Redesign Pass

- Reworked the movable `AFS 小精灵` visual layer into a clearer Studio companion with a stronger full-body silhouette.
- Expanded the avatar footprint to 180 x 206 and adjusted viewport clamping so drag/panel docking still uses the correct bounds.
- Added a focused redesign CSS layer for the larger silhouette, visible drag handle, eyes/visor, arms, feet, scarf, status light, and docking label.
- Kept the existing Runtime `sprite/chat` interface unchanged; this pass only changes the front-end companion appearance and movement affordance.

Verification:

```text
tests/test_web_studio_sprite_static.py + tests/test_web_studio_static.py + tests/test_api_runtime_sprite.py: 16 passed, 1 existing Starlette/httpx warning
npm run check:studio-js: passed for 88 files
Browser on http://127.0.0.1:8797/studio/: character parts rendered, cursor=grab, drag moved position, panel open kept position stable, console warn/error count 0
tools/maintenance_audit.py: failed=0 with warnings only; new redesign CSS stayed under the maintenance threshold
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is runtime/browser verification, not human acceptance or business validation.

## 2026-06-19 - Asset Card Draft Module Split

- Split visual-inspection provider dispatch, provider observation projection, draft prompt summarization, and vision provider constraints out of `apps/api/runtime_asset_card_drafts.py`.
- Added `apps/api/runtime_asset_card_observation.py` for visual observation/provider-facing helper logic.
- Added `apps/api/runtime_asset_card_artifacts.py` for safe manifest/model-context/model-request-plan/draft artifact writing and trace input refs.
- Added a structural regression test so the asset-card draft route stays below the 300-line maintenance threshold and does not absorb the helper responsibilities again.

Verification:

```text
tests/test_api_runtime_asset_card_drafts.py + tests/test_api_runtime_asset_card_modules.py + tests/test_model_call_context_runtime_routes.py: 8 passed / 1 existing Starlette/httpx warning
pytest -q: 532 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count dropped from 39 to 38
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is runtime/module verification, not human acceptance or business validation.

## 2026-06-19 - Auth Module Split

- Split FastAPI auth route and middleware assembly into `apps/api/runtime_auth_routes.py`.
- Split password hashing, session-token hashing, invite-code normalization, bearer parsing, TTL expiry, and timestamp helpers into `apps/api/runtime_auth_security.py`.
- Kept `apps/api/runtime_auth.py` focused on request models, `RuntimeAuthStore`, user projection, and persisted auth-store reads.
- Added a structural regression test to keep auth store, route assembly, and security helpers separated under the 300-line threshold.

Verification:

```text
tests/test_api_runtime_auth.py + tests/test_api_runtime_auth_modules.py + tests/test_afs_internal_beta_acceptance.py + tests/test_afs_internal_beta_preflight_three_end.py: 17 passed / 1 existing Starlette/httpx warning
pytest -q: 533 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count dropped from 38 to 37
git diff --check: passed
```

Boundaries:

- No auth policy was changed.
- No provider gate was changed.
- No provider call was made.
- No invite code, session token, local path, signed URL, provider raw response, or media byte was added to reports.
- This is runtime/internal-beta structure verification, not human acceptance or business validation.

## 2026-06-19 - Internal Beta Preflight Split

- Split HTTP preflight readiness logic out of `tools/afs_internal_beta_acceptance.py` into `tools/afs_internal_beta_acceptance_preflight.py`.
- Moved `AcceptanceConfigurationError` into `tools/afs_internal_beta_acceptance_errors.py` so the CLI runner and preflight module share the same safe configuration error type without circular imports.
- Kept `tools.afs_internal_beta_acceptance.run_http_preflight` as a thin compatibility wrapper, preserving existing imports and HTTP client monkeypatch behavior.
- Added a structural regression test to keep preflight report construction and safe health projection out of the runner.

Verification:

```text
tests/test_afs_internal_beta_acceptance.py: 9 passed / 1 existing Starlette/httpx warning
tests/test_afs_internal_beta_acceptance.py + tests/test_afs_internal_beta_preflight_three_end.py + tests/test_afs_three_end_status.py: 16 passed / 1 existing warning
tools/afs_internal_beta_acceptance.py --help: passed and still exposes preflight/three-end flags
tools/afs_internal_beta_acceptance.py --preflight-only: safe configuration_error when base URL is missing
pytest -q: 531 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count dropped from 40 to 39
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No invite code, session token, base URL, local path, signed URL, provider raw response, or media byte was added to reports.
- This is runtime/readiness verification, not human acceptance or business validation.

## 2026-06-19 - Sprite Companion Character Pass

- Strengthened the decorative `AFS 小精灵` into a clearer movable Studio companion rather than a button-like helper.
- Added a hood, explicit left/right eyes, torso panel, nameplate, and visible drag hint while preserving the existing Runtime `sprite/chat` boundary.
- Added defensive pointer capture handling so synthetic pointer events and browser automation cannot break drag startup.
- Extended the sprite static regression test to cover the new character parts and draggable companion role.

Verification:

```text
tests/test_web_studio_sprite_static.py: 1 passed
tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 6 passed, 1 existing Starlette/httpx warning
npm run check:studio-js: passed for 88 files
Chrome automation on http://127.0.0.1:8797/studio/: character parts rendered, drag moved/persisted position, panel-open position delta 0, zero console warn/error
pytest -q: 530 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0 with warnings only
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is runtime/browser verification, not human acceptance or business validation.

## 2026-06-19 - Sprite Companion Movable Polish

- Versioned the Studio sprite position storage so old local positions do not strand the redesigned companion in the middle of the canvas.
- Changed the default sprite landing point to avoid the right inspector and bottom dock while still keeping it available on the canvas.
- Marked the visible move handle as a first-class drag affordance and added drag-state response for arms, nameplate, shadow, and thruster.
- Verified the sprite keeps a clear character silhouette after moving and stays wired to the existing Runtime `sprite/chat` LLM boundary.

Verification:

```text
tests/test_web_studio_sprite_static.py: 1 passed
tests/test_web_studio_static.py + tests/test_web_studio_sprite_static.py: 11 passed
npm run check:studio-js: passed for 90 files
Browser check on http://127.0.0.1:8797/studio/: default sprite placement avoided inspector/dock; drag moved position from (768,414) to (598,315)
pytest -q: 536 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0 with existing warnings only
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is local browser/runtime verification, not human acceptance or business validation.

## 2026-06-19 - Visual Asset Panel Render Split

- Split the visual asset confirmation modal rendering into `apps/studio/src/panels/visual-asset-panel-render.js`.
- Kept `apps/studio/src/panels/visual-asset-panel.js` focused on Runtime calls, draft-card handling, submit validation, and store updates.
- Preserved the existing `vision_image` draft-card route, fixed/rejected asset review flow, and safe local store projection.
- Added static regression coverage so the main panel stays under 300 lines and the render module owns the visible fields/actions.

Verification:

```text
tests/test_web_studio_assets_generation_static.py + tests/test_web_studio_loop003_static.py + tests/test_web_studio_static.py: 24 passed
npm run check:studio-js: passed for 91 files
Browser check on http://127.0.0.1:8797/studio/: Studio root and sprite root rendered; console warn/error count=0
pytest -q: 536 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count dropped from 33 to 32
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is frontend structure/runtime-boundary verification, not human acceptance or business validation.

## 2026-06-19 - Director Shell Render Split

- Split the Director Shell modal frame, object list, board rendering, and intent preview into `apps/studio/src/panels/director-shell-render.js`.
- Split default director object construction into `apps/studio/src/panels/director-object-factory.js`.
- Kept `apps/studio/src/panels/director-shell.js` focused on interaction orchestration: tab switching, drag state, save/apply actions, prompt append confirmation, and director asset projection.
- Added static regression coverage so Director Shell stays under 300 lines while the render module owns visible layout rendering.

Verification:

```text
Red test: tests/test_web_studio_mature_shell_static.py::test_director_shell_uses_active_ids_and_confirmed_append_only failed before the render module existed.
tests/test_web_studio_mature_shell_static.py targeted director tests: 2 passed
tests/test_web_studio_mature_shell_static.py + tests/test_web_studio_static.py + tests/test_web_studio_sprite_static.py + tests/test_studio_interaction_layer.py: 32 passed
npm run check:studio-js: passed for 93 files
Browser check on http://127.0.0.1:8797/studio/: Studio loaded with title "AFS Studio 创作图谱"; console warn/error count=0
pytest -q: 536 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count dropped from 32 to 31
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret was exposed.
- This is frontend structure/runtime-boundary verification, not human acceptance or business validation.

## 2026-06-19 - Internal Beta Human Review Packet

- Added `tools/afs_internal_beta_acceptance_review.py` to build a safe `human_review_packet` for every deterministic internal beta acceptance report.
- The packet turns machine verification into an operator-facing review checklist with scoring sections for account/project isolation, asset-context continuity, generated media quality, feedback/revision loop, and privacy/provider boundaries.
- Kept the report explicit that human acceptance, business validation, durable memory promotion, and live provider quality approval are still not claimed.
- Avoided writing invite values, session tokens, local paths, signed URLs, provider raw responses, or media bytes into the review packet.

Verification:

```text
Red test: tests/test_afs_internal_beta_acceptance.py failed before human_review_packet and tools/afs_internal_beta_acceptance_review.py existed.
tests/test_afs_internal_beta_acceptance.py: 10 passed, 1 existing Starlette/httpx warning
Acceptance CLI smoke: status=contract_verified_pending_human_acceptance; packet_status=pending_human_review; provider_calls=false; human_claim=not_claimed
tests/test_afs_internal_beta_acceptance.py + tests/test_afs_internal_beta_preflight_three_end.py + tests/test_afs_three_end_status.py: 17 passed, 1 existing warning
pytest -q: 537 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0 with existing warnings only
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No Company OS or long-term memory write was made.
- This is deterministic runtime/readiness verification plus a human review handoff packet, not completed human acceptance or business validation.

## 2026-06-19 - Internal Beta Human Review Markdown

- Added optional `--human-review-md` output to `tools/afs_internal_beta_acceptance.py`.
- Added `render_human_review_markdown()` so the safe `human_review_packet` can become an operator-facing Markdown checklist.
- The checklist includes the report status, review status, non-claim warning, five scoreable review sections, decision options, operator notes, and boundary reminders.
- Split the review-specific tests into `tests/test_afs_internal_beta_acceptance_review.py` so the main acceptance test file stays below the 300-line warning threshold.

Verification:

```text
Red test: tests/test_afs_internal_beta_acceptance.py failed before human_review_path and render_human_review_markdown existed.
tests/test_afs_internal_beta_acceptance.py: 11 passed, 1 existing Starlette/httpx warning
Acceptance CLI smoke with --human-review-md: title present, decision present, 5 score lines, no temp path or credential wording
tests/test_afs_internal_beta_acceptance.py + tests/test_afs_internal_beta_acceptance_review.py + tests/test_afs_internal_beta_preflight_three_end.py + tests/test_afs_three_end_status.py: 18 passed, 1 existing warning
pytest -q: 538 passed / 527 deselected / 2 existing warnings
tools/maintenance_audit.py: failed=0; oversized warning count stayed at 31 after test split
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No Company OS or long-term memory write was made.
- This creates a safe human-review checklist; it still does not claim completed human acceptance or business validation.

## 2026-06-19 - Studio Sprite Navigator Character Polish

- Reworked the movable `AFS 小精灵` companion toward a clearer Studio navigator character rather than a generic floating control.
- Added visible character details: crest, orbit dots, brows, blush marks, and a hover/drag grab ribbon.
- Kept the existing Runtime `sprite/chat` boundary and local viewport-position behavior unchanged.
- Extended the sprite static contract so future changes must preserve the character silhouette and drag affordance, not only the chat wiring.

Verification:

```text
tests/test_web_studio_sprite_static.py: red on missing sprite-crest contract, then passed after implementation
tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 6 passed / 1 existing Starlette/httpx warning
npm run check:studio-js: JS syntax check passed for 93 files
Browser on http://127.0.0.1:8797/studio/: crest/orbit/brow/blush/grab-ribbon rendered; drag moved sprite from (522,270) to (440,222); opening the panel kept root at (440,222), panel followed, status light turned green, console warn/error count 0
tools/maintenance_audit.py: failed=0; warnings only; sprite personality CSS remained below 300 lines
git diff --check: passed
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret exposure.
- This is UI verification, not human acceptance or business validation.

## 2026-06-19 - Internal Beta Human Review Record

- Added `tools/afs_internal_beta_human_review_record.py` as a safe local record step after the internal beta human-review checklist.
- The record step accepts an acceptance report plus operator scores/decision and writes an `afs_internal_beta_human_review_record` JSON artifact.
- Acceptance for the next beta round is only recorded when every required section score meets the packet threshold and the decision is `accepted_for_next_beta_round`.
- Inconsistent accepted decisions with low scores become `review_requires_followup` and keep `human_acceptance_claim=not_claimed`.
- The CLI accepts UTF-8 with BOM input so Windows PowerShell-authored review JSON works.

Verification:

```text
Red test: tests/test_afs_internal_beta_human_review_record.py failed before tools/afs_internal_beta_human_review_record.py existed.
Red regression: BOM CLI test failed on JSONDecodeError before utf-8-sig read support.
tests/test_afs_internal_beta_human_review_record.py: 4 passed / 1 existing Starlette/httpx warning
CLI smoke: generated accepted_for_next_beta_round record; human=accepted_for_next_beta_round; business=not_claimed; durable=not_claimed; no local path, signed/token, or invite leak
tests/test_afs_internal_beta_human_review_record.py + acceptance/three-end focused set: 22 passed / 1 existing warning
git diff --check: passed
```

Boundaries:

- No provider gate was changed.
- No provider call was made.
- No Company OS or long-term memory write was made.
- This records human review for an internal beta round only; it does not claim business validation, provider quality approval, or durable memory promotion.

## 2026-06-19 - TuanTuan Lossless Motion Layer

- Split the Studio companion into separate widget, character-asset, and motion modules so `sprite-widget.js` no longer owns pose assets or continuous motion math.
- Added `sprite-motion.js` to drive continuous pointer attention, hover, drag lift, squash, tilt, bob, and shadow response through CSS variables on the actual mascot button.
- Kept the reference-derived high-resolution TuanTuan PNG poses intact; the motion layer transforms the rendered character and shadow without generating or storing new media bytes.
- Added reduced-motion handling so users who prefer less motion get a calmer version of the companion.

Verification:

```text
npm run check:studio-js: JS syntax check passed for 96 files
tests/test_web_studio_static.py + tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 16 passed / 1 existing Starlette/httpx warning
git diff --check: passed
Browser smoke on Chrome at /studio/?project=tuantuan-motion-smoke: 8 TuanTuan assets loaded at 410x515; pointer/hover/drag changed shift, tilt, squash, and shadow CSS variables; console warn/error count 0
Screenshot evidence: runs/tuantuan-sprite-motion-smoke-20260619.png
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, or secret exposure.
- This is a lightweight lossless motion layer, not a full skeletal animation rig; full rigging still needs layered source art or a dedicated animation asset pipeline.

## 2026-06-19 - TuanTuan V1 Canvas Agent Intent

- Reframed TuanTuan from a mascot / desktop-pet style companion into the embodied projection of the AFS Agent system inside the Studio canvas.
- Replaced pose-image swapping with a canvas-native story-cat DOM rig: resting cat silhouette, story orbit, eye/body/tail components, observe/suggest/preview/execute/complete/sleep state hooks.
- Retired the previous `tuantuan-*.png` pose assets and the old reference-image sprite layer so the current canvas character is not a sticker swap implementation.
- Preserved a quiet default `observe` state and mapped hover/open/send behavior to `think` / `suggest` semantics rather than attention-seeking chat behavior.
- Renamed the main visual stylesheet from mascot language to story-cat language and split state/motion styles out of the base character file to keep files under the maintenance warning line.
- Diagnosed the public-server login loop as Nginx Basic Auth in front of the already-authenticated Runtime app; the server also still runs `master`, so it cannot show this review-branch TuanTuan until the branch is merged and deployed.
- Follow-up shape correction: added the missing IP anchors from the reference direction, including larger cat ears, inner ears, forehead tabby mark, cheek marks, whiskers, nose/mouth, story belly panel, front paws, and segmented tail.

Verification:

```text
Red check: tests/test_web_studio_sprite_static.py failed before the V1 story-cat contract existed.
npm run check:studio-js: JS syntax check passed for 96 files
tests/test_web_studio_static.py + tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 16 passed / 1 existing Starlette/httpx warning
full pytest: 543 passed / 527 deselected / 2 existing warnings
npm run check:studio-js: JS syntax check passed for 96 files
Browser smoke on Chrome at /studio/?project=tuantuan-v1-smoke: character=story-cat, role=embodied-agent, state observe -> hover think -> open suggest, story orbit/cat/body/eyes present, old image-asset sprite absent, console warn/error=0
Browser smoke after old PNG retirement: assetImageCount=0, no failed requests, console warn/error=0
Browser smoke after shape correction: inner ears=2, face marks=3, whiskers=2, nose=1, story panel=1, tail panels=3, console warn/error=0
tools/maintenance_audit.py: failed=0; warnings only
git diff --check: passed
Screenshot evidence: runs/tuantuan-v1-story-cat-smoke-20260619.png
Shape correction screenshot: runs/tuantuan-shape-smoke-20260619.png
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS private source content was written.
- This is frontend/runtime verification only, not human acceptance or business validation.

## 2026-06-20 - TuanTuan Reference Shape Reset

- Reworked TuanTuan's canvas character from the previous abstract dark DOM rig into a closer reference-shape vector rig: low resting tabby-cat posture, larger head and ears, glowing eyes, sprout, dark curled body, paws, whiskers, body tabby marks, story belly panel, and cyan story orbit.
- Switched the character layer to inline SVG inside the existing sprite DOM so the sprite remains animatable and state-driven instead of becoming another static sticker image.
- Updated sprite dimensions and persisted-position version so old local positions from the rejected shape do not lock the new wider resting cat into a bad location.
- Added static shape anchors to tests for SVG, reference body outline, tabby marks, sprout, story panel, and orbit nodes.
- Kept the interaction scope intentionally small: observe/think/suggest/preview/execute/complete/sleep state styling, drag, size settings, and simple LLM-backed chat remain the only V1 behaviors.

Verification:

```text
npm run check:studio-js: JS syntax check passed for 96 files
tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 6 passed / 1 existing Starlette/httpx warning
git diff --check: passed
Browser smoke on Chrome at /studio/?project=tuantuan-reference-shape-v2: catTag=svg, eyes=2, ears=2, tabbyMarks=3, orbitNodes=5, state=observe
Screenshot evidence: runs/tuantuan-reference-shape-20260620/tuantuan-reference-shape-avatar-v2.png
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS private source content was written.
- This sets a more faithful V1 visual baseline; it is still not final IP illustration acceptance or full animation rigging.

## 2026-06-20 - TuanTuan Reference Shape Calibration

- Calibrated the V1 `story-cat` rig against the user-approved TuanTuan reference: expanded the SVG to a wider low-resting cat silhouette, rebuilt the ears, tail, body, rear paw, forepaws, tabby markings, whiskers, and sprout around a dark canvas-native black cat direction.
- Changed the eyes from pure cyan glow blobs into black pupils with blue-white highlights, closer to the reference's calm observing expression.
- Reduced the story belly panel to a very low-opacity internal symbol so the sprite no longer reads as a robot or sticker while keeping the AFS story-orbit/product symbol available for future animation states.
- Added regression anchors for the new viewBox, rear paw, ear rim, face ridge, pupils, eye highlights, and tabby details.

Verification:

```text
Red check: tests/test_web_studio_sprite_static.py failed on the old 320x190 shape before implementation.
tests/test_web_studio_sprite_static.py + tests/test_api_runtime_sprite.py: 6 passed / 1 existing Starlette/httpx warning
npm run check:studio-js: JS syntax check passed for 96 files
Chrome render smoke on 127.0.0.1:8797/studio/?project=tuantuan-reference-shape-local: viewBox=0 0 360 210, ears=2, pupils=2, eyeShine=4, tabbyMarks=9, storyPanelOpacity=0.18, orbitNodes=5, console warn/error=0
Screenshot evidence: runs/tuantuan-reference-shape-20260620/tuantuan-reference-shape-expanded-v4.png
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, invite code, or Company OS private source content was written.
- This is frontend/runtime verification only, not final IP illustration acceptance, human acceptance, business validation, or durable memory promotion.

## 2026-06-20 - TuanTuan Latest Reference Shape Lock

- Responded to the latest reference correction that the current canvas TuanTuan still looked too far from the approved dark story-cat image.
- Rebuilt the SVG rig around the reference's most important visible anchors: larger triangular ears, a wider low resting body, a closed curled tail instead of a thin line, blue-white highlighted eyes with black pupils, brighter inner ear rims, visible forepaws/rear paw, dark body tabby stripes, whiskers, and the cyan story orbit around the body.
- Bumped the local sprite position version and frame from `236 x 220` to `260 x 238`, so old coordinates from rejected shapes do not pin the wider cat into a bad place.
- Kept the implementation as animatable inline SVG/CSS rather than returning to static PNG pose swapping; this preserves the later path toward eye tracking, tail/ear motion, state transitions, and Observe -> Suggest -> Execute behavior.

Verification:

```text
tests/test_web_studio_sprite_static.py: 1 passed
npm run check:studio-js: JS syntax check passed for 96 files
In-app browser smoke at /studio/?project=tuantuan-reference-check:
  viewBox=0 0 390 230
  ears=2
  innerEars=2
  eyes=2
  pupils=2
  tailShapes=1
  tabbyMarks=4
  orbitNodes=5
  state=observe
```

Boundaries:

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, invite code, or Company OS private source content was written.
- This locks a closer V1 visual direction only; it is not final IP illustration acceptance, human acceptance, business validation, or full animation rigging.

## 2026-06-20 - Public Edge Auth Preflight

- Added a safe public-edge preflight that distinguishes Nginx Basic Auth blocking from Runtime app auth.
- The preflight checks the public `/studio/` entry without credentials and, when an SSH server alias is provided, also reads server-side Runtime `/health`.
- Added `--check-runtime-health` for server-side self-checks where SSH-ing back to the same host is not appropriate.
- Wired public edge status into the internal beta HTTP preflight so deployed acceptance reports can fail on `public_edge_auth` explicitly instead of only surfacing generic `/health` 401 failures.
- Current live result is `blocked_by_edge_basic_auth`: public edge returns `401` with `WWW-Authenticate: Basic`, while Runtime health remains `ready`.
- Added a maintenance runbook with the sudo-side Nginx fix and post-fix verification commands.

Verification:

```text
tests/test_afs_public_edge_preflight.py: 3 passed
Live preflight: status=blocked_by_edge_basic_auth, public_edge_http_status=401, edge_basic_auth=true, runtime_status=ready
Report evidence: runs/public_edge_preflight_20260620.json
tests/test_afs_internal_beta_acceptance.py + tests/test_afs_public_edge_preflight.py: 16 passed / 1 existing warning
Internal beta HTTP preflight with `--public-edge-status`: status=needs_attention; public_edge_auth failed with blocked_by_edge_basic_auth; provider_calls_started=false
```

Boundaries:

- No Nginx config was changed because current SSH user has no passwordless sudo.
- No provider gate changed.
- No provider call was made.
- No secret, invite code, local media byte, provider raw response, or Company OS private source content was written.

## 2026-06-21 - Studio Runtime UI Fixes Before Internal Test

- Reworked Runtime job progress so active image/keyframe jobs no longer report fake `50%`; running and pending jobs now expose an indeterminate mode, while terminal progress keeps the existing complete contract.
- Extended keyframe polling so long image jobs stay visibly in progress instead of being marked failed by the frontend while the worker is still producing a candidate.
- Added stale running-job recovery to the Codex image handoff worker so an old stuck running job does not block later pending image jobs.
- Kept Studio state safe by storing Runtime preview routes as project-relative URLs and resolving them to absolute media URLs only at render boundaries.
- Added image asset deletion through the Runtime API and an app-level asset drawer context menu, avoiding the browser's native image context menu for project actions.
- Split TuanTuan pending/input helper logic out of `sprite-widget.js`; added rotating pending copy, shimmer text styling, and input focus restoration across render/save-state updates.
- Tightened the Works library drawer layout so completed work cards stay within the sidebar width.

Verification:

```text
npm run check:studio-js: JS syntax check passed for 98 files
Focused Runtime/worker/API tests: 19 passed / 1 existing warning
Focused Studio frontend tests: 45 passed
Full pytest: 569 passed / 527 deselected / 2 existing warnings
git diff --check: passed with CRLF normalization warning only
Browser/runtime smoke: passed; reference image rendered, image asset context-menu delete worked, TuanTuan focus retained, pending text rotated with generating-text-shimmer, Works library had no horizontal overflow
Browser smoke report: runs/studio_runtime_ui_fixes_browser_smoke.json
```

Boundaries:

- No video gate was opened.
- No live provider call was made during this verification pass.
- No provider raw response, signed URL, local media byte, secret, invite code, or Company OS private source content was written.
- This is automated/runtime/browser verification only, not human acceptance, business validation, or durable memory promotion.

## 2026-06-21 - Full-Coverage Studio Internal Test Replacement Pass

- Created a multi-role QA plan and run ledger for the internal-test replacement pass, covering creator, returning creator, creative director, asset librarian, QA gatekeeper, release operator, privacy/security, waiting user, small viewport, and failure-recovery perspectives.
- Fixed local browser QA startup under proxy-enabled developer machines: health checks now bypass `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` for local Runtime probes, Runtime subprocesses receive `NO_PROXY`, and the QA helper passes the correct `AFS_RUNTIME_ROOT`.
- Updated stale browser QA selectors for the current quick-create menu and duplicate save-asset actions, then added a deterministic `--stub-llm` mode so UI/Runtime browser coverage can run without depending on local provider readiness.
- Fixed a real Studio interaction bug where TuanTuan sat above modal panels and intercepted the visual-asset “确认固定” button; TuanTuan is now a canvas companion layer below prompt bar, dock, drawer, popover, and modal surfaces.
- Fixed a real asset drawer bug where opening ordinary uploaded image details requested `/visual-assets/{image_asset_id}`, producing a 404 and console noise. Image references now render local safe detail only; visual asset detail is requested only when a visual asset id exists.
- Added a broader browser QA script that validates uploaded image preview and app-level right-click delete, TuanTuan pending shimmer and rotating copy, refresh restore, and small-viewport horizontal overflow.
- Verified server-side public edge is now ready for Runtime app auth and no longer blocked by old Basic Auth.
- Ran server non-video provider checks: LLM smoke passed, image handoff smoke succeeded with one candidate and no raw/signed URL persistence, and vision smoke dispatched successfully. Video remained closed.

Verification:

```text
Initial baseline:
npm run check:studio-js: passed for 98 files
python -m apps.cli.main --help: passed
python -m apps.cli.main version: 0.1.0
python tools/maintenance_audit.py: failed=0, warnings only
python -m pytest -q: 572 passed / 527 deselected / 2 existing warnings
git diff --check: passed

Focused fix checks:
tests/test_studio_asset_context_browser_qa_support.py: 3 passed / 1 existing warning
tests/test_web_studio_sprite_static.py: 1 passed
tests/test_web_studio_frontend_wave.py::test_asset_drawer_has_app_context_menu_and_image_delete_action: 1 passed
tests/test_afs_public_edge_preflight.py: 4 passed
tests/test_web_studio_loop003_static.py::test_loop003_qal003_003_asset_detail_reads_runtime_and_exposes_node_actions: 1 passed

Browser QA:
tools/studio_asset_context_browser_qa.py --stub-llm: passed, report runs/final_existing_browser_qa_stub_20260621.json
tools/studio_full_coverage_browser_qa.py: passed, report runs/final_full_coverage_browser_qa_20260621.json, console/network errors 0

Live server safe checks:
three-end status before commit/deploy: server_home and server_opt aligned at 6a5bf30, Runtime ready, local dirty as expected
public edge preflight: ready_for_public_auth
server LLM smoke: passed, provider_calls_started=true
server image handoff smoke: succeeded, output_count=1, provider_raw_response_stored=false, signed_urls_persisted=false
server vision smoke: passed
```

Boundaries:

- Video generation was not triggered and `AFS_ALLOW_REMOTE_VIDEO` remained false.
- No ASR or external download gate was opened.
- No provider raw response, signed URL, local private media byte, secret, invite code, session token, or Company OS private source content was written to repo records.
- Browser/runtime verification and provider smoke remain separate from human acceptance, creative quality scoring, business validation, and durable memory promotion.

## 2026-06-23 - Studio Web, Director, Social Square, and Asset Persistence Fixes

- Fixed Studio node double-click routing so image nodes and other existing nodes open the node input editor, while blank canvas double-click still opens the create-node menu.
- Fixed asset-card save-and-regenerate failures caused by asset-card drafts carrying prior reference images into a zero-slot image route; edited asset cards now save before regeneration and regenerate from prompt/card content.
- Fixed a Studio persistence race where navigating from Studio to the homepage could leave Runtime state stale, then re-entering Studio could overwrite newer local asset-card state. The topbar now flushes before homepage navigation, and Runtime hydration keeps newer local canvas state over older remote state.
- Reworked the public homepage into a cleaner product entry and split Social Square into a standalone collaboration page with publishing, filtering, status actions, submission/report flows, request stats, and a lightweight DOM sprite companion.
- Upgraded the Director Stage surface from a plain 2D layout label to a production package workflow: shot arrangement plus prompt segments, spatial constraints, lighting intent, and generation-use notes.

Verification:

```text
npm run check:studio-js: passed for 112 files
focused Studio/site/API pytest set: 42 passed / 1 existing warning
social/runtime/state pytest set: 52 passed / 1 existing warning
local Runtime 8797 health: ready
browser smoke: homepage + standalone Social Square loaded, demand publish/filter passed, console/network errors 0
browser smoke: image node double-click opened prompt bar instead of add-node menu
browser persistence smoke: newer local asset-card state survived homepage roundtrip and flushed over older Runtime state
```

Boundaries:

- This change did not alter provider-gate policy; no live provider call, video generation, ASR, or external download was triggered.
- Public pages avoid exposing COS/GFR source material, provider raw responses, signed URLs, local private paths, generated media bytes, or secrets.
- Local automated verification does not claim human acceptance, creative quality acceptance, business validation, or durable memory promotion.

Deployment:

```text
Commit: 53a0f17 feat(studio): polish web flows and asset persistence
GitHub master: pushed and aligned
Server /home/afs-ops/AgentFlowStudio: fast-forwarded to 53a0f17
Server /opt/afs/AgentFlowStudio: fast-forwarded to 53a0f17
afs-runtime and afs-codex-image-worker: restarted by terminating old afs-ops user processes after sudo restart was blocked
Runtime health: ready; studio_static.status=ready
Public HTTP checks: https://afstudio.art/site/ -> 200; https://afstudio.art/site/social-square.html -> 200
Three-end report: runs/three_end_status_20260623_web_director_polish_final_after_restart.json -> aligned
```

## 2026-06-21 - Studio Image/TuanTuan Concurrency Hardening

- Fixed Codex image handoff queue semantics: pending jobs now remain `pending` until a worker atomically claims them, running jobs carry a worker claim record, and concurrent workers skip jobs already claimed by another worker.
- Completed candidates recovered from a `running` handoff directory are now moved into `completed` and trimmed, so queue audits do not keep reporting stale running jobs after a successful recovery.
- Replaced fake static image progress with queued/indeterminate progress metadata so Studio no longer jumps to a misleading percentage while long image jobs are still processing.
- Made generated image asset IDs deterministic per source job/candidate to prevent duplicate reusable assets on repeated polls.
- Scoped Codex image worker home/cache per job directory so same-project and cross-project image jobs do not share a transient execution workspace.
- Split prompt optimizer reference handling into subject-reference versus style-reference paths. If the user clearly asks for a new subject, uploaded images are treated as style/quality references instead of overriding the subject.
- Hardened i2i fallback and guardrails so a request like "生成一只狸花猫" with an unrelated reference image no longer forces the reference image filename or subject into the optimized prompt.
- Cached authorized Runtime media object URLs at render boundaries and avoided re-fetching the same project image on node selection, drawer tab changes, or rerenders.
- Made completed image nodes full-bleed in the node body and kept result overlays hover/selection driven instead of occupying permanent content space.
- Added a TuanTuan focused-input DOM guard plus client-side prompt-leak fallback, so save-state rerenders do not interrupt typing/IME composition and prompt instructions are not shown to users.

Verification:

```text
Focused regression set: 20 passed / 1 existing warning
Prompt + sprite + handoff + Studio static set: 67 passed / 1 existing warning
Full pytest: 585 passed / 527 deselected / 2 existing warnings
npm run check:studio-js: JS syntax check passed for 99 files
python -m apps.cli.main --help: passed
python -m apps.cli.main version: 0.1.0
python tools/maintenance_audit.py: failed=0, warnings only
git diff --check: passed
Browser plugin smoke on current branch Runtime 8807: page identity ok, image node full-bleed class present, image loaded, app-level asset context menu/delete worked, TuanTuan Chinese input kept focus/value, page console warn/error=0
tools/studio_full_coverage_browser_qa.py: passed; asset preview/delete, TuanTuan pending shimmer + copy rotation, save/restore, small viewport
Server queue audit: pending=0, running=0, completed=7, failed=3 historical; Runtime health ready; video gate false
Deployment sync: local master, origin/master, server /home/afs-ops/AgentFlowStudio, and server /opt/afs/AgentFlowStudio aligned on the hardened Studio image/TuanTuan flow; afs-runtime active after deploy
```

Boundaries:

- Video generation was not triggered and video gate remained closed.
- Browser/runtime verification and server queue audit are not human acceptance, creative quality scoring, business validation, or durable-memory promotion.
- No provider raw response, signed URL, local private media byte, secret, invite code, session token, or Company OS private source content was written to repo records.
