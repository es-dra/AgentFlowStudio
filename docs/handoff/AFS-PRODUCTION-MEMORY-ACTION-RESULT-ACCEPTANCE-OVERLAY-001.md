# AFS-PRODUCTION-MEMORY-ACTION-RESULT-ACCEPTANCE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-action-result-acceptance-overlay-001`.

## Scope

Preserve action-result source evidence through this generic Production Memory
path:

```text
next_operator_action_result
  -> explicit acceptance_feedback_event
  -> acceptance_feedback_candidate_packet
  -> explicit acceptance_feedback_candidate_promotion_decision
  -> acceptance_feedback_candidate_reviewed_context_overlay
```

This continues the previous action-result acceptance feedback bridge. It does
not add a separate action-result-specific command; it makes the existing
acceptance-feedback candidate review path source-aware.

## Implementation Files

- `agentflow/memory/production_acceptance_feedback_candidate_promotion.py`
- `agentflow/memory/production_acceptance_feedback_candidate_overlay.py`
- `apps/web/memory-workbench-production-acceptance-feedback-candidate-promotion.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_production_memory_acceptance_feedback_candidate_promotion.py`
- `tests/test_production_memory_acceptance_feedback_candidate_overlay.py`
- `tests/test_web_static_production_memory_acceptance_feedback_candidate_promotion.py`

## Behavior

Promotion decisions now preserve:

- `source_artifact_type`;
- `source_artifact_path`;
- `source_artifact_status`;
- `source_ready_for_acceptance`;
- `source_target_ref`;
- `source_target_artifact_type`;
- `source_target_status`.

Reviewed overlays now preserve action-result source metadata and create a
source-aware artifact ledger record. For action-result feedback candidates, the
artifact ledger record uses:

- `artifact_type: agentflow_production_memory_next_operator_action_result`;
- a `next operator action result acceptance evidence` title;
- `status: accepted` for candidate-source accepted feedback.

Standalone promotion and overlay artifacts may reference ignored local runtime
evidence under `data/processed/runs/...`. The derived production-memory loop
projects the source path down to a safe short path such as
`next_operator_action_result/next_operator_action_result.json` before
validation. That keeps source-loop validation strict while preserving runtime
auditability in generated artifacts.

The Web promotion decision view now renders a `Source action result` lane,
`Source artifact` summary card, source evidence refs, and inspector facts for
action-result source metadata.

## Boundaries

This slice does not:

- call providers;
- write Company KB;
- write durable memory;
- execute the next pass;
- add a project-specific inspector;
- follow refs in Web;
- scan directories;
- persist browser state;
- auto-promote memory candidates;
- create new human acceptance;
- claim business validation.

## Verification

Initial red tests failed because promotion decisions, reviewed overlays, and Web
promotion views did not preserve action-result source metadata.

Focused green result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate_promotion.py tests\test_production_memory_acceptance_feedback_candidate_overlay.py tests\test_web_static_production_memory_acceptance_feedback_candidate_promotion.py -q
```

Result: `20 passed`.

Adjacent regression result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate.py tests\test_production_memory_acceptance_feedback_candidate_promotion.py tests\test_production_memory_acceptance_feedback_candidate_overlay.py tests\test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py tests\test_production_memory_operator_handoff_acceptance_feedback_overlay.py tests\test_production_memory_operator_run_package_check_acceptance_overlay.py tests\test_web_static_production_memory_acceptance_feedback_candidate_promotion.py tests\test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py tests\test_web_static_production_memory_operator_handoff_acceptance_overlay.py tests\test_web_static_production_memory_operator_run_package_check.py -q
```

Result: `42 passed`.

CLI smoke:

```text
action result -> action-result acceptance feedback -> candidate -> promoted
decision -> reviewed overlay
```

Result: reviewed run `ready`, `candidate_included_in_context: true`,
`source_artifact_type: agentflow_production_memory_next_operator_action_result`,
`source_artifact_status: action_completed`, `writes_company_kb: false`, and
`provider_calls_started: false`.

Additional verification:

- Changed Python files passed `python -m py_compile`.
- Changed Web modules passed `node --check`.
- Expanded Web/static memory tests passed (`92 passed, 823 deselected`).
- Full suite passed on Python 3.12.12 (`915 passed`).
