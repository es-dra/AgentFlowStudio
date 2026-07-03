# AFS P0 Node Reference Stack Priority - 2026-07-04

## Dispatch

| Field | Value |
|---|---|
| Lane | `IMPL-P0-NODE-REFERENCE-STACK-PRIORITY` |
| TD | `TD-AFS-V02-IMPL-P0-NODE-REFERENCE-STACK-PRIORITY-20260704-001` |
| BU | `BU-AFS-V02-IMPL-P0-NODE-REFERENCE-STACK-PRIORITY-20260704-001` |
| Branch | `codex/p0-node-reference-stack-priority-20260704` |
| Base commit | `c2c95c3e9caaf118824b6b0b3ee56f66ae5d5adb` |
| Close state | `node_reference_stack_priority_completed` |

## Startup Scan

- `project-development-workflow` was not exposed in this session, so fallback
  startup instructions were applied.
- Read startup scope: `AGENTS.md`, `docs/company_operating_model.md`,
  `TASK_TRACKER.md`, and `docs/handoff/INDEX.md`.
- Task classification: `Standard`.
- Initial checkout was detached at
  `c2c95c3e9caaf118824b6b0b3ee56f66ae5d5adb`; base containment check passed
  for asset-binding integration commit
  `c2c95c3e9caaf118824b6b0b3ee56f66ae5d5adb`.
- Created isolated branch `codex/p0-node-reference-stack-priority-20260704`.
- Dirty ownership ledger: clean at startup; all current changed files are owned
  by this lane.
- Provider gate: remote LLM, ASR, image, video, and external download stayed
  closed; no provider call or runtime rerun was started.

## Contract

The new contract is `agentflow.algorithms.node_reference_stack`:

- `ALGORITHM_ID`: `afs.node_reference_stack.v0.1`
- Artifact type: `agentflow_node_reference_stack`.
- Input: project id, node id, explicit node references, and optional
  `agentflow_asset_auto_binding_graph`.
- Output: a safe node-local reference stack with normalized reference type,
  scope, target slot, target ref, status, priority rank, conflict result,
  explainability, reversal plan, selected relationships, and non-claims.
- Priority rule: explicit priority wins first, then scope precedence, then
  Studio entity type precedence.
- Conflict rule: references conflict inside the same node target slot; equal
  priority/scope/type rank fails closed with
  `unresolved_equal_rank_conflict` and requires human review.
- Reversal boundary: selected references use Studio-compatible per-entity
  reversal actions; `binding` uses `unbind`, `generation_candidate` uses
  `reject`, and supported replace-capable entities use `replace`. Reversal
  plans preserve lineage and do not delete assets.
- Safety boundary: no raw provider response, local path, external private link,
  media bytes, long-term memory write, or Company KB write is stored.

## Integration Points

- Registered `node_reference_stack` in `agentflow.algorithms.CORE_AGENT_ALGORITHM_MODULES`.
- Added static contract constants for existing Studio vocabulary entities:
  `project_asset`, `reference_input`, `generation_candidate`,
  `keyframe_version`, `video_revision`, `binding`, and `lineage`.
- Added static compatibility with existing Studio actions:
  `reference`, `bind`, `unbind`, `replace`, `reject`, `view_lineage`, and
  `view_evidence`.
- Added an asset auto-binding adapter that imports established
  `asset_auto_binding_established` suggestions as `binding` references with a
  priority floor of `82` and the source algorithm id
  `afs.asset_auto_binding.v0.1`.
- No Runtime route, OpenAPI, Studio UI behavior, provider adapter, deploy,
  restart, source sync, or server mutation was changed.

## Changed Files

- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/node_reference_stack/__init__.py`
- `agentflow/algorithms/node_reference_stack/_asset_binding.py`
- `agentflow/algorithms/node_reference_stack/_contract.py`
- `tests/test_node_reference_stack_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-P0-NODE-REFERENCE-STACK-PRIORITY-20260704.md`

## Validation

Passed:

```bash
git diff --check
python3 -m py_compile agentflow/algorithms/__init__.py agentflow/algorithms/node_reference_stack/__init__.py agentflow/algorithms/node_reference_stack/_asset_binding.py agentflow/algorithms/node_reference_stack/_contract.py tests/test_node_reference_stack_contract.py
python3 - <<'PY'  # direct_test_node_reference_stack_contract_ok
python3 - <<'PY'  # asset_auto_binding_stack_assertions_ok
python3 - <<'PY'  # equal_rank_conflict_assertions_ok
python3 - <<'PY'  # studio_vocabulary_static_markers_ok
```

Blocked in this checkout:

```bash
python3 -m pytest tests/test_node_reference_stack_contract.py -q
# /usr/bin/python3: No module named pytest
python3 -m apps.cli.main --help
# ModuleNotFoundError: No module named 'typer'
python3 -m apps.cli.main version
# ModuleNotFoundError: No module named 'typer'
```

No Studio JavaScript files were changed. Static Studio vocabulary compatibility
was checked with a Python marker assertion against
`apps/studio/src/studio-entity-status-vocabulary.js`.

## Non-Claims

- No provider behavior change, provider call, provider rerun, generated-media
  QA, human acceptance, business validation, public readiness, legal readiness,
  or product readiness claim.
- No node UI redesign, Runtime mutation, OpenAPI/DOC2/COS/CompanyOS mutation,
  multi-candidate retry engine, local keyframe edit, video adherence panel,
  source sync, fetch, pull, push, deploy, restart, server mutation, durable
  memory promotion, or Company KB promotion.
- No self-archive or archive execution.

## Residual Risks

- Focused pytest must be rerun in a dependency-equipped environment.
- This slice defines deterministic stack ordering and conflict records only; a
  future UI/runtime lane must decide how users inspect and apply the stack.
- Scope/type precedence is intentionally fixed contract data; changing it later
  should be a new contract revision, not an implicit behavior tweak.

## Archive Policy

`agent_created_archive_when_useless`; `owner_manual_archive_excluded=no`;
`archive_after_ack_delivery_confirmed=true`. No archive execution occurred.

## Post-Closeout Next Action

Run dependency-equipped focused pytest/evaluator for the new contract, then
decide whether the next bounded lane should surface the reference stack in
Studio node controls.
