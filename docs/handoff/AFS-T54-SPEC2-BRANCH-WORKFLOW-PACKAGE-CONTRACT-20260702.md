# AFS-T54 SPEC2 Branch Workflow Package Contract - 2026-07-02

## Status

`implementation_ready_for_review`

T54 implements the next smallest deterministic SPEC2 contract slice after T53:
a `branch_workflow_package` readiness wrapper that reuses the T53
`interactive_manga_branch_package` fixture as source evidence.

## Worktree And Dirty Boundary

Primary checkout observed before worktree creation:

- Branch: `master`
- HEAD: `5ddbd399`
- Ahead of `origin/master`: `0`
- Pre-existing do-not-touch untracked path:
  - `docs/demo-docs-20260629/`

T54 worktree:

- Worktree:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t54-spec2-branch-workflow-package-20260702`
- Branch: `codex/afs-t54-spec2-branch-workflow-package-20260702`
- Base: `master` at `5ddbd399`
- Decision: isolated worktree because this is a multi-file deterministic
  contract lane and the primary checkout has protected untracked local state.

## Scope

Write scope:

- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/branch_workflow_package/__init__.py`
- `agentflow/algorithms/branch_workflow_package/_validator.py`
- `agentflow/algorithms/branch_workflow_package/_support.py`
- `tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json`
- `tests/test_branch_workflow_package_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff

Non-goals:

- No Runtime route, OpenAPI path, Studio UI, provider adapter, provider config,
  provider prompt inclusion, reader playback, public interactive runtime,
  generated media, external download, deploy, server sync, Runtime restart,
  CompanyOS projection, or COS source-rule edit.
- No edits to `docs/demo-docs-20260629/`.

## Contract Implemented

The new `branch_workflow_package` algorithm validates:

- the SPEC2 package wrapper fields: choice point, branch path, branch shot,
  asset need, continuity constraint, evidence requirement, review status, and
  handoff envelope;
- the wrapper package ref against the T53
  `interactive_manga_branch_package_fixture_v0` source fixture;
- shared and branch-specific asset scopes without collapsing candidate assets
  into fixed assets;
- unconfirmed branch-specific candidate exclusion from implementation-ready
  evidence;
- review-ready evidence completeness separately from
  accepted-for-generation-planning evidence completeness;
- Production Graph reference-only behavior with `graph_node_writes_required`
  false and `reference_only_no_node_write`;
- unsafe-marker rejection;
- protected non-claim preservation for reader playback, Runtime route, Studio
  UI, OpenAPI path, provider prompt inclusion, provider smoke, generated media,
  human creative acceptance, business validation, deploy/runtime health,
  CompanyOS projection, COS active-rule promotion, final schema acceptance, and
  product readiness.

## PB3 And Stage Residual Boundary

The fixture carries:

```text
pb3_local_package_commit_8296afa31b639224bcb3e7c1f8dea70000ea00b4_review_pending_local_package
pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate
pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready
stage1_evaluator_system_error_residual
```

These are review boundaries only. T54 does not erase or upgrade them into final
schema acceptance, product readiness, provider readiness, Runtime readiness, or
human acceptance.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-red tests\test_branch_workflow_package_contract.py -q
# red as expected: 9 failed because branch_workflow_package was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-green tests\test_branch_workflow_package_contract.py -q
# 9 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t54-impacted-final tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 41 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warning-only categories include the new English T54 handoff in human_doc_chinese_coverage

git diff --check
# passed
```

## Cleanup Review

| Object | Decision | Evidence |
|---|---|---|
| `branch_workflow_package` public module | keep | 99 lines; public constants and exports only. |
| `_validator.py` | keep | 277 lines; single-purpose deterministic validator after helper split. |
| `_support.py` | keep | 92 lines; fixture-root, reference-index, and report helpers only. |
| Branch workflow JSON fixture | keep | 498 lines; one atomic readable fixture object, no provider/raw/media payloads and no local private paths. Split only if a second fixture variant is added. |
| T54 focused test | keep | 156 lines; covers positive contract plus candidate exclusion, graph-write rejection, unsafe marker rejection, and non-claim failures. |
| Runtime/OpenAPI/Studio/provider surfaces | unchanged | No product surface expansion in this slice. |
| Primary checkout do-not-touch path | untouched | Work ran in isolated worktree. |

## Remaining Risks

- This is deterministic branch workflow package readiness verification only.
- Exact final schema, Runtime API, Studio UI placement, storage, reader
  playback model, and provider prompt-inclusion policy remain future
  evaluator-gated work.
- Branch-specific candidate assets remain excluded from implementation-ready
  evidence until future confirmation work records stronger evidence.
- Production Graph extension policy remains closed; branch workflow records use
  safe graph artifact references only.
- Human creative acceptance, story quality, generated-media quality, business
  validation, public/legal/patent readiness, deploy/runtime health, CompanyOS
  projection, and COS active-rule promotion remain separate gates.

## Non-Claims

T54 does not claim provider smoke, live provider calls, generated media,
generated-media quality, final schema acceptance, product readiness, Runtime
route readiness, OpenAPI readiness, Studio UI readiness, reader playback,
public interactive runtime, human creative acceptance, business validation,
customer/public/legal/patent readiness, deployment, Runtime health, CompanyOS
projection, durable-memory promotion, or COS active-rule promotion.

## Upward Feedback

`upward_feedback_delivery = sent_to_ceo`
