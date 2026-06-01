# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-PROMOTION-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-promotion-overlay-001`.

## Scope

Let the generic no-provider operator-loop command include an explicit
next-pass promotion decision and its derived follow-up context overlay in the
same auditable manifest.

This extends the existing optional `--next-pass-result` path. The promotion
decision option is valid only when the next-pass result is supplied, because
the decision must be validated against the generated `next_pass_review`.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `agentflow/memory/production_operator_manifest.py`
- `agentflow/memory/production_operator_outputs.py`
- `apps/cli/production_memory_operator_command.py`
- `tests/test_production_memory_operator_loop_promotion.py`

## CLI Surface

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T06:00:00+08:00 --source-kb-status restructuring_or_unknown --next-pass-result next_pass_result.json --next-pass-promotion-decision next_pass_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_loop_with_promotion
```

## Output Additions

When a promotion decision is supplied, the operator-loop output includes:

- `next_pass_promotion_decision/next_pass_promotion_decision.json`
- `next_pass_reviewed_feedback/derived_production_memory_loop.json`
- `next_pass_reviewed_feedback/production_memory_loop_run.json`
- `next_pass_reviewed_feedback/context_bundle.json`
- `next_pass_reviewed_feedback/pass_readiness.json`
- `next_pass_reviewed_feedback/next_pass_bundle.json`
- `next_pass_reviewed_feedback/next_pass_promotion_overlay.json`

The manifest includes separate nodes for:

- `next_pass_review`
- `next_pass_promotion_decision`
- `next_pass_promotion_overlay`

## Boundaries

- No provider call.
- No next-pass execution.
- No Company KB write.
- No durable memory write.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification So Far

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_promotion.py -q
```

Result: `3 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py -q
```

Result: `7 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_operator_loop.py tests/test_production_memory_next_pass_promotion.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_task_packet.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py -q
```

Result: `49 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed.

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider ... --next-pass-result ... --next-pass-promotion-decision ...
```

Result: wrote ignored runtime artifacts and reported
`Next pass promotion: included_in_context`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `747 passed` on Python 3.12.12.

## Remaining Verification

- `git diff --check`
- staged sensitive scan before commit
