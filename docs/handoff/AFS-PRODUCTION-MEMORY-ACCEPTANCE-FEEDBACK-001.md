# AFS-PRODUCTION-MEMORY-ACCEPTANCE-FEEDBACK-001

Status: verified locally on
`codex/afs-production-memory-acceptance-feedback-001`.

## Scope

This slice records a human-supplied package-level feedback decision after an
explicit `operator_run_package_check.json`.

Added command:

```powershell
python -m apps.cli.main production-memory-loop-record-acceptance-feedback data/processed/runs/production_memory_loop/operator_run_package_smoke/operator_run_package_check/operator_run_package_check.json --decision accepted --summary "Human operator accepted the package for the next local iteration." --reviewed-at 2026-06-03T00:05:00+08:00 --output data/processed/runs/production_memory_loop/acceptance_feedback
```

The command writes:

- `acceptance_feedback_event.json`
- `acceptance_feedback_event.md`

## Contract

- Artifact kind:
  `agentflow_production_memory_acceptance_feedback_event`.
- Supported decisions: `accepted`, `rejected`, `needs_revision`.
- `accepted` requires the source package check to be `passed` and
  `ready_for_handoff=true`.
- `rejected` and `needs_revision` can record human blockers from a failed or
  not-ready package check.
- The event records human acceptance feedback only. It does not create memory
  candidates, create promotion decisions, write durable memory, write Company
  KB, call providers, or claim business validation.

## Web

The read-only Web workbench now recognizes selected
`acceptance_feedback_event.json` files and renders:

- explicit acceptance decision;
- source package check status;
- ready-for-handoff state;
- business-validation boundary;
- memory and Company KB write boundaries;
- no-provider controls.

The Web slice is selected-file only. It does not scan directories, persist
browser state, execute workflows, call providers, follow refs, or add
project-specific inspector behavior.

## Verification

- Red test failed first because the acceptance feedback module did not exist.
- `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback.py -q`
  passed (`4 passed`).
- `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_acceptance_feedback.py -q`
  passed (`2 passed`).
- Py compile for touched Python files passed.
- JS import smoke for the new Web module, controller, and workspace passed.
- Focused production-memory/Web/contract regression passed (`52 passed`).
- `python -m apps.cli.main --help` passed and lists the new command.
- `production-memory-loop-validate` passed on the generic example.
- `production-memory-loop-run-no-provider` passed and wrote ignored runtime
  outputs.
- CLI smoke wrote ignored `acceptance_feedback_event.json` and
  `acceptance_feedback_event.md` from a passed run package check.
- Full suite passed on Python 3.12.12 (`833 passed`).
- `git diff --check` passed with CRLF normalization warnings only.
- Added-diff and new-file sensitive scans were clean.

## Line Counts

Initial checked line counts:

- `agentflow/memory/production_acceptance_feedback.py`: 204.
- `apps/cli/production_memory_acceptance_feedback_command.py`: 57.
- `apps/web/memory-workbench-production-acceptance-feedback.js`: 125.
- `tests/test_production_memory_acceptance_feedback.py`: 127.
- `tests/test_web_static_production_memory_acceptance_feedback.py`: 131.
- `apps/web/artifact-workspace.js`: 282.

## Remaining Risks

- This is not business validation. The user still needs to choose real
  artifacts and perform the actual review before making a production business
  decision.
- The event is evidence for the AFS loop only. It is not Company KB memory and
  does not promote any memory candidate.
- Browser-level smoke is separate from static Web tests and should not be
  described as human acceptance.
