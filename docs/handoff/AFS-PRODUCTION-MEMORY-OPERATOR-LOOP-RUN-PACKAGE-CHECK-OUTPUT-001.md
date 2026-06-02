# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-RUN-PACKAGE-CHECK-OUTPUT-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-run-package-check-output-001`.

## Scope

Let `production-memory-loop-run-operator-no-provider` optionally write the
operator run package check in the same unattended no-provider run that writes
the final operator run package.

This follows:

- `AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-001`
- `AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-001`
- `AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-WEB-001`

The goal is to reduce the next operator's manual startup steps without changing
the evidence boundary.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `apps/cli/production_memory_operator_command.py`
- `tests/test_production_memory_operator_run_package_check.py`
- `docs/architecture/production_memory_architecture.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Command

```powershell
production-memory-loop-run-operator-no-provider `
  examples/agentflow/production_memory_loop.example.json `
  --generated-at <iso-timestamp> `
  --source-kb-status restructuring_or_unknown `
  --draft-next-pass-result `
  --write-run-package `
  --write-run-package-check `
  --output <dir>
```

`--write-run-package-check` requires `--write-run-package`.

The command writes:

```text
operator_manifest_check/operator_manifest_check.json
operator_handoff/operator_handoff_packet.json
operator_handoff/operator_handoff_packet.md
operator_run_package/operator_run_package.json
operator_run_package/operator_run_package.md
operator_run_package_check/operator_run_package_check.json
```

## Behavior

- The writer first writes the full operator-loop artifact chain and manifest.
- `--write-run-package` still writes manifest check, handoff packet, and final
  run package.
- `--write-run-package-check` runs the existing package check against the
  written `operator_run_package/operator_run_package.json`.
- The check report is written under `operator_run_package_check/`.
- `result["operator_run_package_check"]` is populated for callers.
- CLI stdout reports `Operator run package check: passed` when the check passes.
- If the package check fails, the CLI exits non-zero.

## Boundaries

- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution.
- No ref following beyond package item existence/type checks.
- No next-pass execution.
- No automatic memory promotion.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification So Far

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Initial result: `2 failed, 4 passed` because
`write_production_memory_operator_loop_run()` did not accept
`write_run_package_check` and the CLI did not recognize
`--write-run-package-check`.

Green test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Result: `6 passed`.

Focused regression:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py tests\test_production_memory_operator_run_package.py tests\test_production_memory_operator_loop_manifest_check.py tests\test_production_memory_operator_handoff_packet.py tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_loop.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py -q
```

Result: `60 passed`.

Py compile:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_loop.py apps\cli\production_memory_operator_command.py tests\test_production_memory_operator_run_package_check.py
```

Result: passed.

CLI help:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider --help
```

Result: help lists `--write-run-package-check`.

CLI smoke:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples\agentflow\production_memory_loop.example.json --generated-at 2026-06-02T22:15:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --write-run-package-check --output data/processed/runs/production_memory_loop/operator_loop_run_package_check_output_smoke
```

Result: wrote ignored runtime artifacts and printed:

```text
Operator run package: ready
Operator run package check: passed
Provider calls: not started
Writes Company KB: false
```

Generated check summary:

```json
{"kind":"agentflow_production_memory_operator_run_package_check","check_status":"passed","ready_for_handoff":true,"checked_item_count":18,"missing_refs":0,"failed_controls":0,"provider_calls_started":false,"writes_company_kb":false}
```

`git check-ignore` confirmed the smoke check report is ignored by
`data/processed/*`.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `825 passed`.

```powershell
git diff --check
```

Result: passed with CRLF normalization warnings only.

```powershell
git diff --cached --check
```

Result: passed.

Staged added-diff sensitive scan result: clean.

## Line Counts

- `agentflow/memory/production_operator_loop.py`: 281 lines
- `apps/cli/production_memory_operator_command.py`: 181 lines
- `tests/test_production_memory_operator_run_package_check.py`: 155 lines

## Remaining Risks

- This check confirms local package consistency only. It is not human
  acceptance, business validation, provider success, durable Memory OS
  behavior, or Company KB promotion.
- Generated smoke artifacts must remain ignored under `data/processed/`.
