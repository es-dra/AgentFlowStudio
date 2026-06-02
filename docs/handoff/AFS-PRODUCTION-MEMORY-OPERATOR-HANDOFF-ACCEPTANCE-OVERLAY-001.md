# AFS-PRODUCTION-MEMORY-OPERATOR-HANDOFF-ACCEPTANCE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-operator-handoff-acceptance-overlay-001`.

## Scope

Surface embedded acceptance feedback candidate promotion summaries in the
generic no-provider operator handoff packet and final operator run package.

This follows
`AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-ACCEPTANCE-FEEDBACK-CANDIDATE-OVERLAY-001`.
The operator-loop manifest already embeds the promoted acceptance feedback
candidate overlay; this slice makes the next operator handoff/package readable
without forcing the next run to infer state from scattered output artifacts.

## Implementation Files

- `agentflow/memory/production_operator_acceptance_feedback_candidate_handoff.py`
- `agentflow/memory/production_operator_handoff.py`
- `agentflow/memory/production_operator_run_package.py`
- `tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py`

## Behavior

When the source operator-loop manifest includes
`acceptance_feedback_candidate_promotion`:

- `operator_handoff_packet.json` includes the same promotion summary.
- `operator_run_package.json` inherits the same summary from the handoff
  packet.
- `operator_handoff_packet.md` and `operator_run_package.md` render an
  `Acceptance Feedback Candidate Promotion` section.
- A promoted/included acceptance feedback candidate changes
  `next_operator_action.action` to
  `run_next_ai_task_with_acceptance_feedback_context`.
- A blocked acceptance feedback candidate changes the action to
  `run_next_ai_task_without_acceptance_feedback_candidate`.

Baseline no-overlay handoffs keep the existing
`run_next_ai_task_from_next_task_packet` behavior.

## CLI Smoke

The smoke run uses only local no-provider commands and writes ignored artifacts
under:

```text
data/processed/runs/production_memory_loop/handoff_acceptance_overlay_smoke/
```

Final operator-loop command:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-03T05:20:00+08:00 --source-kb-status restructuring_or_unknown --acceptance-feedback-candidate-packet data/processed/runs/production_memory_loop/handoff_acceptance_overlay_smoke/acceptance_feedback_candidate/acceptance_feedback_candidate_packet.json --acceptance-feedback-candidate-promotion-decision data/processed/runs/production_memory_loop/handoff_acceptance_overlay_smoke/acceptance_feedback_candidate_promotion/acceptance_feedback_candidate_promotion_decision.json --write-run-package --write-run-package-check --output data/processed/runs/production_memory_loop/handoff_acceptance_overlay_smoke/operator_loop_with_acceptance_handoff
```

Observed final output:

- operator loop: `ready`
- acceptance feedback candidate promotion: `included_in_context`
- operator manifest check: `passed`
- operator handoff packet: `ready`
- operator run package: `ready`
- operator run package check: `passed`
- final handoff action:
  `run_next_ai_task_with_acceptance_feedback_context`

## Verification

Initial red result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py -q
```

The focused test failed because `operator_handoff_packet.json` did not expose
`acceptance_feedback_candidate_promotion`.

Green and regression results:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py -q
```

Result: `1 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_handoff_packet.py tests/test_production_memory_operator_run_package.py tests/test_production_memory_operator_run_package_check.py -q
```

Result: `20 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py -q
```

Result: `6 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py tests/test_production_memory_operator_handoff_packet.py tests/test_production_memory_operator_run_package.py tests/test_production_memory_operator_run_package_check.py tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `52 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_run_package.py tests/test_web_static_production_memory_operator_run_package_check.py -q
```

Result: `8 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_handoff.py agentflow/memory/production_operator_run_package.py tests/test_production_memory_operator_handoff_acceptance_feedback_overlay.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `862 passed` on Python 3.12.12.

## Contract Boundaries

- acceptance feedback remains feedback evidence until explicitly converted into
  a candidate and explicit promotion decision.
- candidate-only packets and pending templates are not promoted memory.
- this slice does not write durable memory or Company KB.
- this slice does not execute a next pass or call providers.
- the CLI smoke uses synthetic local feedback for verification only; it is not
  new human acceptance, business validation, provider success, or memory
  promotion.
- no Loulan-specific inspector, adapter, or content-production behavior was
  added.

## Remaining Risks

- Browser-level verification was not run for this slice; static Web regression
  was run only to ensure related read-only views still parse.
- Optional provider validation was not attempted or required.
