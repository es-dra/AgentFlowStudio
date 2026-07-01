# AFS-T53 Interactive Manga Branch Package Contract - 2026-07-01

## Status

`implementation_ready_for_review`

T53 implements the smallest deterministic Stage 2 Interactive Manga branch
package contract after T52. It proves branch package structure before reader,
provider, Social Square, Director Console, Studio UI, Runtime, or OpenAPI work.

## Worktree And Dirty Boundary

Primary checkout observed before worktree creation:

- Branch: `master`
- HEAD: `56c3f700`
- Ahead of `origin/master`: `0`
- Pre-existing do-not-touch untracked paths:
  - `docs/demo-docs-20260629/`
  - `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`

T53 worktree:

- Worktree:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701`
- Branch: `codex/afs-t53-interactive-manga-branch-package-20260701`
- Base: `master` at `56c3f700`
- Decision: isolated worktree because this is a multi-file contract lane and
  the primary checkout has protected untracked local state.

## Scope

Write scope:

- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/interactive_manga_branch_package/__init__.py`
- `agentflow/algorithms/interactive_manga_branch_package/_helpers.py`
- `agentflow/algorithms/interactive_manga_branch_package/_validator.py`
- `tests/fixtures/interactive_manga_branch_package/branch_package_fixture.json`
- `tests/test_interactive_manga_branch_package_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff

Non-goals:

- No reader playback, public interactive runtime, Runtime route, OpenAPI path,
  Studio UI, provider adapter, provider prompt inclusion, provider config,
  generated media, external download, deploy, server sync, Runtime restart,
  CompanyOS projection, or COS source-rule edit.
- No edits to `docs/demo-docs-20260629/` or
  `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`.

## Contract Implemented

The new `interactive_manga_branch_package` algorithm validates:

- one deterministic branch package with exactly one choice point and two branch
  paths;
- branch shots that map back to base storyboard and base shot refs while
  carrying branch-specific shot refs;
- shared and branch-specific asset needs as separate scopes;
- shared and branch-specific continuity constraints;
- evidence requirements mapped to storyboard refs, Production Graph artifact
  refs, asset refs, evidence refs, and handoff envelope refs;
- Production Graph reference-only behavior with `graph_node_writes_required`
  false and `reference_only_no_node_write`;
- unsafe-marker rejection;
- protected non-claim preservation for reader playback, Runtime route, Studio
  UI, OpenAPI path, provider prompt inclusion, provider smoke, generated media,
  human creative acceptance, business validation, deploy/runtime health,
  CompanyOS projection, COS active-rule promotion, final schema acceptance, and
  product readiness.

## T52 And Stage1 Residual

The fixture carries:

```text
stage1_evaluator_system_error_residual
```

and source boundary refs:

```text
handoff:stage1-shared-contract
shared_object_evidence:fixture_v0
docs/handoff/AFS-T52-SHARED-OBJECT-EVIDENCE-FIXTURE-20260701.md
```

This means the branch package fixture builds on T52 structure evidence. It does
not erase the Stage1 residual or upgrade it into final schema acceptance,
product readiness, provider readiness, or human acceptance.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-red tests\test_interactive_manga_branch_package_contract.py -q
# red as expected: 9 failed because interactive_manga_branch_package was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-green tests\test_interactive_manga_branch_package_contract.py -q
# 9 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t53-final-impacted tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 32 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warnings are existing legacy_frozen_surface, human_doc_chinese_coverage, secret_like_fragments, oversized_files categories

git diff --check
# passed
```

## Cleanup Review

| Object | Decision | Evidence |
|---|---|---|
| `interactive_manga_branch_package` public module | keep | 93 lines; public constants and exports only. |
| `_validator.py` | keep | 287 lines; single-purpose deterministic validator for Stage 2 branch package shape. |
| `_helpers.py` | keep | 66 lines; local validation helpers reused only by this contract. |
| Branch package JSON fixture | keep | 537 lines; one atomic readable fixture object with no provider/raw/media payloads and no local private paths. Split only if a second fixture variant is added. |
| T53 focused test | keep | 140 lines; covers positive contract plus unresolved ref, unsafe marker, and non-claim failures. |
| Runtime/OpenAPI/Studio/provider surfaces | unchanged | No product surface expansion in this slice. |
| Primary checkout do-not-touch paths | untouched | Work ran in isolated worktree. |

## Remaining Risks

- This is deterministic branch package structure verification only.
- Exact final schema, Runtime API, Studio UI placement, storage, reader
  playback model, and provider prompt-inclusion policy remain future
  evaluator-gated work.
- Production Graph extension policy remains closed; branch package records use
  safe graph artifact references only.
- Human creative acceptance, story quality, generated-media quality, business
  validation, public/legal/patent readiness, deploy/runtime health, CompanyOS
  projection, and COS active-rule promotion remain separate gates.

## Non-Claims

T53 does not claim provider smoke, live provider calls, generated media,
generated-media quality, final schema acceptance, product readiness, Runtime
route readiness, OpenAPI readiness, Studio UI readiness, reader playback, public
interactive runtime, human creative acceptance, business validation,
customer/public/legal/patent readiness, deployment, Runtime health, CompanyOS
projection, durable-memory promotion, or COS active-rule promotion.

## Upward Feedback

`upward_feedback_delivery = sent_to_ceo`
