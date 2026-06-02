# AFS-PRODUCTION-MEMORY-ACCEPTANCE-FEEDBACK-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-acceptance-feedback-overlay-001`.

## Scope

Overlay one explicitly reviewed
`agentflow_production_memory_acceptance_feedback_candidate_packet` and
`agentflow_production_memory_acceptance_feedback_candidate_promotion_decision`
onto the generic production-memory loop, then build a no-provider derived
context bundle and readiness report.

This closes the backend context-reuse step after explicit acceptance feedback
candidate review. It does not write durable memory, write Company KB, call
providers, execute the next pass, claim new human acceptance, or claim business
validation.

## Implementation Files

- `agentflow/memory/production_acceptance_feedback_candidate_overlay.py`
- `apps/cli/production_memory_acceptance_feedback_candidate_overlay_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_acceptance_feedback_candidate_overlay.py`
- `docs/architecture/production_memory_architecture.md`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-run-acceptance-feedback-candidate-reviewed-no-provider examples/agentflow/production_memory_loop.example.json --candidate-packet data/processed/runs/production_memory_loop/acceptance_feedback_candidate/acceptance_feedback_candidate_packet.json --promotion-decision data/processed/runs/production_memory_loop/acceptance_feedback_candidate_promotion/acceptance_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/acceptance_feedback_candidate_reviewed
```

The command writes:

- `derived_production_memory_loop.json`
- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`
- `acceptance_feedback_candidate_promotion_overlay.json`

## Contract Boundaries

- pending promotion templates cannot drive the overlay.
- the decision must match the candidate packet, source acceptance feedback
  event, source pending template id, and candidate id.
- promoted and merged decisions can include the candidate in the derived
  context bundle.
- rejected, expired, and blocked decisions keep the candidate in blocked refs.
- blocked candidates cannot be promoted or merged.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- the overlay is not new human acceptance.
- the overlay is not business validation.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate_overlay.py -q
```

Initial red result: collection failed because
`agentflow.memory.production_acceptance_feedback_candidate_overlay` did not
exist.

Green result after implementation: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_acceptance_feedback_candidate_overlay.py apps\cli\production_memory_acceptance_feedback_candidate_overlay_command.py apps\cli\command_registry.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-acceptance-feedback-candidate-reviewed-no-provider --help
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback.py tests\test_production_memory_acceptance_feedback_candidate.py tests\test_production_memory_acceptance_feedback_candidate_promotion.py tests\test_production_memory_acceptance_feedback_candidate_overlay.py tests\test_production_memory_operator_feedback_candidate_overlay.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py -q
```

Result: `53 passed`.

CLI smoke used ignored acceptance candidate and promotion decision artifacts,
then wrote a reviewed no-provider context run under:

```text
data/processed/runs/production_memory_loop/acceptance_feedback_candidate_reviewed_smoke/
```

The smoke overlay had:

- `kind=agentflow_production_memory_acceptance_feedback_candidate_promotion_overlay`
- `decision=promoted`
- `decision_effect=included_in_context`
- `candidate_included_in_context=true`
- `provider_calls_started=false`
- `writes_long_term_memory=false`
- `writes_company_kb=false`
- `source_acceptance_decision=accepted`

The smoke output is ignored by `.gitignore`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `855 passed` on Python 3.12.12.

## Line Counts

Initial checked line counts:

- `agentflow/memory/production_acceptance_feedback_candidate_overlay.py`: 271.
- `apps/cli/production_memory_acceptance_feedback_candidate_overlay_command.py`: 82.
- `tests/test_production_memory_acceptance_feedback_candidate_overlay.py`: 176.

## Remaining Risks

- This slice does not integrate the acceptance feedback candidate overlay into
  the no-provider operator-loop command or operator-loop manifest.
- This slice does not add Web rendering for the standalone overlay artifact.
- No provider validation was attempted or required.
- Machine tests are not human acceptance or business validation.
