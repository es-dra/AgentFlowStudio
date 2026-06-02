# AFS-PRODUCTION-MEMORY-ACCEPTANCE-FEEDBACK-PROMOTION-001

Status: verified locally on
`codex/afs-production-memory-acceptance-feedback-promotion-001`.

## Scope

Convert a selected
`agentflow_production_memory_acceptance_feedback_candidate_packet` into an
explicit no-provider operator decision artifact, then render that decision in
the read-only generic Web memory workbench.

This closes the explicit review step after candidate-only acceptance feedback
drafting. It does not write durable memory, write Company KB, execute the next
pass, call providers, claim new human acceptance, or claim business validation.

## Implementation Files

- `agentflow/memory/production_acceptance_feedback_candidate_promotion.py`
- `apps/cli/production_memory_acceptance_feedback_candidate_promotion_command.py`
- `apps/cli/command_registry.py`
- `apps/web/memory-workbench-production-acceptance-feedback-candidate-promotion.js`
- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_production_memory_acceptance_feedback_candidate_promotion.py`
- `tests/test_web_static_production_memory_acceptance_feedback_candidate_promotion.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-review-acceptance-feedback-candidate data/processed/runs/production_memory_loop/acceptance_feedback_candidate/acceptance_feedback_candidate_packet.json --decision promoted --rationale "Traceable acceptance feedback selected for the next context overlay." --decided-at 2026-06-03T02:15:00+08:00 --output data/processed/runs/production_memory_loop/acceptance_feedback_candidate_promotion
```

The command writes:

- `acceptance_feedback_candidate_promotion_decision.json`
- `acceptance_feedback_candidate_promotion_decision.md`

## Contract Boundaries

- acceptance feedback candidate packets still require an explicit operator
  decision before reuse.
- pending promotion templates cannot be used as reviewed decisions.
- promoted and merged decisions set `candidate_reuse_allowed: true`.
- rejected, expired, and blocked decisions keep candidate reuse blocked.
- blocked candidates cannot be promoted or merged.
- the decision records source packet, source acceptance feedback event, source
  pending template id, candidate id, source human acceptance decision, reviewer
  role, rationale, and decision effect.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- `decision_is_durable_memory_write: false`
- `decision_writes_company_kb: false`
- `candidate_is_durable_memory: false`
- `business_validation: not_validated`

## Web

The read-only Web workbench now recognizes selected
`acceptance_feedback_candidate_promotion_decision.json` files and renders:

- explicit decision;
- source acceptance decision;
- candidate reuse status;
- decision effect;
- business-validation boundary;
- memory and Company KB write boundaries;
- no-provider controls.

The Web slice is selected-file only. It does not scan directories, persist
browser state, execute workflows, call providers, follow refs, or add
project-specific inspector behavior.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate_promotion.py -q
```

Initial red result: CLI invocation failed because
`production-memory-loop-review-acceptance-feedback-candidate` was not
registered.

Green result after implementation: `7 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate_promotion.py tests\test_web_static_production_memory_acceptance_feedback_candidate_promotion.py -q
```

Result: `9 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_acceptance_feedback_candidate_promotion.py apps\cli\production_memory_acceptance_feedback_candidate_promotion_command.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback.py tests\test_production_memory_acceptance_feedback_candidate.py tests\test_production_memory_acceptance_feedback_candidate_promotion.py tests\test_web_static_production_memory_acceptance_feedback.py tests\test_web_static_production_memory_acceptance_feedback_candidate.py tests\test_web_static_production_memory_acceptance_feedback_candidate_promotion.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py -q
```

Result: `49 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-review-acceptance-feedback-candidate --help
```

Result: passed.

CLI smoke used the ignored
`acceptance_feedback_candidate_smoke/acceptance_feedback_candidate_packet.json`
artifact and wrote an explicit promoted decision under:

```text
data/processed/runs/production_memory_loop/acceptance_feedback_candidate_promotion_smoke/
```

The smoke JSON had:

- `kind=agentflow_production_memory_acceptance_feedback_candidate_promotion_decision`
- `decision=promoted`
- `decision_effect=eligible_for_next_context_overlay`
- `candidate_reuse_allowed=true`
- `provider_calls_started=false`
- `writes_long_term_memory=false`
- `writes_company_kb=false`
- `human_acceptance=accepted`
- `business_validation=not_validated`

The smoke output is ignored by `.gitignore`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `850 passed` on Python 3.12.12.

## Line Counts

Initial checked line counts:

- `agentflow/memory/production_acceptance_feedback_candidate_promotion.py`: 247.
- `apps/cli/production_memory_acceptance_feedback_candidate_promotion_command.py`: 68.
- `apps/web/memory-workbench-production-acceptance-feedback-candidate-promotion.js`: 158.
- `tests/test_production_memory_acceptance_feedback_candidate_promotion.py`: 186.
- `tests/test_web_static_production_memory_acceptance_feedback_candidate_promotion.py`: 159.
- `apps/web/artifact-workspace.js`: 300.

## Remaining Risks

- This slice does not build a next-context overlay from the acceptance feedback
  candidate decision. A follow-up should decide whether promoted or merged
  acceptance feedback candidates can be added to a derived context bundle.
- Browser-level smoke was not required for this slice; static Web tests verify
  selected-file rendering only.
- No provider validation was attempted or required.
- Machine tests are not human acceptance or business validation.
