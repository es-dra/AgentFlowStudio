# AFS-T57 SPEC2 Fixed Asset Confirmation Evidence Contract - 2026-07-02

## Status

`implementation_ready_for_review`

T57 implements the smallest deterministic SPEC2 contract slice after T56:
fixed-asset confirmation evidence and residual-question closure evidence for
`branch_workflow_package`.

This is evidence structure only. It does not run generation, call providers,
create media, add Runtime/OpenAPI/Studio surfaces, write graph nodes, implement
reader playback, or claim product readiness.

## Branch And Dirty Boundary

Worktree:

```text
C:\Users\chenzy\.codex\worktrees\5e58\AgentFlowStudio
```

Branch:

```text
codex/afs-t57-spec2-fixed-asset-confirmation-evidence-contract-retry-20260702
```

Base:

```text
61b5b8b9d98577df1d2b7c0c273f32869ffb8518
```

Dirty ownership ledger:

- Current worktree started clean and detached at T56, then switched to the
  retry branch above.
- `origin/master`, local `master`, and current `HEAD` were aligned at T56
  commit `61b5b8b9` after fetch.
- A preexisting T57 branch was already checked out in
  `C:\Users\chenzy\.codex\worktrees\df4a\AgentFlowStudio` with dirty files:
  `agentflow/algorithms/branch_workflow_package/__init__.py` and
  `tests/test_branch_workflow_confirmation_evidence_contract.py`. This retry
  lane did not read, modify, stage, or depend on that worktree.
- Protected `docs/demo-docs-20260629/` was not touched.

## Write Scope

- `agentflow/algorithms/branch_workflow_package/__init__.py`
- `agentflow/algorithms/branch_workflow_package/_confirmation_evidence.py`
- `agentflow/algorithms/branch_workflow_package/_generation_planning.py`
- `agentflow/algorithms/branch_workflow_package/_support.py`
- `agentflow/algorithms/branch_workflow_package/_validator.py`
- `tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json`
- `tests/test_branch_workflow_confirmation_evidence_contract.py`
- `tests/test_branch_workflow_generation_planning_gate.py`
- `tests/test_branch_workflow_package_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff

## Implementation Summary

- Added `_confirmation_evidence.py`, a deterministic local validator for
  fixed-asset confirmation evidence and residual-question closure evidence.
- The default fixture now carries a pending
  `fixed_asset_confirmation_evidence` envelope with only the already-confirmed
  shared map asset. Branch-specific assets remain visible as candidates and
  remain blocked by default.
- Branch-specific assets cannot become implementation-ready evidence without
  repo-local confirmation records, fixed asset source refs, confirmation source
  refs, owner/reviewer decision refs, close-condition refs, protected
  non-claim refs, `provider_prompt_inclusion_allowed=false`, and
  `graph_node_writes_required=false`.
- Residual questions cannot be closed without closure records containing
  target refs, evidence refs, owner/reviewer decision refs, close-condition
  refs, and non-claim-preserving close conditions.
- `generation_planning_candidate.checks` now includes fixed-asset confirmation
  completeness and residual-question closure completeness. The T56 default
  fixture remains not eligible.
- The eligible path remains deterministic fixture mutation only; it proves what
  evidence would unblock generation-planning eligibility, not product or
  provider readiness.

## Verification

Red check:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t57-red tests\test_branch_workflow_confirmation_evidence_contract.py -q
# expected red: 13 failed because fixed_asset_confirmation_evidence was not implemented
```

Focused green:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t57-focused-2 tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 16 passed
```

Branch workflow contract bundle:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t57-branch-contract-2 tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 34 passed
```

Impacted T57/T56/T55/T54/T53/T52/algorithm bundle:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t57-impacted tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 66 passed
```

Project gates:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only existing categories plus the new untracked T57 focused test oversized warning

git diff --check
# passed
```

## Integration Verification - 2026-07-02

Integrated onto current `master` after docs-cleanup commit
`7823a86c972b238227da50d3009b24ef9bfcd0ba`. The integration replayed only the
scoped T57 code, fixture, test, handoff, and handoff-index delta from
`C:\Users\chenzy\.codex\worktrees\5e58\AgentFlowStudio`; `DEVLOG.md` and
`TASK_TRACKER.md` were merged deliberately above the docs-cleanup records.

Preserved boundary: no `docs/demo-docs-20260629/`, Runtime/OpenAPI/Studio,
provider/config/secrets, storage, reader, deploy/server, generated media,
CompanyOS/Learning_notes, durable-memory, or COS active-rule surface was
touched.

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-focused tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 16 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-branch-contract tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py -q
# 34 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-impacted tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 66 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t57-integration-full -q
# 841 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories including the T57 focused test oversized warning
```

## Cleanup Review

| Object | Decision | Evidence |
|---|---|---|
| `_confirmation_evidence.py` | keep | 256 lines; one responsibility: local fixed-asset confirmation and residual closure evidence validation. |
| `_validator.py` | keep | 300 lines after helper split; still at the ideal threshold. |
| `_generation_planning.py` | keep | 139 lines; small candidate gate extended with T57 checks. |
| Branch workflow fixture | keep | 605 lines; one atomic SPEC2 fixture. It already exceeded the ideal threshold before T57 and remains a single readable contract object. Split only when a second fixture variant is added. |
| Focused T57 test | keep | Covers default blocked state, asset-only confirmation, residual closure requirement, full eligible evidence path, non-local evidence rejection, protected non-claims, provider prompt closure, and graph-write closure. |
| Runtime/OpenAPI/Studio/provider/storage/reader surfaces | unchanged | Explicitly out of scope and untouched. |

## Residual Risks

- This is deterministic structure evidence only; it is not final schema
  acceptance, provider generation, storage lifecycle, reader playback, Runtime,
  OpenAPI, Studio, product readiness, or human creative acceptance.
- The eligible path is proven by fixture mutation, not by a real human review
  workflow or generated media.
- Test helper duplication remains in focused contract tests. It is acceptable
  for this slice; a future test-support cleanup can consolidate helpers if
  another SPEC2 fixture variant is added.

## Non-Claims

T57 does not claim provider smoke, live provider calls, external download,
generated media, generated-media quality, Runtime/OpenAPI/Studio readiness,
reader playback, storage lifecycle, deploy/server sync, Runtime health, product
readiness, final schema acceptance, human creative acceptance, business
validation, public/legal/patent readiness, CompanyOS projection, durable-memory
promotion, or COS active-rule promotion.

## Upward Feedback

```text
upward_feedback_delivery = sent_to_ceo
```
