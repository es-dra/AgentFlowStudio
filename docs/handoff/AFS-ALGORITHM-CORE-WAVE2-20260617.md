# AFS Algorithm Core Wave 2 - 2026-06-17

## Scope

This wave continues the Algorithm Library migration after provider-flow intake.
It does not add live provider calls and does not change provider credentials or
server configuration.

## Changes

- `creative_intent_control.video_prompt` owns i2v/t2v mode selection, visual
  reference detection, deterministic video fallback prompts, video enhancement
  instructions, strict retry instructions, and first-frame reference subject
  extraction.
- `provider_gate_manifest.video_prompt` owns video-safe provider prompt
  projection and image-edit wording stripping for Kling-style video calls.
- `context_resolver.references` owns merging of context-bundle reference image
  refs with explicit request asset refs.
- `apps/studio/src/video-node-flow.js` owns video first-frame inference from
  upstream keyframes and safe auto-poll scheduling for submitted/running video
  jobs.
- Runtime files now call algorithm helpers for the migrated product semantics.

## Verification

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

## Boundaries

- No live provider call was started.
- No secret, cookie, Authorization header, signed URL, provider raw response,
  provider URL, provider config path, local private media byte, or generated
  media byte is committed.
- Runtime verification and structure verification are not human acceptance or
  business validation.
- Feedback/scoring evidence remains raw evidence and is not durable memory.

## Remaining Debt

- `runtime_llm_enhancement.py`, `runtime_video_routes.py`, `node-actions.js`,
  and several test files remain oversized. This wave reduced the active surface
  and moved product semantics into algorithms, but it does not claim full
  maintainability cleanup.
