# AFS-PRODUCTION-MEMORY-NEXT-TASK-PACKET-WEB-001 Handoff

Status: verified locally; local-only branch slice.

Branch:

```text
codex/afs-production-memory-next-task-packet-web-001
```

Base:

```text
codex/afs-production-memory-next-task-packet-001 @ fda540b
```

## Scope

Render a no-provider production-memory next-task packet artifact in the generic
read-only Web memory workbench.

The Web view recognizes selected local JSON with:

```text
kind: agentflow_production_memory_next_task_packet
```

It renders:

- allowed context refs;
- blocked refs;
- no-provider controls;
- Company KB and durable-memory write-disabled boundaries;
- non-claim boundaries for next-pass execution, human acceptance, business
  validation, provider success, durable Memory OS, and Company KB promotion.

## Boundaries

- No remote provider calls.
- No Company source knowledge-base write.
- No durable memory write.
- No directory scan.
- No browser persistence.
- No workflow execution from Web.
- No automatic ref following.
- No Loulan-specific inspector.
- No human acceptance or business validation claim.

## Verification

Fresh verification should include:

```text
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_task_packet.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_task_packet.py tests/test_web_static_production_memory_next_context_handoff.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_task_packet.py tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_next_task_packet.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
git diff --check
```

Current result:

```text
RED: Web static next-task packet test failed before implementation because the artifact source role was unclassified.
GREEN: tests/test_web_static_production_memory_next_task_packet.py -> 2 passed.
Focused Web suite -> 29 passed.
Focused production-memory/contract suite -> 37 passed.
Full suite -> 728 passed on Python 3.12.12.
git diff --check -> exit 0; CRLF normalization warnings only.
```
