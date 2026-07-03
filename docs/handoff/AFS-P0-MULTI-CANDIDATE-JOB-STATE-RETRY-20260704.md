# AFS P0 Multi-Candidate Job-State Retry - 2026-07-04

## Scope

- Lane: `IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY`.
- Top-down dispatch:
  `TD-AFS-V02-IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704-001`.
- Bottom-up feedback:
  `BU-AFS-V02-IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704-001`.
- Branch: `codex/p0-multi-candidate-job-state-retry-20260704`.
- Base: `3b803085ea32e0d9289a33b1fa7a6472694e404d`.
- Task difficulty: Standard.

## Startup Notes

- `project-development-workflow` was not exposed in the runtime skill registry
  and no local fallback file was found under `/home/afs-ops/.codex`; AGENTS
  fallback startup rules were used.
- Startup scan read `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, and the current Runtime/Studio
  recovery handoffs.
- Original checkout `/home/afs-ops/AgentFlowStudio` was on `master` at
  `3b803085ea32e0d9289a33b1fa7a6472694e404d`, with known Owner dirty docs
  present. This lane used an isolated worktree, preserving those files.

## Changed

- Kept Studio failed-items-only retry state active after a keyframe retry submit
  receives an active Runtime response such as `submitted`, `pending`, or
  `running`.
- Passed retry-state intent through keyframe submit, bootstrap refresh, and
  background poll response application.
- Guarded `responseStatusSummary(..., { retrying: true })` so retrying applies
  only to active Runtime statuses; terminal `complete`, `partially_complete`,
  `failed`, and `needs_attention` responses clear the retrying job state.
- Added a focused static/Node regression for a two-candidate retry: active
  retry remains `generationPolicyStatus=retrying` with
  `retryFailedItemsOnly=true`, then terminal success clears retrying.

## Changed File Boundary

- `apps/studio/src/generation-status-policy.js`
- `apps/studio/src/node-keyframe-actions.js`
- `apps/studio/src/node-keyframe-response.js` (recovery-owned actual response
  path fix)
- `tests/test_web_studio_gate_status_recovery_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704.md`

## Recovery - Actual Response Path

- Dispatch:
  `TD-AFS-V02-FIX-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-ACTUAL-PATH-RECOVERY-20260704-001`.
- Bottom-up feedback:
  `BU-AFS-V02-FIX-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-ACTUAL-PATH-RECOVERY-20260704-001`.
- Evaluator finding: helper-level retry policy checks passed, but
  `applyKeyframeResponse()` dropped retry intent by calling
  `updateNodeGenerationState(n, response, { kind })`.
- Recovery fix: `applyKeyframeResponse()` now forwards
  `retrying: Boolean(options.retrying)` into `updateNodeGenerationState()`.
- Recovery-owned boundary expanded to include
  `apps/studio/src/node-keyframe-response.js` because it is the actual failing
  response path identified by the evaluator.
- Focused regression now exercises `applyKeyframeResponse()` directly for
  active `submitted`, `pending`, and `running` statuses and terminal
  `complete`, `partially_complete`, `failed`, and `needs_attention` outcomes.

## Verification

Passed:

```text
python3 -m py_compile tests/test_web_studio_gate_status_recovery_static.py
npm run check:studio-js
# JS syntax check passed: 139 files

PYTHONPATH=tests python3 - <<'PY'
import test_web_studio_gate_status_recovery_static as t
t.test_active_multi_candidate_retry_keeps_retrying_job_state_until_terminal_response()
print("direct actual-path static regression passed")
PY
# direct actual-path static regression passed

node --input-type=module - <<'JS'
// direct actual-path active statuses assertion
JS
# actual active retry statuses preserved: submitted,pending,running

node --input-type=module - <<'JS'
// direct actual-path terminal statuses assertion
JS
# actual terminal retry state clears: complete,partially_complete,failed,needs_attention

/home/afs-ops/AgentFlowStudio/.venv/bin/python -m pytest tests/test_web_studio_gate_status_recovery_static.py -q
# 8 passed

git diff --check
```

## Dirty Ownership Preservation

- Original dirty Owner docs were not edited, staged, removed, normalized, or
  overwritten:
  `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md`,
  `docs/demo/`, and
  `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`.
- This implementation ran in the isolated worktree
  `/home/afs-ops/.codex/worktrees/p0-multi-candidate-job-state-retry-20260704`.

## Residual Risks

- No browser/UI runtime session was started; validation is static and direct
  Node execution only.

## Non-Claims

- No fetch, pull, push, or source-sync.
- No provider gate opened and no provider call.
- No Runtime or Studio server run.
- No deploy, restart, or generated-media QA.
- No OpenAPI, DOC2, COS, CompanyOS, or source-KB mutation.
- No readiness, human acceptance, business/public/legal claim, or durable-memory
  promotion.
- No archive execution or self-archive.

## Completion Delivery

- BU delivery is performed from the worker control thread after commit.
- Archive policy: no self-archive; archive eligibility requires CEO ACK,
  route/registration, CTO/decision-owner consumption, and explicit archive
  policy gate.
