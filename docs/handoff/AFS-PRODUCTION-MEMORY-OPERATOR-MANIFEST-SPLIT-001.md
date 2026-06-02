# AFS-PRODUCTION-MEMORY-OPERATOR-MANIFEST-SPLIT-001

Status: verified locally on
`codex/afs-production-memory-operator-manifest-split-001`.

## Scope

Split next-pass helper logic out of the main production-memory operator
manifest module.

This is a structural slice after
`AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-NEXT-PASS-RESULT-SCAFFOLD-001`.
`agentflow/memory/production_operator_manifest.py` had reached exactly 300
lines, so future operator-loop work needed room before adding more behavior.

## Implementation Files

- `agentflow/memory/production_operator_manifest.py`
- `agentflow/memory/production_operator_next_pass_manifest.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior Boundary

No production-memory contract changed.

The new helper owns only next-pass operator-manifest projections:

- next-pass result ready gate and summary;
- next-pass review ready gate and summary;
- next-pass promotion ready gate, controls, nodes, and summary.

The main manifest still owns the overall operator-loop manifest shape, core
source/run/session/Company KB candidate summaries, and final manifest assembly.

## Contract Boundaries

- no CLI surface change
- no Web behavior change
- no provider call
- no Company KB write
- no durable memory write
- no next-pass execution
- no Loulan-specific behavior
- no human acceptance or business validation claim

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_manifest.py agentflow\memory\production_operator_next_pass_manifest.py agentflow\memory\production_operator_loop.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop_result_scaffold.py -q
```

Result: `15 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_operator_loop_feedback_candidate_overlay.py tests/test_production_memory_next_pass_result.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_pass_promotion.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop_feedback_candidate.py tests/test_web_static_production_memory_operator_loop_result_scaffold.py tests/test_web_static_production_memory_next_pass_result.py tests/test_web_static_production_memory_next_pass_review.py tests/test_web_static_production_memory_next_pass_promotion.py -q
```

Result: `67 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `790 passed`.

## Line Counts

Measured by PowerShell `Get-Content` item count:

- `agentflow/memory/production_operator_manifest.py`: 230 lines
- `agentflow/memory/production_operator_next_pass_manifest.py`: 156 lines
- `agentflow/memory/production_operator_feedback_candidate_manifest.py`: 95
  lines

## Remaining Risks

- This slice does not add new operator behavior; it only makes the current
  operator-loop manifest safer to extend.
