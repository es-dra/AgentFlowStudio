# AFS-T52 Shared Object Evidence Fixture - 2026-07-01

## Status

`implementation_ready_for_review`

T52 implements the smallest deterministic local fixture contract from the
Stage1 shared object/evidence packet. It converts the planning packet into an
executable repo-local fixture and validator, while carrying the Stage1
evaluator system-error residual explicitly.

## Worktree And Dirty Boundary

Primary checkout observed before edits:

- Branch: `codex/afs-post-main-loop-e2e-continuation-20260630`
- Dirty T51 files: `DEVLOG.md`, `TASK_TRACKER.md`,
  `docs/handoff/INDEX.md`, `tests/test_studio_main_path_browser_qa_tool.py`,
  `tools/studio_main_path_browser_qa.py`, plus untracked T51 handoff/test/tool
  files.
- Do-not-touch local state: `docs/demo-docs-20260629/`

T52 worktree:

- Worktree:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701`
- Branch: `codex/afs-t52-shared-object-evidence-fixture-20260701`
- Base: current branch HEAD `b09c5482`
- Decision: isolated worktree, because editing the primary checkout would
  interleave T52 records with pre-existing T51 dirty files.

## Scope

Write scope:

- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/shared_object_evidence/__init__.py`
- `tests/fixtures/shared_object_evidence/stage1_contract_fixture.json`
- `tests/test_shared_object_evidence_contract_fixture.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff

Non-goals:

- No Runtime route, OpenAPI path, Studio UI, provider adapter, provider config,
  generated media, external download, deploy, server sync, Runtime restart, or
  CompanyOS/COS source-rule edit.
- No edits to `docs/demo-docs-20260629/`.

## Contract Implemented

The new `shared_object_evidence` algorithm validates:

- deterministic fixture load and stable sorted refs;
- canonical object refs for project, script, storyboard, base shot, branch
  path/shot, asset candidate, fixed asset, Production Graph node/reference,
  evidence ref, feedback review state, handoff envelope, and reuse scope;
- all declared source, evidence, target, node, asset, shot, branch, and reuse
  refs resolve inside the fixture;
- current Production Graph nodes remain limited to current approved node types,
  while proposed branch graph nodes require `evaluator_required`;
- `production_graph_reference` remains `reference_only_no_node_write`;
- unsafe markers fail closed;
- `partial` evidence requires `evidence_gap_reason`;
- handoff envelopes include targets, evidence route, next owner/action, close
  condition, reuse scope, blockers, and non-claims;
- fixed assets retain source candidate/evidence refs and do not collapse
  provider or human-acceptance non-claims.

## Stage1 Residual

The Stage1 evaluator failure is carried as:

```text
stage1_evaluator_system_error_residual
```

The validator reports:

```text
evaluator_system_error_residual_carried
```

This means the local fixture is executable and structure-verified, not that the
Stage1 packet received final schema acceptance or downstream product approval.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t52-red tests\test_shared_object_evidence_contract_fixture.py -q
# red as expected: 8 failed because shared_object_evidence was not implemented

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t52-green tests\test_shared_object_evidence_contract_fixture.py -q
# 8 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t52-impacted-worktree tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py tests\test_model_call_context_contract.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py -q
# 36 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp D:\Projects\AgentFlowStudio\.venv\pytest-t52-final tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py tests\test_model_call_context_contract.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py -q
# 36 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; warnings are legacy_frozen_surface, human_doc_chinese_coverage, secret_like_fragments, oversized_files

git diff --check
# passed
```

Note: the first impacted run used `.venv\pytest-t52-impacted` inside the
isolated worktree and failed because the isolated worktree has no `.venv`
directory for pytest basetemp. It was rerun with an existing primary `.venv`
basetemp and passed.

## Cleanup Review

| Object | Decision | Evidence |
|---|---|---|
| `shared_object_evidence` module | keep | Single-purpose deterministic validator, 244 nonblank lines. |
| Stage1 JSON fixture | keep | Repo-local safe fixture, 270 lines, no provider/raw/media payloads. |
| T52 focused test | keep | 83 nonblank lines and covers positive plus fail-closed cases. |
| Runtime/OpenAPI/Studio surfaces | unchanged | No product surface expansion in this slice. |
| T51 primary checkout files | untouched | Work ran in isolated worktree. |
| `docs/demo-docs-20260629/` | untouched | Do-not-touch local state. |

## Remaining Risks

- This is deterministic local structure verification only.
- Exact final shared-object schema, Runtime API, Studio UI placement, storage,
  and provider prompt-inclusion policy remain future evaluator-gated work.
- Production Graph extension policy remains narrow: proposed branch, spatial,
  collaboration, review, handoff, or reuse-scope nodes are not approved graph
  writes.
- T51 records are dirty in the primary checkout and are not included in this
  isolated T52 branch.

## Non-Claims

T52 does not claim provider smoke, live provider calls, generated media,
generated-media quality, final schema acceptance, Runtime route readiness,
OpenAPI readiness, Studio UI readiness, human creative acceptance, business
validation, customer/public/legal/patent readiness, deployment, Runtime health,
CompanyOS projection, durable-memory promotion, or COS active-rule promotion.
