# AFS Video Node Duration + Provenance Idempotence Revision - 2026-07-02

## Status

`implementation_ready_for_review`

Branch/worktree:

```text
branch: codex/afs-video-node-duration-provenance-revision-20260702
worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-video-node-duration-provenance-revision-20260702
base: 2f96939c784b9e41616a29a5fde6061d8a2263aa
prior recovery base: 87cbe3247261d819e3752e0e5a18cf96223d03e4
original T58 baseline: 38c7cf5ef08b6d84217ef145129c4592866d8b49
```

## Scope

Narrow evaluator revision for two blocking issues:

- provenance idempotence across repeated `ensureVideoFirstFrameAsset()` and
  `videoInputSourceForRequest()` calls
- Studio operator duration acceptance for every one-second value from `1s`
  through `15s`

## Files Touched

- `apps/studio/src/video-node-flow.js`
- `apps/studio/src/presets/specs.js`
- `tests/test_web_studio_video_node_contract.py`
- `tests/test_web_studio_frontend_wave.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-VIDEO-NODE-DURATION-PROVENANCE-IDEMPOTENCE-REVISION-20260702.md`

## Behavior

- Direct uploaded first frames stay `uploaded_image` after repeated
  ensure/request calls.
- Upstream uploaded-image first frames stay `upstream_uploaded_image` after
  repeated ensure/request calls.
- Keyframe/generated first frames stay `upstream_generated_image` and preserve
  the original keyframe node id and job id.
- Generic upload `source_node_id` / `source_job_id` alone no longer imply
  keyframe provenance.
- Keyframe provenance is only inferred from `sourceKeyframeNodeId`,
  `sourceKeyframeJobId`, `upload.source_role=generated_keyframe_reference`,
  `upload.source_mode=upstream_generated_image`, or existing
  `videoInputSource.source_mode=upstream_generated_image`.
- Studio duration options now generate all `1s` through `15s` choices; backend
  and provider duration guards were not changed.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_video_node_contract.py tests\test_web_studio_frontend_wave.py -q
# red before patch:
# - direct upload repeated ensure flipped uploaded_image -> upstream_generated_image
# - upstream uploaded image repeated ensure flipped upstream_uploaded_image -> upstream_generated_image
# - duration options exposed only ["1s", "5s", "10s", "15s"]
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

OpenAPI was not touched, so the OpenAPI snapshot was not regenerated or rerun
for this revision.

## Dirty Boundary

- Saved checkout pre-existing dirty state: protected untracked
  `docs/demo-docs-20260629/`.
- Isolated worktree dirty state before edits: clean.
- Current-session edits are limited to the files listed above.
- Protected `docs/demo-docs-20260629/` was not modified.
- No provider/config/secret/private/customer/cost/generated-media files were
  edited.

## Residual Risks

- This revision verifies deterministic Studio/request contracts only.
- Browser/operator visual QA was not run because the requested smallest patch
  used the existing select-option surface rather than a new slider/stepper UI.
- Provider smoke was intentionally not run.

## Non-Claims

This revision is not provider smoke, generated-media quality validation, human
creative acceptance, business validation, public/legal/patent decision,
external download, deploy/server sync, Runtime health verification, OpenAPI
change, CompanyOS projection, durable-memory promotion, or COS active-rule
promotion.

## Next Action

Evaluator/CEO review can inspect the local commit and confirm:

```text
direct upload repeated request source_mode=uploaded_image
upstream uploaded-image repeated request source_mode=upstream_uploaded_image
keyframe generated repeated request source_mode=upstream_generated_image
duration options=1s..15s
```
