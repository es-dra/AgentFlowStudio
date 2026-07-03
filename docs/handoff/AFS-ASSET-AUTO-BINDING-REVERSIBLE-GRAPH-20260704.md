# AFS Asset Auto-Binding Reversible Graph - 2026-07-04

## Dispatch

| Field | Value |
|---|---|
| Lane | `IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH` |
| TD | `TD-AFS-V02-IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704-001` |
| BU | `BU-AFS-V02-IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704-001` |
| Branch | `codex/asset-auto-binding-reversible-graph-20260704` |
| Base commit | `67913d8e708cdd04c0681b7630761944738259fe` |
| Close state | `asset_auto_binding_reversible_graph_completed` |

## Startup Scan

- `project-development-workflow` was not exposed and no local
  `project-development-workflow` skill file existed under `/home/afs-ops/.codex`;
  repo fallback instructions from `AGENTS.md` were applied.
- Read startup scope: `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, `DEVLOG.md`, and `docs/handoff/INDEX.md`.
- Task classification: `Standard`.
- Dirty ownership ledger: clean checkout at scan time; no unrelated dirty or
  untracked work was present.
- Provider gate: remote LLM, ASR, image, and video stayed closed; no provider
  calls or reruns were started.

## Contract

The new contract is `agentflow.algorithms.asset_auto_binding`:

- `ALGORITHM_ID`: `afs.asset_auto_binding.v0.1`
- Input: candidate asset graph, fixed visual assets, project id.
- Output: `agentflow_asset_auto_binding_graph` with binding suggestions,
  established production-graph relationships, blocked candidates, and
  non-claims.
- Minimum confidence: `0.82`, matching the existing local storyboard fallback
  confidence for explicit label presence without an inline marker.
- A binding is auto-established only when all gates pass:
  exact asset type and normalized label match, candidate evidence exists, fixed
  source evidence exists, the match is unambiguous, the candidate graph has no
  unsupported additions or merge candidates, and the reversal plan is explicit.
- The relationship type is `asset_auto_binding_established`; the reversible
  action is `unbind`.
- Fail-closed paths produce `blocked_candidates` with reasons such as
  `low_confidence_candidate`, `missing_candidate_evidence`,
  `missing_fixed_source_evidence`, `ambiguous_fixed_asset_match`,
  `unsupported_additions_require_review`, and
  `merge_candidates_require_review`.

## Implementation

- Added a single-purpose algorithm module for deterministic binding graph
  construction.
- Registered the module in the algorithm library module list.
- Integrated the binding graph into `build_storyboard_production_graph()`:
  eligible bindings add safe reversible graph relationships, and summary counts
  are surfaced on the production graph.
- Added `asset_auto_binding_graph` as a direct storyboard response field and as
  a standalone storyboard artifact.
- Added evidence ledger coverage for the new artifact role.
- Added focused tests for algorithm contract/export, reversible establishment,
  low-confidence and missing-evidence fail-closed behavior, ambiguous match
  blocking, and Runtime production-graph exposure.

## Changed Files

- `agentflow/algorithms/asset_auto_binding/__init__.py`
- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/production_graph/__init__.py`
- `agentflow/algorithms/evidence_ledger/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `apps/api/runtime_storyboard_artifacts.py`
- `tests/test_asset_auto_binding_contract.py`
- `tests/test_api_runtime_production_graph_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704.md`

## Validation

Passed:

```bash
python3 -m py_compile agentflow/algorithms/asset_auto_binding/__init__.py agentflow/algorithms/__init__.py agentflow/algorithms/production_graph/__init__.py agentflow/algorithms/evidence_ledger/__init__.py apps/api/runtime_storyboard_breakdown.py apps/api/runtime_storyboard_artifacts.py tests/test_asset_auto_binding_contract.py tests/test_api_runtime_production_graph_contract.py
git diff --check
python3 - <<'PY'  # asset_auto_binding_no_pytest_assertions
python3 - <<'PY'  # asset_auto_binding_static_assertions
python3 - <<'PY'  # production_graph_auto_binding_no_pytest_assertions
```

Blocked:

```bash
python3 -m apps.cli.main --help
# ModuleNotFoundError: No module named 'typer'
python3 -m apps.cli.main version
# ModuleNotFoundError: No module named 'typer'
python3 -m pytest tests/test_asset_auto_binding_contract.py tests/test_api_runtime_production_graph_contract.py -q
# /usr/bin/python3: No module named pytest
```

Direct Runtime route substitute was also blocked:

```bash
python3 - <<'PY'  # TestClient storyboard route assertion
# ModuleNotFoundError: No module named 'fastapi'
```

There is no `.venv` in this checkout.

## Non-Claims

- No provider call, provider rerun, generated-media QA, or human acceptance.
- No node reference stack UI, multi-candidate retry engine, keyframe edit,
  video adherence implementation, deploy, restart, runtime server mutation,
  source sync, fetch, pull, push, OpenAPI, DOC2, COS, or CompanyOS mutation.
- No fixed asset promotion, durable memory promotion, business validation,
  public readiness, legal readiness, or product readiness claim.

## Residual Risks

- Focused pytest and direct Runtime route assertions must be rerun in an
  environment with project dependencies installed.
- The first slice uses deterministic exact type/label matching only; semantic
  similarity, multi-candidate arbitration beyond duplicate blocking, and UI
  review controls are intentionally excluded.
- Existing local storyboard extraction quality still controls whether a
  candidate asset appears for binding.

## Archive Policy

`agent_created_archive_when_useless`; `owner_manual_archive_excluded=no`;
`archive_after_ack_delivery_confirmed=true`. No archive execution occurred.

## Post-Closeout Next Action

Run the focused pytest/evaluator in a dependency-equipped environment, then
review whether the next lane should surface the reversible binding artifact in
the Studio node reference stack UI.
