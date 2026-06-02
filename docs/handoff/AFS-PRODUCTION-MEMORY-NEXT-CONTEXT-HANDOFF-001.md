# AFS-PRODUCTION-MEMORY-NEXT-CONTEXT-HANDOFF-001 Handoff

Status: verified locally; local-only branch slice.

Branch:

```text
codex/afs-production-memory-next-context-handoff-001
```

Base:

```text
codex/afs-production-memory-operator-loop-web-001 @ a39a719
```

## Scope

Generate a no-provider next-context handoff artifact for the next AI task from
an assembled production-memory run.

The handoff writes:

- `next_context_handoff.json`
- `next_context_handoff.md`

It is also emitted by:

```text
production-memory-loop-run-operator-no-provider
```

## Contract

The artifact kind is:

```text
agentflow_production_memory_next_context_handoff
```

It records:

- `next_context_refs` from `context_bundle.included_refs`;
- `blocked_refs` kept separate from next task context;
- no-provider controls;
- a bounded task prompt;
- non-claim boundaries for human acceptance, business validation, durable
  Memory OS, provider success, and Company KB promotion.

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
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_production_memory_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
git diff --check
```

Current result:

```text
RED: next-context handoff test failed on missing production_next_context module.
GREEN: tests/test_production_memory_next_context_handoff.py -> 3 passed.
Operator-loop integration RED: missing next_context_handoff outputs.
Operator-loop integration GREEN: handoff/operator/Web focused suite -> 7 passed.
Focused production-memory/contract suite -> 43 passed.
CLI help passed; production-memory-loop-next-context-handoff is visible.
CLI smoke wrote ignored next_context_handoff JSON/Markdown outputs.
Full suite -> 720 passed on Python 3.12.12.
```
