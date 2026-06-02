# AFS-PRODUCTION-MEMORY-WEB-HANDOFF-ACCEPTANCE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-web-handoff-acceptance-overlay-001`.

## Scope

Render embedded acceptance feedback candidate promotion summaries in the
read-only Web Memory Workbench selected-file views for:

- `agentflow_production_memory_operator_handoff_packet`
- `agentflow_production_memory_operator_run_package`

This follows
`AFS-PRODUCTION-MEMORY-OPERATOR-HANDOFF-ACCEPTANCE-OVERLAY-001`, which added
the same promotion summary to the JSON and Markdown handoff/package artifacts.
This slice only projects that existing field into Web.

## Implementation Files

- `apps/web/memory-workbench-production-acceptance-feedback-handoff.js`
- `apps/web/memory-workbench-production-operator-handoff.js`
- `apps/web/memory-workbench-production-operator-run-package.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_web_static_production_memory_operator_handoff_acceptance_overlay.py`

## Behavior

When a selected operator handoff packet or operator run package includes
`acceptance_feedback_candidate_promotion`, the Web view now exposes:

- a workflow action for inspecting the acceptance feedback candidate promotion;
- an `Acceptance feedback candidate` summary card;
- an `acceptance_feedback_candidate_promotion` memory-loaded item;
- an `Acceptance feedback candidate` lane;
- a protocol control for whether the candidate is included in context;
- artifact inspector facts for decision, decision effect, and included status.

Baseline handoff/package artifacts without the field keep their existing view.

## Verification

Initial red result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_handoff_acceptance_overlay.py -q
```

The test failed because the selected-file handoff and run-package views did not
render an `Acceptance feedback candidate` lane.

Green and regression results:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_handoff_acceptance_overlay.py -q
```

Result: `3 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_handoff_packet.py tests/test_web_static_production_memory_operator_run_package.py tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py tests/test_web_static_production_memory_operator_run_package_check.py -q
```

Result: `7 passed`.

```powershell
node --check apps/web/memory-workbench-production-acceptance-feedback-handoff.js
node --check apps/web/memory-workbench-production-operator-handoff.js
node --check apps/web/memory-workbench-production-operator-run-package.js
node --check apps/web/memory-workbench-production-inspector-facts.js
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py tests/test_production_memory_operator_run_package.py tests/test_production_memory_operator_handoff_packet.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `39 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests -k "web_static or web_memory" -q
```

Result: `78 passed, 787 deselected`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `865 passed` on Python 3.12.12.

## Contract Boundaries

- Web reads selected local JSON artifacts only.
- No directory scan, browser persistence, provider execution, provider call, or
  workflow execution was added.
- No Loulan-specific inspector, adapter, or content-production behavior was
  added.
- Acceptance feedback candidate promotion remains operator evidence for context
  assembly; it is not durable memory, Company KB promotion, business
  validation, provider success, or new human acceptance.

## Remaining Risks

- Browser-level verification was not run because Browser control tools were not
  exposed in this turn.
- Optional provider validation was not attempted or required.
