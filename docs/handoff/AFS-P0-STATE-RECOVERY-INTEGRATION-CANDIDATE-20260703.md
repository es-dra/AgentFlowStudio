# AFS P0 State Recovery Integration Candidate - 2026-07-03

## Scope

- Lane: `INT-P0-AFS-STATE-RECOVERY-CANDIDATE-INTEGRATION`.
- Top-down dispatch: `TD-AFS-V02-INT-P0-STATE-RECOVERY-CANDIDATE-INTEGRATION-20260703-001`.
- Bottom-up feedback: `BU-AFS-V02-INT-P0-STATE-RECOVERY-CANDIDATE-INTEGRATION-20260703-001`.
- Integration worktree: `/home/afs-ops/.codex/worktrees/14b4/AgentFlowStudio`.
- Integration branch: `codex/p0-state-recovery-integration-20260703`.
- Baseline/reference: `dd027f72173a5a14ebd2f52a7ab587e1cecb6d4f`.
- Task difficulty: Deep.

## Candidate Inputs Inspected Read-Only

- Runtime candidate: `/home/afs-ops/.codex/worktrees/2bb8/AgentFlowStudio`, branch `codex/runtime-state-artifact-recovery-20260703`.
- Studio candidate: `/home/afs-ops/.codex/worktrees/6775/AgentFlowStudio`, branch `codex/studio-gate-status-recovery-20260703`.
- Both candidate worktrees had uncommitted accepted deltas on top of `dd027f7`; they were not mutated.
- Integration source worktree was clean and detached at `dd027f7` before creating the integration branch.

## Integrated Changes

- Brought in Runtime recovery contract, keyframe/comparison/video recovery envelopes, safe manifest recovery fields, async poll sanitization, partial output preservation, and non-fixture video no-output `needs_attention` behavior.
- Brought in Studio gate/status/recovery vocabulary, pre-submit readiness surfaces, retry-failed-items default copy/actions, job-center/canvas/inspector/process/review/node-menu hooks, accepted generation plan blocked review copy, and narrow viewport status-card CSS.
- Added an integration bridge so Studio status policy directly consumes Runtime `runtime_recovery` status, preserved outputs, and safe artifact pointers.
- Fixed repeated async keyframe terminal poll recovery so safe candidate previews/assets can be reconstructed from candidate files without re-echoing provider outputs through public safe manifests.
- Fixed cross-platform image upload public filename sanitization for Windows-style filenames before safe metadata validation.
- Updated stale deterministic tests for accepted no-output comparison/video behavior.

## Verification

Passed:

```text
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip install 'playwright>=1.45,<2'
.venv/bin/python -m playwright install chromium

.venv/bin/python -m py_compile apps/api/runtime_recovery_contract.py apps/api/runtime_generation_comparisons.py apps/api/runtime_image_assets.py apps/api/runtime_jobs.py apps/api/runtime_keyframe_async.py apps/api/runtime_keyframe_payloads.py apps/api/runtime_keyframe_routes.py apps/api/runtime_keyframes.py apps/api/runtime_video_candidates.py apps/api/runtime_video_dispatch.py apps/api/runtime_video_manifest.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_generation_comparison.py tests/test_api_runtime_provider_submit_preflight.py tests/test_api_runtime_video_generations.py tests/test_volc_seedance_video_adapter.py tests/test_web_studio_gate_status_recovery_static.py tests/test_web_studio_accepted_generation_plan_static.py

npm run check:studio-js
# JS syntax check passed: 138 files

.venv/bin/python -m pytest tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_generation_comparison.py tests/test_api_runtime_video_generations.py tests/test_web_studio_gate_status_recovery_static.py tests/test_web_studio_accepted_generation_plan_static.py tests/test_api_runtime_provider_submit_preflight.py::test_generation_comparison_gate_open_accepts_matching_preflight_token tests/test_volc_seedance_video_adapter.py::test_runtime_video_generation_passes_first_and_last_frames_to_provider tests/test_codex_image_handoff.py::test_codex_image_handoff_runtime_poll_route_completes_after_worker tests/test_api_runtime_feedback_candidate_context_consumption.py::test_context_resolver_consumes_promoted_feedback_overlay_without_asset_inclusion tests/test_api_runtime_media_contract.py::test_image_asset_contract_returns_safe_metadata_and_preview_bytes_only_on_preview_route -q
# 53 passed

.venv/bin/python tools/maintenance_audit.py
# failed=0, warning-only

git diff --check
# passed
```

Mocked browser/Playwright verification passed with provider gates closed:

```text
/studio/ -> seeded Runtime studio-state recovery nodes -> drawer job-center
390x820 and 1366x900
provider_calls_started=false
Browser plugin not available; regular Playwright used.
```

Assertions covered visible/readable `partially_complete`, `failed`, and `needs_attention` job-center cards, blocked reason and next action text, no horizontal overflow, and no state/main-text overlap.

Generated local evidence:

```text
/tmp/afs-p0-state-recovery-browser-report.json
/tmp/afs-p0-state-recovery-mobile-390x820.png
/tmp/afs-p0-state-recovery-mobile-needs-attention-390x820.png
/tmp/afs-p0-state-recovery-desktop-1366x900.png
```

Full non-legacy pytest was run after in-scope fixes:

```text
.venv/bin/python -m pytest -q
# 4 failed, 899 passed, 520 deselected, 1 warning
```

After the media-contract fix, the current direct residual set is:

```text
.venv/bin/python -m pytest tests/test_agentflow_knowledgebase.py::test_creative_prompt_knowledgebase_schema_registry_and_sync tests/test_agentflow_knowledgebase_coverage.py::test_knowledgebase_external_copy_stays_in_sync_after_audio_coverage tests/test_api_runtime_openapi_snapshot.py::test_committed_runtime_openapi_snapshot_matches_default_exporter -q
# 3 failed
```

Residual failures:

- External source-KB path absent in this Linux worker: `D:/Learning materials/Learning_notes/10-Startup/70-Projects/AgentFlow-Studio/knowledgebase`.
- OpenAPI snapshot mismatch is limited to generated `ValidationError` schema under the freshly resolved temporary dependency environment; no path diffs were found. Snapshot churn was not folded into this P0 recovery integration.

## Provider Gate

- No provider gate was opened.
- No live provider submit, poll, probe, or smoke was run.
- No external download, deploy, restart, systemd, Nginx, server state, production runtime state, generated media, provider raw response, signed URL, secret, or local config was touched.

## Non-Claims

- No merge to main/origin/server baseline.
- No push.
- No deploy/restart/runtime loaded-code freshness.
- No live provider probe or smoke.
- No generated-media QA.
- No human creative acceptance.
- No DOC2 cleanup.
- No review/export/provenance P1 completion.
- No product/commercial/public/legal readiness.
- No CompanyOS/COS promotion.
- No durable-memory promotion.
