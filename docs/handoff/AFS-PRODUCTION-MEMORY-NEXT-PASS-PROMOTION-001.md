# AFS-PRODUCTION-MEMORY-NEXT-PASS-PROMOTION-001

Status: verified locally on
`codex/afs-production-memory-next-pass-promotion-001`.

## Scope

Add the explicit decision layer after `next_pass_review.json`.

This slice consumes:

- a selected `agentflow_production_memory_next_pass_review`;
- one selected next-pass feedback candidate id;
- an explicit operator decision of `promoted`, `merged`, `rejected`,
  `expired`, or `blocked`.

It produces:

- `next_pass_promotion_decision.json`;
- `derived_production_memory_loop.json`;
- `production_memory_loop_run.json`;
- `context_bundle.json`;
- `pass_readiness.json`;
- `next_pass_bundle.json`;
- `next_pass_promotion_overlay.json`.

## Commands

```powershell
python -m apps.cli.main production-memory-loop-review-next-pass-promotion data/processed/runs/production_memory_loop/next_pass_review/next_pass_review.json --candidate-id memory-candidate-feedback-next-pass-001 --decision promoted --rationale "Traceable next-pass feedback selected by the operator." --decided-at 2026-06-02T05:10:00+08:00 --output data/processed/runs/production_memory_loop/next_pass_promotion_decision
python -m apps.cli.main production-memory-loop-run-next-pass-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --next-pass-review data/processed/runs/production_memory_loop/next_pass_review/next_pass_review.json --promotion-decision data/processed/runs/production_memory_loop/next_pass_promotion_decision/next_pass_promotion_decision.json --output data/processed/runs/production_memory_loop/next_pass_reviewed_feedback
```

## Implementation Files

- `agentflow/memory/production_next_pass_promotion.py`
- `agentflow/memory/production_next_pass_promotion_records.py`
- `apps/cli/production_memory_next_pass_promotion_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_next_pass_promotion.py`

## Boundaries

- No provider call.
- No next-pass execution.
- No Company KB write.
- No durable memory write.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

Pending promotion templates from `next_pass_review.json` are rejected by the
overlay command. Only an explicit next-pass promotion decision can affect the
derived context bundle.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_promotion.py -q
```

Result: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_promotion.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_operator_loop.py tests/test_production_memory_next_task_packet.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `44 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `742 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

## Remaining Risks

- This slice does not add a Web renderer for
  `agentflow_production_memory_next_pass_promotion_decision` or
  `agentflow_production_memory_next_pass_promotion_overlay`.
- No provider validation was attempted.
