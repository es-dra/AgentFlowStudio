# AFS P0 Reference Upload Flexibility Local Contract - 2026-07-04

## Scope

- Lane: `IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT`.
- Top-down dispatch:
  `TD-AFS-V02-IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704-001`.
- Bottom-up feedback:
  `BU-AFS-V02-IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704-001`.
- Branch: `codex/p0-reference-upload-flexibility-20260704`.
- Base: `70da628200bc66e2ba23039417954a853cda56a5`.
- Task difficulty: Standard.

## Startup Notes

- `project-development-workflow` was not exposed in the runtime skill list, so
  the task used the required fallback startup route.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, and `docs/handoff/INDEX.md`.
- Branch and baseline were verified before edits. The worktree started detached
  at `70da628200bc66e2ba23039417954a853cda56a5`, and the baseline was an
  ancestor of `HEAD`.
- Initial dirty ledger was clean in this worktree. Protected Owner paths were
  not edited, staged, normalized, removed, or overwritten.

## Changed

- Made direct Studio image uploads node-aware in the existing `params.uploads`
  actual path.
- Direct uploads now preserve safe local contract fields:
  `role`, `reference_target`, `user_intent`, `media_kind`, `mime_type`, and
  `source_mode`.
- Video-node uploads immediately bind as `first_frame`, set
  `firstFrameImageAssetId`, and persist `videoInputSource` with the same safe
  user intent.
- Keyframe-generation image nodes persist `reference_target:
  keyframe_generation`.
- Asset-card draft image nodes persist `role: asset_reference` and
  `reference_target: asset_card_draft`, keeping asset-card drafts separate from
  ordinary keyframe generations.
- Optimization request node parameters now expose the same safe upload
  summaries through `uploaded_images`.

## Changed File Boundary

- `apps/studio/src/node-upload-actions.js`
- `apps/studio/src/optimizer-contract.js`
- `tests/test_web_studio_reference_upload_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704.md`

## Verification

Passed before commit:

```text
python3 -m py_compile tests/test_web_studio_reference_upload_contract.py
python3 tests/test_web_studio_reference_upload_contract.py
npm run check:studio-js
# JS syntax check passed: 139 files
git diff --check
```

Blocked:

```text
python3 -m pytest tests/test_web_studio_reference_upload_contract.py -q
# /usr/bin/python3: No module named pytest
ls -la .venv/bin/python
# .venv/bin/python is absent
```

Required post-commit checks are recorded in the worker BU.

## Direct Assertion

- `python3 tests/test_web_studio_reference_upload_contract.py` runs a direct
  Node script that calls the real `uploadSelectedImage()` path with a fake
  browser `FileReader` and fake Runtime upload response.
- The assertion covers image, video, keyframe-generation, and asset-card-draft
  node cases.
- It proves upload request payloads and resulting Studio node state preserve
  reference media metadata and bounded user intent without Runtime, provider,
  browser, or generated-media execution.

## Dirty Ownership Preservation

- Protected Owner paths were not touched:
  `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md`,
  `docs/demo/`, and
  `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`.

## Residual Risks

- No browser UI session was started, so chooser UX and visual rendering were not
  inspected.
- Runtime upload validation was not executed against a live Runtime Service;
  validation is local contract/static/direct-path only.

## Non-Claims

- No source-sync, fetch, pull, push, provider call/gate, Runtime/Studio server
  start, restart, deploy, browser QA, generated-media QA, OpenAPI/DOC2/COS/
  CompanyOS/source-KB mutation, readiness claim, human/business/public/legal
  claim, durable-memory promotion, archive execution, or self-archive.

## Completion Delivery

- BU delivery is performed from the worker control thread after commit.
- Archive policy: no self-archive; archive eligibility requires CEO ACK,
  route/registration, CTO/decision-owner consumption, and explicit archive
  policy gate.
