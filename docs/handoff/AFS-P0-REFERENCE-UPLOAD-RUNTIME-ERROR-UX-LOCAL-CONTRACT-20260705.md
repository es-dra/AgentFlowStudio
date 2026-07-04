# AFS P0 Reference Upload Runtime Error UX Local Contract - 2026-07-05

## Scope

- Lane: `FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT`.
- Top-down dispatch:
  `TD-AFS-V02-FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705-001`.
- Bottom-up feedback:
  `BU-AFS-V02-FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705-001`.
- Branch: `codex/p0-reference-upload-runtime-error-ux-20260705`.
- Base and pre-commit HEAD:
  `cfffa487cd3d3dce085e3157ce3852496f5f9a69`.
- Task difficulty: Standard.

## Startup Notes

- `project-development-workflow` was not exposed in the runtime skill list, so
  the required fallback startup route was used.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, and `docs/handoff/INDEX.md`.
- Relevant implementation/test paths were inspected before mutation:
  `apps/studio/src/node-upload-actions.js`,
  `apps/studio/src/runtime-client.js`,
  `apps/studio/src/runtime-error-utils.js`,
  `apps/studio/src/node-action-utils.js`,
  `apps/api/runtime_image_assets.py`,
  `apps/api/runtime_exception_handlers.py`,
  `apps/api/runtime_errors.py`, and
  `tests/test_web_studio_reference_upload_contract.py`.
- Initial dirty ledger was clean. No Owner/manual dirty paths were present or
  overwritten.

## Changed

- Hardened Studio Runtime error normalization so structured object payloads,
  validation arrays, nested `details`, and plain string errors do not render
  `[object Object]`.
- Structured Runtime upload errors now render safe Chinese lines with available
  message, reason, field label, error code, request id, and stage.
- Internal upload validation fields such as `data_base64` are mapped to a safe
  Chinese field label (`上传图片内容`) instead of exposing raw payload vocabulary.
- `safeError()` now routes non-structured fallback messages through the shared
  Runtime formatter, preserving existing gateway/provider special cases while
  applying Studio redaction to bearer/token/path/URL/media-byte fragments.
- Reference upload now rejects unsupported node targets and unsupported
  non-PNG/JPEG file selections locally before `FileReader` or Runtime upload
  calls.
- Existing successful upload binding behavior remains covered for loose image
  references, video first-frame uploads, keyframe-generation references, and
  asset-card draft references.

## Changed File Boundary

- `apps/studio/src/runtime-error-utils.js`
- `apps/studio/src/runtime-client.js`
- `apps/studio/src/node-action-utils.js`
- `apps/studio/src/node-upload-actions.js`
- `tests/test_web_studio_reference_upload_contract.py`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705.md`

## Verification

Passed before commit:

```text
/home/afs-ops/AgentFlowStudio/.venv/bin/python -m pytest tests/test_web_studio_reference_upload_contract.py
# 3 passed

/home/afs-ops/AgentFlowStudio/.venv/bin/python -m py_compile tests/test_web_studio_reference_upload_contract.py

npm run check:studio-js
# JS syntax check passed: 141 files

node --input-type=module -e '<structured validation-array safeError assertion>'
# passed; output used safe Chinese field label and no [object Object]
```

Additional required git whitespace checks are recorded in the worker BU.

## Direct Assertion Results

- Object Runtime error body through actual `uploadSelectedImage()` catch path:
  returned `图片上传失败`, safe Chinese validation message, reason, field label,
  code, request id, and stage; did not include `[object Object]`, bearer
  secrets, local paths, data URI fragments, raw `data_base64`, or token text.
- String error body through `safeError()` preserved the safe user-facing
  message while redacting bearer, token, local path, and media-byte fragments.
- Unsupported target and unsupported file checks returned clear Chinese errors
  before `FileReader` or Runtime upload calls.
- Successful upload/replace contract remains unchanged for image, video,
  keyframe-generation, and asset-card draft reference binding.

## Maintenance Notes

- This was a P0 fix, not a maintenance, cleanup, broad refactor, or
  Chinese-localization lane, so no maintenance ledger was opened.
- `apps/studio/src/runtime-client.js` was already above 500 lines before this
  task. Splitting the core Runtime client would broaden the P0 error UX fix and
  is deferred to a dedicated maintenance lane.

## Dirty Ownership Preservation

- Initial worktree status was clean.
- No fetch, pull, source-sync, push, merge, or destructive git operation was
  performed.
- No unrelated structured-QA files or Owner/manual paths were changed.

## Residual Risks

- No live Runtime Service was started, so this does not prove live upload route
  freshness or server-side behavior.
- No browser session was run, so chooser UI rendering and visual placement were
  not inspected.
- Provider gates stayed closed; no provider, generated-media, or business
  acceptance validation occurred.

## Non-Claims

- No live Web/browser/runtime freshness acceptance.
- No provider call, provider gate mutation, generated-media QA, final media
  decision, human/business/public/legal readiness claim, durable-memory
  promotion, COS/CompanyOS/source-KB mutation, deploy, restart, push, source
  sync, archive execution, or self-archive.

## Completion Delivery

- BU delivery is performed from the worker control thread after commit.
- Archive policy: no self-archive. Archive eligibility requires CEO ACK,
  route/registration, CTO/decision-owner consumption, and explicit archive
  policy gate.
- Post-closeout next action: CEO ACK/register/routes BU; CTO decides
  acceptance/recovery/evaluator/integration/source-sync eligibility/archive
  gate.
