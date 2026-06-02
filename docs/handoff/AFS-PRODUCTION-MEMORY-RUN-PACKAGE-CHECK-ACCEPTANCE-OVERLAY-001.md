# AFS-PRODUCTION-MEMORY-RUN-PACKAGE-CHECK-ACCEPTANCE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-run-package-check-acceptance-overlay-001`.

## Scope

Add a final machine consistency check for embedded
`acceptance_feedback_candidate_promotion` summaries in operator run package
checks.

This follows:

- `AFS-PRODUCTION-MEMORY-OPERATOR-HANDOFF-ACCEPTANCE-OVERLAY-001`
- `AFS-PRODUCTION-MEMORY-WEB-HANDOFF-ACCEPTANCE-OVERLAY-001`

Those slices put the acceptance feedback candidate promotion summary into the
operator handoff packet, final run package, and read-only selected-file Web
views. This slice makes the final run package check enforce that the summary is
present and consistent before the next operator relies on acceptance-feedback
context.

## Implementation Files

- `agentflow/memory/production_operator_run_package_acceptance_check.py`
- `agentflow/memory/production_operator_run_package_check.py`
- `agentflow/memory/production_operator_run_package_check_render.py`
- `apps/web/memory-workbench-production-operator-run-package-check.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_production_memory_operator_run_package_check_acceptance_overlay.py`
- `tests/test_web_static_production_memory_operator_run_package_check.py`

## Behavior

`check_operator_run_package(...)` now emits
`acceptance_feedback_candidate_promotion_check`.

When `next_operator_action.action` is
`run_next_ai_task_with_acceptance_feedback_context`, the check now requires:

- a package-level `acceptance_feedback_candidate_promotion` summary;
- a matching handoff-level `acceptance_feedback_candidate_promotion` summary;
- `candidate_included_in_context: true`;
- `decision_effect: included_in_context`;
- `candidate_blocked_from_context: false`.

The check fails with normal `failed_controls` if the summary is missing,
mismatched with handoff, or not actually included in next context.

Baseline packages without an acceptance-feedback context action are marked
`not_applicable` for this specific check and keep their existing package-check
behavior.

The read-only Web run-package-check view now surfaces the new check as:

- a workflow action;
- an `Acceptance promotion check` summary card;
- an `Acceptance promotion check` lane;
- protocol controls for check pass and context inclusion;
- artifact inspector facts for check status, decision effect, included status,
  and handoff/package match.

## Verification

Initial red backend result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check_acceptance_overlay.py -q
```

The test failed because the run package check did not expose
`acceptance_feedback_candidate_promotion_check`.

Initial red Web result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package_check.py -q
```

The new test failed because the selected-file run-package-check view did not
render an `Acceptance promotion check` lane.

Green and regression results:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check_acceptance_overlay.py -q
```

Result: `4 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Result: `8 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package_check.py -q
```

Result: `3 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check_acceptance_overlay.py tests\test_production_memory_operator_run_package_check.py tests\test_production_memory_operator_handoff_acceptance_feedback_overlay.py tests\test_web_static_production_memory_operator_run_package_check.py tests\test_web_static_production_memory_operator_handoff_acceptance_overlay.py tests\test_contract_examples.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `45 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests -k "web_static or web_memory" -q
```

Result: `79 passed, 790 deselected`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `870 passed` on Python 3.12.12.

## Contract Boundaries

- No provider call was made.
- No Company KB write was made.
- No durable memory write was made.
- No Web directory scanning, browser persistence, provider execution, or
  workflow execution was added.
- No Loulan-specific inspector, adapter, or content-production behavior was
  added.
- Passing this check is machine package consistency only. It is not human
  acceptance, business validation, provider success, durable Memory OS, or
  automatic memory promotion.

## Remaining Risks

- Browser-level verification was not run because Browser control tools were not
  exposed in this turn.
- Optional gated image/video provider validation was not attempted and is not
  part of this core milestone.
