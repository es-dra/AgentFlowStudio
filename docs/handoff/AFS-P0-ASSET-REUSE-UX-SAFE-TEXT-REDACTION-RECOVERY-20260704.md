# AFS P0 Asset Reuse UX Safe Text Redaction Recovery - 2026-07-04

## Scope

- Lane: `FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION`.
- Top-down dispatch:
  `TD-AFS-V02-FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-20260704-001`.
- Bottom-up feedback:
  `BU-AFS-V02-FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-20260704-001`.
- Branch: `codex/p0-asset-reuse-ux-explanation-reversal-20260704`.
- Base: `3f750347e29155c46e4ab13be8cd625ae652582d`.
- Recovery start commit: `db69f666e46242d56c5e7b39774f49c92bd0ba76`.
- Task difficulty: Standard recovery.

## Startup Notes

- `project-development-workflow` was not exposed in the runtime skill list, so
  the required AGENTS fallback startup route was used.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, the asset reuse local contract
  handoff, and the reference upload flexibility handoff.
- Worktree was live, clean, on
  `codex/p0-asset-reuse-ux-explanation-reversal-20260704`, and exactly at
  `db69f666e46242d56c5e7b39774f49c92bd0ba76` before edits.
- Lineage checks passed for both `db69f666e46242d56c5e7b39774f49c92bd0ba76`
  and base `3f750347e29155c46e4ab13be8cd625ae652582d`.
- Provider gates stayed closed for LLM, ASR, image, video, external download,
  provider smoke, and generated-media QA.

## Recovery

- Added `apps/studio/src/safe-text-redaction.js` as a shared Studio-local
  sanitizer for safe text surfaces.
- Routed `apps/studio/src/asset-reuse-contract.js` `safeText` and unsafe-id
  checks through the shared sanitizer.
- Routed `apps/studio/src/optimizer-contract.js` `safeUploadText` and upload
  token checks through the same sanitizer.
- Redaction now removes unsafe fragments embedded inside otherwise valid text:
  raw provider markers, `raw_provider_response`, `data_base64`, `data:*` URIs,
  PNG/JPEG/GIF/WebP/MP4/PDF/audio-like base64 signatures, long base64-like
  payloads, signed/private URLs, bearer/token-like strings, local paths, and
  raw media markers.
- Legitimate short human intent text is preserved before and after the redacted
  unsafe fragments.

## Changed File Boundary

- `apps/studio/src/safe-text-redaction.js`
- `apps/studio/src/asset-reuse-contract.js`
- `apps/studio/src/optimizer-contract.js`
- `tests/test_web_studio_asset_reuse_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-RECOVERY-20260704.md`

## Validation

Available validation before commit:

```text
python3 -m py_compile tests/test_web_studio_asset_reuse_contract.py
python3 - <<'PY'  # asset_reuse_direct_assertions: passed
npm run check:studio-js
# JS syntax check passed: 141 files
```

Additional required whitespace, focused pytest availability, reference-upload
regression, staged check, and post-commit checks are recorded in the worker BU.

## Direct Assertion Coverage

- Evaluator-leaked fragments no longer serialize through either
  `assetReuseLocalContract()` or `buildOptimizationRequest()` output:
  `raw_provider_response`, `data_base64`, `data:image/*`, PNG base64 signature
  `iVBORw0KGgoAAAANSUhEUgAAAAUA`, long base64-like payloads,
  signed/private URLs, bearer/token-like strings, and local paths.
- Legitimate intent prefix `Use as pose ref` remains available in both asset
  reuse source evidence and optimizer `uploaded_images`.
- Existing behavior still covers asset reuse states, reversal action
  applicability, non-destructive reversal preservation, asset-card draft
  separation, optimizer `asset_reuse` gating, and reference-upload regression.

## Dirty Ownership Preservation

- Startup dirty ledger was clean in this isolated worktree.
- No unrelated Owner dirty/untracked docs were visible, staged, normalized,
  deleted, overwritten, or committed by this recovery.

## Residual Risks

- No browser UI session was started.
- No live Runtime Service path, OpenAPI path, provider path, generated-media QA,
  or human acceptance path was exercised.

## Non-Claims

- No fetch, pull, push, source-sync, provider call/gate mutation, Runtime or
  Studio server/browser run, deploy/restart, generated-media QA,
  OpenAPI/DOC2/COS/CompanyOS/source-KB mutation, readiness claim,
  human/business/public/legal claim, durable-memory promotion, archive
  execution, or self-archive.

## Completion Delivery

- BU delivery is performed from the worker control thread after local commit
  and required post-commit checks.
- Archive policy: no self-archive. Archive eligibility requires CEO ACK,
  route/registration, CTO/decision-owner consumption, and explicit archive
  policy gate.

## Post-Closeout Next Action

CEO should ACK/register/route the recovery BU. CTO decides independent
evaluator rerun, alternate recovery, blocker, or integration path.
