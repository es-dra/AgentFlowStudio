# AFS-PRODUCTION-MEMORY-NEXT-PASS-RESULT-SCAFFOLD-001

Status: verified locally on
`codex/afs-production-memory-next-pass-result-scaffold-001`.

## Scope

Add a generic no-provider scaffold for
`agentflow_production_memory_next_pass_result`.

This is an enabling slice for `AFS-SECOND-PASS-001`: after a
`next_task_packet.json` is ready, the operator can create a local result
envelope that records which allowed context refs the next-pass output claims to
use. The existing next-pass review command can then inspect the result.

## Non-Goals

- no LLM/image/video/ASR provider call
- no generated content claim
- no next-pass execution claim
- no automatic feedback capture
- no memory candidate creation inside the scaffold
- no promotion decision
- no Company KB write
- no durable memory write
- no Loulan-specific behavior
- no human acceptance or business validation claim

## Implementation Files

- `agentflow/memory/production_next_pass_result.py`
- `apps/cli/production_memory_next_pass_result_command.py`
- `apps/cli/command_registry.py`
- `agentflow/memory/production_next_pass_review.py`
- `tests/test_production_memory_next_pass_result.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-draft-next-pass-result-no-provider data/processed/runs/production_memory_loop/next_task_packet/next_task_packet.json --generated-at 2026-06-02T11:00:00+08:00 --output-ref next-pass:artifact:operator-draft-001 --title "Second pass operator draft" --summary "Operator-supplied scaffold for the second pass." --output data/processed/runs/production_memory_loop/next_pass_result
```

The command writes:

- `next_pass_result.json`
- `next_pass_result.md`

## Behavior

- Requires `kind: agentflow_production_memory_next_task_packet`.
- Requires `packet_status: ready`.
- Defaults to all `allowed_context_refs` from the task packet.
- Rejects blocked or unknown refs supplied through `--used-context-ref`.
- Keeps `feedback_events` empty; feedback must be captured explicitly after
  operator review.
- Emits non-claims for generated content, provider success, human acceptance,
  business validation, durable memory, Company KB promotion, feedback capture,
  and memory promotion.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_result.py -q
```

Initial red result: failed because
`agentflow.memory.production_next_pass_result` did not exist.

Green result after implementation: `4 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_result.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_task_packet.py tests/test_production_memory_operator_loop.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `19 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_next_pass_result.py agentflow\memory\production_next_pass_review.py apps\cli\production_memory_next_pass_result_command.py apps\cli\command_registry.py
```

Result: passed.

CLI help includes
`production-memory-loop-draft-next-pass-result-no-provider`.

Runtime CLI smoke generated an ignored local chain under
`data/processed/runs/production_memory_loop/next_pass_result_scaffold_smoke/`:

```text
production-memory-loop-run-no-provider
  -> production-memory-loop-next-context-handoff
  -> production-memory-loop-next-task-packet
  -> production-memory-loop-draft-next-pass-result-no-provider
  -> production-memory-loop-review-next-pass
```

Result: review status `ready_for_operator_review`, provider calls false,
blocked or unknown refs `0`, and feedback candidates `0`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_result.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_task_packet.py tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_operator_loop_feedback_candidate_overlay.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `51 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `783 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0 with CRLF warnings only.

Touched code/test line counts remain under the 300-line target:

- `agentflow/memory/production_next_pass_result.py`: 174 lines
- `apps/cli/production_memory_next_pass_result_command.py`: 76 lines
- `agentflow/memory/production_next_pass_review.py`: 215 lines
- `apps/cli/command_registry.py`: 160 lines
- `tests/test_production_memory_next_pass_result.py`: 106 lines

## Remaining Risks

- This is still not a real second-pass execution. It only creates a local
  result envelope.
- Web does not yet render `agentflow_production_memory_next_pass_result` as a
  first-class selected artifact.
- Machine review of the scaffold is not human acceptance or business
  validation.
