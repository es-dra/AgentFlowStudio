# AFS P0 Node Reference Stack Priority Eval Gaps Recovery - 2026-07-04

## Dispatch

| Field | Value |
|---|---|
| Lane | `FIX-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS` |
| TD | `TD-AFS-V02-FIX-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS-20260704-001` |
| BU | `BU-AFS-V02-FIX-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS-20260704-001` |
| Branch | `codex/p0-node-reference-stack-priority-20260704` |
| Target base | `d0dedbf240fc84c4ee109383ab30faf1bc415e3d` |
| Close state | `node_reference_stack_priority_eval_gaps_recovered` |

## Startup And Scope

- `project-development-workflow` was not exposed, so AGENTS fallback startup
  scan was applied.
- Startup files read: `AGENTS.md`, `docs/company_operating_model.md`, and
  `TASK_TRACKER.md`.
- Task classification: `Standard`.
- Initial checkout was `master` at
  `4717430276f5aa8e46faa982f678f510fd34e466` with unrelated dirty docs:
  owner acceptance matrix handoff, `docs/demo/`, and
  `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`.
- Target branch existed locally and contained target base
  `d0dedbf240fc84c4ee109383ab30faf1bc415e3d`; branch switch preserved the
  unrelated dirty/untracked docs.
- Provider gates stayed closed for LLM, ASR, image, video, external download,
  provider smoke, and generated-media QA.

## Fixes

- Action applicability: introduced a Studio-compatible
  `REVERSAL_ACTION_BY_REFERENCE_TYPE` map. Selected `generation_candidate`
  references now emit reversal action `reject` instead of `replace`; focused
  tests assert each emitted reversal action is present in Studio vocabulary and
  applies to the emitted reference entity.
- Unsafe target gap: target normalization now blocks `data:*`,
  `data:image/...;base64`, base64 media signatures, long base64 media-byte-like
  targets, and bytes input; unsafe target refs are redacted to
  `unsafe_ref_redacted`.
- Asset-binding import hardening: imported
  `agentflow_asset_auto_binding_graph` suggestions now fail closed when fixed
  asset id is empty, a matching `asset_auto_binding_established` relationship
  is missing, or the source relationship is missing/incomplete/mismatched.

## Changed File Boundary

- `agentflow/algorithms/node_reference_stack/__init__.py`
- `agentflow/algorithms/node_reference_stack/_asset_binding.py`
- `agentflow/algorithms/node_reference_stack/_contract.py`
- `agentflow/algorithms/node_reference_stack/_target_safety.py`
- `tests/test_node_reference_stack_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-NODE-REFERENCE-STACK-PRIORITY-20260704.md`
- `docs/handoff/AFS-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS-20260704.md`

## Validation

Passed:

```bash
.venv/bin/python -m py_compile agentflow/algorithms/node_reference_stack/__init__.py agentflow/algorithms/node_reference_stack/_asset_binding.py agentflow/algorithms/node_reference_stack/_contract.py agentflow/algorithms/node_reference_stack/_target_safety.py tests/test_node_reference_stack_contract.py
git diff --check
.venv/bin/python -m pytest tests/test_node_reference_stack_contract.py -q
# 8 passed
.venv/bin/python - <<'PY'  # direct static assertions
# passed: reversal appliesTo, data/base64 blocking, malformed asset-binding fail-closed
```

Pending after local commit creation:

```bash
git diff --cached --check
git diff --check HEAD
```

## Dirty Ownership

Unrelated work preserved and not owned by this recovery:

- `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md`
- `docs/demo/`
- `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`

## Residual Risks

- `agentflow/algorithms/node_reference_stack/__init__.py` is now in the
  301-500 line maintenance warning band after a scoped recovery patch; no
  split was performed because this task was a bounded evaluator fix, not a
  maintenance/refactor lane.
- This recovery validates algorithm contract behavior only. It does not claim
  Studio UI rendering, provider submission behavior, generated-media quality,
  or human acceptance.

## Non-Claims

- No master integration, source-sync, fetch, pull, push, provider gate/call,
  Runtime/Studio UI/OpenAPI/DOC2/COS/CompanyOS mutation, deploy/restart/server
  action, generated-media QA, readiness claim, human/business/public/legal
  claim, durable-memory promotion, archive execution, or self-archive.

## Archive Policy

`agent_created_archive_when_useless`; `owner_manual_archive_excluded=no`;
archive only after ACK delivery, route, decision-owner consumption, and explicit
archive policy gate. No archive execution occurred.

## On-Completion Delivery

Event-driven BU delivery is required after local validation and commit. The
final BU packet records the actual upward delivery result.

## Post-Closeout Next Action

CEO should ACK/register/route the BU to CTO. CTO decides recovery acceptance,
evaluator rerun, integration, or alternate route.
