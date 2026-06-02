# AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-001

Status: verified locally on
`codex/afs-production-memory-operator-run-package-check-001`.

## Scope

Add a read-only handoff-time consistency check for selected
`agentflow_production_memory_operator_run_package` artifacts.

This follows `AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-001` and
`AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-WEB-001`: the run package is now
an entry artifact for the next unattended operator, and the check confirms that
the package item refs and no-provider/write boundaries are still usable before
the next operator relies on it.

## Implementation Files

- `agentflow/memory/production_operator_run_package_check.py`
- `apps/cli/production_memory_operator_run_package_check_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_operator_run_package_check.py`
- `docs/architecture/production_memory_architecture.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-check-operator-run-package `
  data/processed/runs/production_memory_loop/operator_run_package_smoke/operator_run_package/operator_run_package.json `
  --output data/processed/runs/production_memory_loop/operator_run_package_smoke/operator_run_package_check/operator_run_package_check.json
```

The command reads one explicit package JSON. If the package path is under an
`operator_run_package/` folder, the default artifact root is the parent operator
loop output directory. Operators may override that with `--artifact-root`.

## Behavior

- Validates the selected JSON kind.
- Checks every `package_items[].path` for unsafe, missing, and mismatched refs.
- Confirms Markdown package items exist without parsing them as JSON.
- Independently rechecks provider, durable-memory, and Company KB write
  boundaries even if the package's embedded controls are stale.
- Writes an optional JSON check report.
- Exits non-zero when the package is not ready for handoff.

## Boundaries

- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution.
- No ref following beyond existence/type checks.
- No next-pass execution.
- No automatic memory promotion.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Initial result: failed because
`agentflow.memory.production_operator_run_package_check` did not exist.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Result: `4 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py tests\test_production_memory_operator_run_package.py tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_handoff_packet.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `23 passed`.

Py compile:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_run_package_check.py apps\cli\production_memory_operator_run_package_check_command.py apps\cli\command_registry.py tests\test_production_memory_operator_run_package_check.py
```

Result: passed.

CLI help:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-check-operator-run-package --help
```

Result: passed.

CLI smoke:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T20:40:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --output data/processed/runs/production_memory_loop/operator_run_package_check_smoke
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-check-operator-run-package data/processed/runs/production_memory_loop/operator_run_package_check_smoke/operator_run_package/operator_run_package.json --output data/processed/runs/production_memory_loop/operator_run_package_check_smoke/operator_run_package_check/operator_run_package_check.json
```

Result: check passed with `ready_for_handoff=true`, 18 checked items, 0 missing
refs, 0 failed controls, no provider call, and no Company KB write.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `821 passed`.

CLI surface:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: command list includes
`production-memory-loop-check-operator-run-package`.

`git diff --check` passed with CRLF normalization warnings only.

High-risk added-diff sensitive scan was clean.

## Line Counts

- `agentflow/memory/production_operator_run_package_check.py`: 178 lines
- `apps/cli/production_memory_operator_run_package_check_command.py`: 55 lines
- `apps/cli/command_registry.py`: 178 lines
- `tests/test_production_memory_operator_run_package_check.py`: 101 lines

## Remaining Verification

- Staged diff and staged sensitive-content checks before commit.

## Remaining Risks

- The check proves package-ref consistency only; it is not human acceptance,
  business validation, provider success, durable Memory OS behavior, or Company
  KB promotion.
- Generated smoke artifacts must remain ignored under `data/processed/`.
