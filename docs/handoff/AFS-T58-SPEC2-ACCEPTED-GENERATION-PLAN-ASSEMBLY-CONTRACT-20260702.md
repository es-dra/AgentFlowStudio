# AFS-T58 SPEC2 Accepted Generation Plan Assembly Contract - 2026-07-02

## Status

`implementation_ready_for_review`

T58 implements the next deterministic SPEC2 contract slice after T57: an
accepted local generation plan packet assembled only when the existing
branch workflow package has complete fixed-asset confirmation evidence,
complete residual-question closure evidence, accepted review state, and a
repo-local generation-planning candidate.

This is structure evidence only. It does not run generation, call providers,
create media, add Runtime/OpenAPI/Studio surfaces, write graph nodes, implement
reader playback, add storage lifecycle, or claim product readiness.

## Branch And Dirty Boundary

Worktree:

```text
C:\Users\chenzy\.codex\worktrees\4646\AgentFlowStudio
```

Branch:

```text
codex/afs-t58-generation-plan-contract-20260702
```

Base:

```text
be476eed107cdaf318f6a6f8a5c3d7c6ac33c95f
```

Dirty ownership ledger:

- Startup fetch/status found this worktree clean and detached at T57
  integration commit `be476eed107cdaf318f6a6f8a5c3d7c6ac33c95f`.
- This lane created `codex/afs-t58-generation-plan-contract-20260702` in the
  existing isolated worktree before edits.
- The worktree-local `.venv` path was absent; verification used the main
  project venv at `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe`.
- Protected `docs/demo-docs-20260629/`, Runtime/OpenAPI/Studio, provider,
  generated-media, server/deploy, CompanyOS/Learning_notes, durable-memory,
  and COS active-rule surfaces were not touched.

## Write Scope

- `agentflow/algorithms/branch_workflow_package/__init__.py`
- `agentflow/algorithms/branch_workflow_package/_generation_plan_packet.py`
- `agentflow/algorithms/branch_workflow_package/_support.py`
- `agentflow/algorithms/branch_workflow_package/_validator.py`
- `tests/test_branch_workflow_accepted_generation_plan_packet.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff

## Implementation Summary

- Added `_generation_plan_packet.py`, a focused deterministic helper that
  assembles `accepted_generation_plan_packet` after the existing T56/T57
  candidate and confirmation evidence checks.
- The default T57 fixture remains blocked. It reports
  `packet_state=blocked_pending_generation_plan_prerequisites` because
  branch-specific fixed assets and residual-question closures are incomplete.
- An explicitly confirmed repo-local fixture mutation now assembles
  `packet_state=accepted_local_generation_plan_packet`.
- The accepted packet carries fixed asset refs, residual closure refs, local
  evidence refs, owner/reviewer/close-condition refs, review state,
  generation-planning candidate ref, fixed-asset confirmation evidence ref,
  protected non-claim boundary, and provider-closed generation-request planning
  fields.
- The request plan is provider-closed structure evidence only. It includes
  branch path refs, branch shot refs, continuity constraint refs, production
  graph artifact refs, evidence requirement refs, fixed asset refs, and
  `provider_gate=closed` with `provider_calls_started=false`,
  `generated_media=false`, and `graph_node_writes_required=false`.
- The contract still rejects fake external confirmation origins, provider
  response evidence, graph writes, unsafe markers, and protected non-claim
  collapse through the existing T56/T57 validation path.

## Verification

Interpreter path note:

```text
.\.venv\Scripts\python.exe -m pytest ...
# failed before pytest: isolated worktree has no local .venv
```

Red check:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-red tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# expected red: 2 failed, 1 passed because accepted_generation_plan_packet was not implemented
```

Focused green:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-focused tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# 3 passed
```

Branch workflow contract bundle:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-branch-contract tests\test_branch_workflow_package_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_accepted_generation_plan_packet.py -q
# 37 passed
```

Impacted T58/T57/T56/T55/T54/T53/T52/algorithm bundle:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t58-impacted tests\test_branch_workflow_accepted_generation_plan_packet.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 69 passed
```

Project gates:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories, including current-scope _validator.py at 311 lines

git diff --check
# passed
```

## Cleanup Review

| Object | Decision | Evidence |
|---|---|---|
| `_generation_plan_packet.py` | keep | One responsibility: assemble accepted or blocked local generation plan packet from already validated T56/T57 evidence. |
| `_validator.py` | keep with warning | Small wiring increase may put the file above the 300-line ideal threshold; helper split avoids mixing packet assembly into the validator body. |
| `_support.py` | keep | Report-shaping only; adds the new packet section. |
| New focused T58 test | keep | Covers default blocked packet, accepted local fixture packet, and fake external confirmation rejection. |
| Branch workflow fixture | keep unchanged | The accepted path remains deterministic fixture mutation, avoiding a second copied 600-line fixture. |
| Runtime/OpenAPI/Studio/provider/storage/reader surfaces | unchanged | Explicitly out of scope and untouched. |

## Residual Risks

- This is deterministic structure evidence only, not final schema acceptance
  or product readiness.
- The accepted path is proven by local fixture mutation, not by a real human
  operator workflow, generated media, or provider call.
- Runtime route, OpenAPI path, Studio operator surface, storage lifecycle,
  reader playback, provider prompt inclusion, and generated-media QA remain
  future evaluator-gated lanes.
- Test helper duplication remains in branch workflow focused tests. It is
  acceptable for this slice; consolidate only if the next SPEC2 lane adds more
  fixture variants or broader test support.

## Non-Claims

T58 does not claim provider smoke, live provider calls, external download,
generated media, generated-media quality, Runtime/OpenAPI/Studio readiness,
reader playback, storage lifecycle, deploy/server sync, Runtime health, product
readiness, final schema acceptance, human creative acceptance, business
validation, public/legal/patent readiness, CompanyOS projection,
durable-memory promotion, or COS active-rule promotion.

## Upward Feedback

```text
upward_feedback_delivery = sent_to_ceo
```
