# AFS Provider Flow Intake - 2026-06-17

## Scope

This handoff records the local intake of server-side PR #87 after the COS/GFR
baseline branch. It keeps the work limited to Runtime/Studio provider-flow
behavior and no-cost readiness.

## Changes

- Preserved uploaded/reference image assets for keyframe provider prompts even
  when a context bundle exists.
- Routed video prompt optimization through i2v/t2v-specific instructions and
  fallback text instead of image-edit wording.
- Built video-safe Kling provider prompts from first-frame continuity and safe
  asset-context text, without provider raw persistence.
- Let Studio video nodes infer a first frame from connected upstream keyframes,
  auto-poll submitted/running video jobs, and show image/video download links.
- Refreshed no-cost provider-connected readiness at
  `AFS-PROVIDER-FLOW-INTAKE-READINESS-20260617.json`.

## Verification

```text
node --check apps/studio/src/node-actions.js -> pass
node --check apps/studio/src/node-result-view.js -> pass
node --check apps/studio/src/optimizer-contract.js -> pass
pytest tests/test_web_studio_static.py tests/test_api_runtime_prompt_memory_loop.py::test_video_prompt_optimizer_uses_i2v_instruction_with_first_frame tests/test_api_runtime_video_generations.py::test_video_provider_prompt_removes_image_edit_language tests/test_api_runtime_keyframe_reference_assets.py::test_uploaded_image_asset_survives_context_bundle_reference_fallback -q -> 28 passed, 1 warning
pytest tests/test_afs_provider_connected_validation_readiness.py -q -> 4 passed, 1 warning
```

## Boundaries

- No local live provider call was started in this intake.
- No secret, cookie, Authorization header, signed URL, provider raw response,
  provider URL, or media byte is committed.
- Server-side Kling smoke notes remain provider-smoke evidence only.
- This is not human acceptance, business validation, or durable memory
  promotion.

## Next Gate

Before any live smoke from this local branch, ask for explicit authorization of
the exact provider capability, candidate count, budget, and disabled capabilities.
