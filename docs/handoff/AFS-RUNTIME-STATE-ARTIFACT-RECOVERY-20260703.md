# AFS Runtime State Artifact Recovery - 2026-07-03 Dispatch

## Scope

- Lane: `IMP-P0-RUNTIME-STATE-ARTIFACT-RECOVERY`.
- Top-down dispatch: `TD-AFS-V02-IMP-RUNTIME-STATE-ARTIFACT-RECOVERY-20260703-001`.
- Bottom-up feedback: `BU-AFS-V02-IMP-RUNTIME-STATE-ARTIFACT-RECOVERY-20260703-001`.
- Branch: `codex/runtime-state-artifact-recovery-20260703`.
- Base: `dd027f7`.
- Task difficulty: Deep.

## Changed

- Added a shared Runtime recovery contract helper for accepted public batch states, safe artifact pointers, provider gate/provider-call provenance, default failed-item retry scope, preserved-output metadata, and non-claim copy.
- Added `batch_status`, `stage`, failure class, retry metadata, batch summary, and safe provenance to keyframe and video safe manifests.
- Added `runtime_recovery` response envelopes to keyframe, video, and multi-image comparison Runtime responses.
- Normalized keyframe provider partial results so valid outputs are preserved and registered as generated image assets while missing/failed items remain retryable.
- Preserved async keyframe outputs when a provider reports a failed/blocked poll response that still includes valid outputs.
- Normalized multi-image comparison reports to `partially_complete` for mixed output/block arms and removed relative `image_ref` paths from result refs.
- Contained fake video placeholder generation to fake/fixture providers only; non-fixture video providers that return no reviewable output now surface `needs_attention` without creating a fake MP4.

## Fixback - Async Poll Safe Manifest Sanitization

- Dispatch: `TD-AFS-V02-FIX-RUNTIME-ASYNC-POLL-SAFE-MANIFEST-SANITIZE-20260703-001`.
- Bottom-up feedback: `BU-AFS-V02-FIX-RUNTIME-ASYNC-POLL-SAFE-MANIFEST-SANITIZE-20260703-001`.
- Verifier finding reproduced by inspection: async keyframe poll success/partial path copied provider outputs into `safe_manifest["outputs"]`, and those provider outputs included `image_ref` derived from provider `image_path`.
- Removed the async `safe_manifest["outputs"]` echo.
- Stopped mapping provider `image_path` into Runtime `image_ref` in normalized keyframe provider outputs.
- Added async submit-plus-poll regression coverage that asserts public poll JSON has no `image_candidates/`, `image_ref`, `image_path`, `output_dir`, `request.json`, or handoff-job internals while retaining safe candidate preview and `runtime_recovery` retry/preservation pointers.

## Provider Gate

- No provider gate was opened.
- No live provider submit or poll was run.
- No external download, deploy, restart, or server operation was run.

## Verification

```text
python3 -m py_compile apps/api/runtime_recovery_contract.py apps/api/runtime_generation_comparisons.py apps/api/runtime_jobs.py apps/api/runtime_keyframe_async.py apps/api/runtime_keyframe_payloads.py apps/api/runtime_keyframe_routes.py apps/api/runtime_keyframes.py apps/api/runtime_video_candidates.py apps/api/runtime_video_dispatch.py apps/api/runtime_video_manifest.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_generation_comparison.py tests/test_api_runtime_video_generations.py
# passed

git diff --check
# passed

wc -l apps/api/runtime_recovery_contract.py
# 291 apps/api/runtime_recovery_contract.py
```

Blocked verification:

```text
python -m pytest tests/test_api_runtime_creative_agent_keyframes.py::test_keyframe_partial_outputs_are_preserved_with_failed_item_retry_scope tests/test_api_runtime_generation_comparison.py::test_generation_comparison_uses_partial_state_for_mixed_image_arms tests/test_api_runtime_video_generations.py::test_video_generation_does_not_create_fake_placeholder_for_non_fixture_provider -q
# blocked: /bin/bash: python: command not found

python3 -m pytest tests/test_api_runtime_creative_agent_keyframes.py::test_keyframe_partial_outputs_are_preserved_with_failed_item_retry_scope tests/test_api_runtime_generation_comparison.py::test_generation_comparison_uses_partial_state_for_mixed_image_arms tests/test_api_runtime_video_generations.py::test_video_generation_does_not_create_fake_placeholder_for_non_fixture_provider -q
# blocked: /usr/bin/python3: No module named pytest

python3 -m pytest tests/test_api_runtime_creative_agent_keyframes.py::test_async_keyframe_poll_safe_manifest_does_not_echo_provider_paths -q
# blocked: /usr/bin/python3: No module named pytest
```

## Residual Risks

- Focused pytest and broader Runtime suites still need to be run from the project Python environment with pytest installed.
- Legacy `job.status=succeeded` remains for fully complete compatibility paths; accepted DEC states are exposed through `batch_status` and `runtime_recovery.status`, and mixed partial batches use `partially_complete`.
- Safe manifests use candidate counts for retry summaries; response recovery envelopes use actual safe preview candidate IDs when available.

## Non-Claims

- Not product readiness.
- Not live provider probe or smoke.
- Not generated-media QA.
- Not human acceptance.
- Not business/public/legal readiness.
- Not deploy alignment or Runtime loaded-code freshness.
- Not CompanyOS/COS promotion or durable-memory promotion.
