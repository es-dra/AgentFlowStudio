# AFS Video Node Keyframe Provenance Revision - 2026-07-02

## Status

`implementation_ready_for_review`

Branch/worktree:

```text
branch: codex/afs-video-node-keyframe-provenance-revision-20260702
worktree: C:\Users\chenzy\.codex\worktrees\452b\AgentFlowStudio
base: 87cbe3247261d819e3752e0e5a18cf96223d03e4
```

## Scope

Narrow evaluator revision for the old text -> image -> video/generated-keyframe
continuation path. The fix preserves upstream generated-image provenance in the
Studio video input source contract when a video node is created from a keyframe
and then submitted through `ensureVideoFirstFrameAsset()` and
`videoInputSourceForRequest()`.

## Files Touched

- `apps/studio/src/keyframe-video-continuation.js`
- `apps/studio/src/video-node-flow.js`
- `apps/api/runtime_studio_state_params.py`
- `tests/test_web_studio_video_node_contract.py`
- `tests/test_api_runtime_studio_state.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-VIDEO-NODE-KEYFRAME-PROVENANCE-REVISION-20260702.md`

## Verification

```text
Detached base reproduction at 87cbe3247261d819e3752e0e5a18cf96223d03e4
# expected failure:
# requestSource.source_mode=explicit_first_frame_selection
# requestSource.source_node_id=node_1
# requestSource.source_job_id=null

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

OpenAPI was not touched, so `tests\test_api_runtime_openapi_snapshot.py` was not
rerun for this revision.

## Dirty Boundary

- Current-session edits are limited to the files listed above.
- Pre-existing dirty work was not present when the branch was created.
- Protected `docs/demo-docs-20260629/` was not modified.
- No provider/config/secret/private/customer/cost/generated-media files were
  edited.

## Non-Claims

This revision is deterministic provenance/request/state evidence only. It does
not claim provider smoke, generated-media quality, human creative acceptance,
business validation, deploy/server sync, Runtime health, OpenAPI change,
CompanyOS projection, durable-memory promotion, or COS active-rule promotion.

## Next Action

Evaluator/CEO review can inspect the local commit and confirm the keyframe
continuation request now reports:

```text
source_mode=upstream_generated_image
source_node_id=<original keyframe node id>
source_job_id=<keyframe job id>
role=first_frame
```
