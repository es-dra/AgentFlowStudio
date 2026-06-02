# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-MANIFEST-CHECK-OUTPUT-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-manifest-check-output-001`.

## Scope

Let the generic no-provider operator-loop command optionally write the
operator manifest consistency check report in the same unattended run.

This connects the previous standalone check command to the main operator-loop
execution path without changing the default output shape.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `apps/cli/production_memory_operator_command.py`
- `tests/test_production_memory_operator_loop.py`
- `tests/test_production_memory_operator_loop_manifest_check.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior Boundary

New explicit option:

```powershell
production-memory-loop-run-operator-no-provider <loop.json> --write-manifest-check --output <dir>
```

When enabled, the command writes:

```text
operator_manifest_check/operator_manifest_check.json
```

Default behavior remains unchanged: without `--write-manifest-check`, the
operator-loop command does not write the check report.

This slice does not call providers, write Company KB, write durable memory,
change Web behavior, add Loulan behavior, execute a next pass, or claim human
acceptance/business validation.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py -q
```

Result before implementation: failed because
`write_production_memory_operator_loop_run` did not accept
`write_manifest_check` and the CLI did not recognize
`--write-manifest-check`.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py -q
```

Result: `9 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py tests\test_production_memory_operator_loop_manifest_check.py tests\test_production_memory_operator_manifest_check.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `16 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_loop.py apps\cli\production_memory_operator_command.py tests\test_production_memory_operator_loop_manifest_check.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed.

CLI smoke without `--write-manifest-check` did not write
`operator_manifest_check/operator_manifest_check.json`.

CLI smoke with `--write-manifest-check` wrote the report and printed
`Operator manifest check: passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `797 passed`.

## Line Counts

Measured by PowerShell `Get-Content` item count:

- `agentflow/memory/production_operator_loop.py`: 242 lines
- `apps/cli/production_memory_operator_command.py`: 153 lines
- `tests/test_production_memory_operator_loop.py`: 270 lines
- `tests/test_production_memory_operator_loop_manifest_check.py`: 56 lines

## Remaining Risks

- The report is a machine consistency check only. It does not prove human
  acceptance, business validation, provider success, or durable Memory OS
  behavior.
