# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-001 Handoff

Status: verified locally; local-only branch slice.

Branch:

```text
codex/afs-production-memory-operator-loop-001
```

Base:

```text
codex/afs-company-kb-feedback-web-001 @ ed968b6
```

## Scope

Add a single no-provider orchestration command for the generic AFS production
memory operator loop.

The command runs:

```text
production_memory_loop
  -> production_memory_loop_run
  -> context_bundle
  -> pass_readiness
  -> next_pass_bundle
  -> production_memory_session_report
  -> company_kb_feedback_candidate_packet
  -> production_memory_operator_loop_run manifest
```

## CLI

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T01:00:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/operator_loop
```

Writes ignored runtime artifacts:

- `run/production_memory_loop_run.json`
- `run/context_bundle.json`
- `run/pass_readiness.json`
- `run/next_pass_bundle.json`
- `session_report/production_memory_session_report.json`
- `session_report/production_memory_session_report.md`
- `company_kb_candidates/company_kb_feedback_candidate_packet.json`
- `company_kb_candidates/company_kb_feedback_candidate_packet.md`
- `production_memory_operator_loop_run.json`

## Boundaries

- No remote provider calls.
- No Company source knowledge-base write.
- No durable memory write.
- No browser persistence or Web execution change.
- No Loulan-specific adapter.
- No human acceptance or business validation claim.

## Verification

```text
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T01:00:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/operator_loop
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_loop.py tests/test_production_memory_session_report.py tests/test_company_kb_feedback_packet.py tests/test_agentflow_contract_audit.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Current result:

```text
2 passed
CLI help passed; command is visible
operator loop ready; wrote all runtime artifacts under ignored output
54 passed
715 passed on Python 3.12.12
```

## Next

Optional Web recognition for `agentflow_production_memory_operator_loop_run`
can be added later if the operator needs to inspect the manifest directly in
the memory workbench. Keep it read-only and generic.
