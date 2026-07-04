# AFS P0 Asset Reuse UX Explanation Reversal Local Contract - 2026-07-04

## Scope

- Lane: `IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT`.
- Top-down dispatch:
  `TD-AFS-V02-IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704-001`.
- Bottom-up feedback:
  `BU-AFS-V02-IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704-001`.
- Branch: `codex/p0-asset-reuse-ux-explanation-reversal-20260704`.
- Base: `3f750347e29155c46e4ab13be8cd625ae652582d`.
- Task difficulty: Standard.

## Startup Notes

- `project-development-workflow` was not exposed in the runtime skill list, so
  the required AGENTS fallback startup route was used.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, and relevant handoff records for
  reference upload, Studio vocabulary, asset auto-binding, node reference stack,
  and safe-packet/vocabulary integration.
- Current worktree was clean at startup. Base commit
  `3f750347e29155c46e4ab13be8cd625ae652582d` was present and was the starting
  `HEAD`/local `master` tip before creating the bounded branch.
- Provider gates stayed closed for LLM, ASR, image, video, external download,
  provider smoke, and generated-media QA.

## Changed

- Added `apps/studio/src/asset-reuse-contract.js`, a Studio-only local contract
  module that emits safe asset reuse summaries for:
  `recognized`, `reused`, `graph-bound`, `blocked`, `conflicted`, and
  `reversed/unbound`.
- The local contract consumes only already-local safe surfaces: upload metadata,
  fixed visual asset refs, optional `agentflow_asset_auto_binding_graph`
  suggestions and blocked candidates, optional node reference stack conflict
  state, local generation candidate records, and local reversal records.
- Explanation summaries include safe source evidence, asset id/label/type,
  target node/slot, confidence, lock/review state, selected/shadowed/blocked
  state, next action, and non-claims where locally available.
- Reversal plans follow existing Studio vocabulary:
  `binding -> unbind`, `generation_candidate -> reject`, and replace-capable
  entities -> `replace`.
- `recordAssetReuseReversal()` records reversal intent without deleting
  assets/media/provider artifacts/source evidence/upload records/candidate
  records.
- `buildOptimizationRequest()` now includes `node_parameters.asset_reuse` only
  when safe local reuse items exist.
- The existing `uploaded_images` optimization summary now redacts local path,
  signed/private URL, media-byte, bearer/token-like, and raw-provider markers.
- Asset-card uploads with `role=asset_reference` and
  `reference_target=asset_card_draft` remain draft/candidate reference inputs,
  not confirmed fixed assets and not ordinary keyframe generations.

## Changed File Boundary

- `apps/studio/src/asset-reuse-contract.js`
- `apps/studio/src/optimizer-contract.js`
- `tests/test_web_studio_asset_reuse_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704.md`

## Validation

Passed before commit:

```text
python3 -m py_compile tests/test_web_studio_asset_reuse_contract.py tests/test_web_studio_reference_upload_contract.py
python3 - <<'PY'  # asset_reuse_direct_assertions: passed
python3 - <<'PY'  # reference_upload_direct_assertions: passed
npm run check:studio-js
# JS syntax check passed: 140 files
```

Blocked:

```text
.venv/bin/python unavailable
python3 -m pytest tests/test_web_studio_asset_reuse_contract.py tests/test_web_studio_reference_upload_contract.py -q
# /usr/bin/python3: No module named pytest
```

Required whitespace/staged/post-commit checks are recorded in the worker BU.

## Direct Assertion Coverage

- Asset reuse states: `recognized`, `reused`, `graph-bound`, `blocked`,
  `conflicted`, and local `reversed/unbound` after recording a reversal.
- Safe explanation/redaction: no signed URL, local absolute path, media bytes,
  bearer/token-like text, or raw provider response marker is exposed in the
  contract or optimization output.
- Reversal behavior: `binding` emits `unbind`; `generation_candidate` emits
  `reject`; emitted actions apply to their Studio entity vocabulary entries.
- Non-destructive reversal: uploads, fixed visual assets, source evidence
  summaries, and generation candidate records remain present after reversal
  recording.
- Asset-card draft separation: `role=asset_reference` plus
  `reference_target=asset_card_draft` remains draft/candidate semantics and is
  not treated as a confirmed fixed asset.

## Dirty Ownership Preservation

- Initial and pre-record dirty ledger had no unrelated tracked or untracked
  Owner docs in this isolated worktree.
- No Owner dirty/untracked docs were staged, normalized, deleted, overwritten,
  or committed by this lane.

## Residual Risks

- `apps/studio/src/asset-reuse-contract.js` is 449 lines, within the 301-500
  maintenance warning band but below the hard split threshold; it remains a
  single-purpose local contract module.
- No browser UI session was started, so visual rendering and interaction
  affordance was not inspected.
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

CEO should ACK/register/route the BU to CTO. CTO decides evaluator, local
integration, recovery, alternate route, or exact blocker.
