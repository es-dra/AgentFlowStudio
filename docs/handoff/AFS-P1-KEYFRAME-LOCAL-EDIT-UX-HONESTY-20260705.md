# AFS P1 Keyframe Local Edit UX Honesty - 2026-07-05

## Close State

`keyframe_local_edit_ux_honesty_completed`

## Dispatch

| Field | Value |
|---|---|
| TD | `TD-AFS-V02-FIX-P1-KEYFRAME-LOCAL-EDIT-UX-HONESTY-20260705-001` |
| Lane | `FIX-P1-KEYFRAME-LOCAL-EDIT-UX-HONESTY` |
| Expected BU | `BU-AFS-V02-FIX-P1-KEYFRAME-LOCAL-EDIT-UX-HONESTY-20260705-001` |
| Branch | `codex/fix-p1-keyframe-local-edit-ux-honesty-20260705` |
| Base / pre-HEAD | `cfffa487cd3d3dce085e3157ce3852496f5f9a69` |
| Task class | `Standard` bounded Studio UI honesty slice |
| Provider gate | Closed for LLM, ASR, image, video, external download, provider smoke, browser QA, and generated-media QA |

## Startup Notes

- `project-development-workflow` was not exposed, so the required fallback
  route was used.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, and relevant keyframe/video/
  reference/localized-edit handoffs.
- Worktree started clean and detached at
  `cfffa487cd3d3dce085e3157ce3852496f5f9a69`, matching the structured-QA
  integration called out by the dispatch.
- The lane created branch
  `codex/fix-p1-keyframe-local-edit-ux-honesty-20260705`.

## Changed

- Renamed keyframe/video regenerate actions so they say full-image/full-video
  regeneration instead of generic retry or modification.
- Added disabled/gated local-edit menu items for keyframe and video surfaces:
  current keyframe local edit requires image-edit/mask capability, and current
  video local edit requires video-edit/mask/temporal capability.
- Changed video revision draft copy to state that it is a whole-video
  regeneration attempt, not local edit, and recorded a Studio-only
  `local_edit_availability.status=unavailable` state on the draft.
- Changed video progress/result/algorithm-panel labels from revision language
  to regeneration-attempt language.
- Changed asset-card panel copy from local revision wording to whole asset-image
  regeneration wording, with an explicit image-edit/mask gate note.

## Changed File Boundary

- `apps/studio/src/keyframe-video-continuation.js`
- `apps/studio/src/node-generation-progress.js`
- `apps/studio/src/node-generation-results.js`
- `apps/studio/src/node-result-view.js`
- `apps/studio/src/node-video-actions.js`
- `apps/studio/src/panels/algorithm-context-panel.js`
- `apps/studio/src/panels/asset-card-panel.js`
- `apps/studio/src/panels/node-menu.js`
- `apps/studio/src/prompt-bar.js`
- `tests/test_web_studio_assets_generation_static.py`
- `tests/test_web_studio_prompt_script_static.py`
- `tests/test_web_studio_local_edit_honesty_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P1-KEYFRAME-LOCAL-EDIT-UX-HONESTY-20260705.md`

Structured-QA files were not edited.

## Validation

Passed before commit:

```text
python3 -m py_compile tests/test_web_studio_local_edit_honesty_static.py tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py
# passed; no output

python3 - <<'PY'
# direct import and execution of focused local-edit honesty assertions
# local_edit_honesty_direct_assertions: passed

npm run check:studio-js
# JS syntax check passed: 141 files

git diff --check
# passed; no output
```

Blocked before commit:

```text
python3 -m pytest tests/test_web_studio_local_edit_honesty_static.py -q
# /usr/bin/python3: No module named pytest
```

Staged and post-commit checks are recorded in the BU because their exact
results depend on the final commit.

## Direct Assertions

- Studio keyframe/video source now contains explicit regenerate labels and
  disabled local-edit unavailable/gated states.
- The old current-source UI labels `创建视频修改草稿` and
  `保存并局部修订生成` are absent from active Studio source.
- `enableVideoRevisionDraft()` directly records
  `local_edit_availability.status=unavailable`,
  `required_capability=video_edit_or_masked_temporal_edit`, and
  `reason=current_video_revision_is_global_regeneration_attempt`.
- Existing Runtime/provider call markers remain in place:
  `runtime.generateKeyframe(request)`, `runtime.generateVideo(request)`,
  `runtime.generateVideoRevision(request)`, `/keyframe-generations`, and
  `/video-revisions`.

## Dirty Ownership Preservation

- Startup dirty ledger was clean on this worktree.
- Structured-QA integration files from the starting commit were not edited,
  reverted, normalized, moved, staged separately, or deleted.
- No prompt textarea worker or reference-upload actual-path files were edited.
- No cleanup, archive, source-sync, fetch, pull, push, deploy, restart, or
  generated-media artifact action occurred.

## Residual Risks

- Browser rendering and interaction were intentionally not run for this lane.
- Runtime server freshness and provider behavior were intentionally not tested.
- Real local keyframe edit, image mask/edit capability, and true video
  local-edit implementation remain separate gated work.
- Historical records still describe older asset-card source-image edit work;
  this lane changes active Studio UI wording only and does not rewrite history.

## Non-Claims

- No true local edit implementation.
- No provider/mask/video-edit capability claim.
- No Runtime route, OpenAPI, provider descriptor, or request contract change.
- No browser/server QA, provider call/gate mutation, generated-media QA,
  source-sync, push, deploy, restart, human/business/public/legal readiness,
  durable-memory promotion, COS/CompanyOS/source-KB mutation, archive execution,
  or self-archive.

## Completion Delivery

- Required BU delivery targets: CEO ACK thread
  `019f29df-fefa-7131-9e7f-0957cf807e71`; visibility threads CTO
  `019f29e0-4f37-7731-8a78-497b9a39a3ec`, CPO
  `019f29df-90b6-7fa0-8c44-f40016c0829d`, COO
  `019f29e0-9d30-7ca2-a4a0-ce381d200a18`, PM
  `019f29e0-ed33-7c60-986b-e64bcad396d4`.
- Delivery result is recorded in the BU after commit and send attempts.

## Archive Policy

No self-archive. Archive eligibility requires CEO ACK, route/registration,
CTO/PM decision-owner consumption, and explicit archive gate.

## Post-Closeout Next Action

CEO ACK/register/routes BU. CTO/PM decide acceptance, recovery, evaluator,
integration, source-sync eligibility, archive gate, and keep true local edit
implementation separately gated.
