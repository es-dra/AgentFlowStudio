# AFS-COMPANY-KB-FEEDBACK-PACKET-001 Handoff

Status: verified locally; local-only branch slice.

Branch:

```text
codex/afs-company-kb-feedback-packet-001
```

Base:

```text
codex/afs-production-memory-session-report-001 @ 8c15930
```

## Scope

Add a generic candidate-only packet that turns a production-memory session
report into reviewable Company KB feedback candidates.

The packet records:

- source session, loop, project, and context signal;
- candidate-only reusable lessons;
- non-claim boundaries;
- source KB status metadata;
- explicit non-promotions.

## Boundaries

- No remote provider calls.
- No Company source knowledge-base write.
- No durable memory write.
- No human acceptance or business validation claim.
- No provider success claim.
- No private Company strategy, real costs, provider secrets, customer details,
  or unpublished business judgment.

## CLI

```powershell
python -m apps.cli.main production-memory-loop-company-kb-candidates data/processed/runs/production_memory_loop/session_report/production_memory_session_report.json --generated-at 2026-06-02T00:20:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/company_kb_candidates
```

Writes ignored runtime artifacts:

- `company_kb_feedback_candidate_packet.json`
- `company_kb_feedback_candidate_packet.md`

## Verification

```text
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_company_kb_feedback_packet.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_contract_examples.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-no-provider examples/agentflow/production_memory_loop.example.json --output data/processed/runs/production_memory_loop/no_provider
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-session-report data/processed/runs/production_memory_loop/no_provider/production_memory_loop_run.json --generated-at 2026-06-02T00:10:00+08:00 --output data/processed/runs/production_memory_loop/session_report
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-company-kb-candidates data/processed/runs/production_memory_loop/session_report/production_memory_session_report.json --generated-at 2026-06-02T00:20:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/company_kb_candidates
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_company_kb_feedback_packet.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_production_memory_session_report.py tests/test_production_memory_loop.py tests/test_cli_command_registry_boundaries.py -q
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
git diff --check
```

Current result:

```text
5 passed
24 passed
CLI help passed; new command is visible
no-provider run ready
session report ready
candidate packet candidate_only; writes Company KB false; 3 candidate items
52 passed
711 passed on Python 3.12.12
git diff --check -> exit 0; CRLF normalization warnings only
```

## Commit Boundary

Local commit is allowed for this branch slice. Do not push or create a PR
without explicit instruction.
