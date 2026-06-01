# AFS-PRODUCTION-MEMORY-NEXT-TASK-PACKET-001 Handoff

Status: verified locally; local-only branch slice.

Branch:

```text
codex/afs-production-memory-next-task-packet-001
```

Base:

```text
codex/afs-production-memory-next-context-handoff-web-001 @ b223b00
```

## Scope

Consume a no-provider next-context handoff into an auditable next-task packet
for a future AI task.

The command writes:

- `next_task_packet.json`
- `next_task_packet.md`

It is also emitted by:

```text
production-memory-loop-run-operator-no-provider
```

## Contract

The artifact kind is:

```text
agentflow_production_memory_next_task_packet
```

It records:

- `allowed_context_refs` copied only from ready `next_context_refs`;
- `blocked_refs` retained but excluded from task context;
- no-provider controls;
- task instructions that repeat feedback, candidate, and promotion boundaries;
- non-claim boundaries for next-pass execution, human acceptance, business
  validation, durable Memory OS, provider success, and Company KB promotion.

## Boundaries

- No remote provider calls.
- No Company source knowledge-base write.
- No durable memory write.
- No next-pass execution.
- No automatic ref following.
- No human acceptance or business validation claim.

## Verification

Fresh verification should include:

```text
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_task_packet.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_task_packet.py tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
git diff --check
```

Current result:

```text
RED: next-task packet test failed on missing production_next_task module.
GREEN: tests/test_production_memory_next_task_packet.py -> 4 passed.
Operator-loop integration RED: missing next_task_packet node and outputs.
Operator-loop integration GREEN: tests/test_production_memory_operator_loop.py -> 2 passed.
Focused production-memory/contract suite -> 35 passed.
CLI help passed; production-memory-loop-next-task-packet is visible.
CLI smoke wrote ignored next-task packet JSON/Markdown outputs through the
operator-loop command.
Full suite -> 726 passed on Python 3.12.12.
git diff --check -> exit 0; CRLF normalization warnings only.
```
