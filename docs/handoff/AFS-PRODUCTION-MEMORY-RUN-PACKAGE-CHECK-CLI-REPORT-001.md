# AFS-PRODUCTION-MEMORY-RUN-PACKAGE-CHECK-CLI-REPORT-001

Status: verified locally on
`codex/afs-production-memory-run-package-check-cli-report-001`.

## Scope

Let the standalone operator run package check CLI write an optional Markdown
report from an explicit `operator_run_package.json`.

This follows `AFS-PRODUCTION-MEMORY-RUN-PACKAGE-CHECK-REPORT-001`, which added
the shared Markdown renderer and let the operator-loop writer emit a Markdown
check report.

## Implementation Files

- `apps/cli/production_memory_operator_run_package_check_command.py`
- `tests/test_production_memory_operator_run_package_check.py`
- `docs/architecture/production_memory_architecture.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-check-operator-run-package `
  <operator_run_package.json> `
  --output <operator_run_package_check.json> `
  --markdown-output <operator_run_package_check.md>
```

## Behavior

- `--output` remains the optional JSON report path.
- `--markdown-output` writes the operator-readable Markdown report.
- The command still reads one explicit package JSON and does not scan a
  directory.
- The command exits non-zero when the package check fails.

## Boundaries

- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution.
- No automatic memory promotion.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.
- No provider success claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Initial result: one failure because `--markdown-output` was not recognized by
the CLI.

Green focused test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py -q
```

Result: `8 passed`.

Py compile:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile apps\cli\production_memory_operator_run_package_check_command.py tests\test_production_memory_operator_run_package_check.py
```

Result: passed.

Focused regression:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package_check.py tests\test_production_memory_operator_run_package.py tests\test_production_memory_operator_loop_manifest_check.py tests\test_production_memory_operator_handoff_packet.py tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_loop.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py -q
```

Result: `62 passed`.

CLI help:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-check-operator-run-package --help
```

Result: passed and lists `--markdown-output`.

CLI smoke:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-check-operator-run-package <operator_run_package.json> --output <operator_run_package_check.json> --markdown-output <operator_run_package_check.md>
```

Result: wrote ignored runtime artifacts including:

```text
operator_run_package_check/operator_run_package_check.json
operator_run_package_check/operator_run_package_check.md
```

Generated check summary:

```json
{"check_status":"passed","ready_for_handoff":true,"checked_item_count":18,"missing_refs":0,"failed_controls":0,"provider_calls_started":false,"writes_company_kb":false,"markdown_exists":true,"markdown_has_status":true,"markdown_has_non_claim":true}
```

`git check-ignore` confirmed the Markdown smoke artifact is ignored by
`data/processed/*`.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `827 passed`.

Diff check:

```powershell
git diff --check
```

Result: passed with CRLF normalization warnings only.

Sensitive scan:

Result: clean. Added-diff and new-file sensitive scans produced no hits.

## Line Counts

- `apps/cli/production_memory_operator_run_package_check_command.py`: 74 lines
- `tests/test_production_memory_operator_run_package_check.py`: 242 lines
- `agentflow/memory/production_operator_run_package_check_render.py`: 115 lines

## Remaining Verification

- None before local commit. Staged diff check passed, and staged added-diff
  sensitive scan was clean.

## Remaining Risks

- The Markdown report is a readability surface only. It is not human
  acceptance, business validation, provider success, durable Memory OS
  behavior, or Company KB promotion.
- Generated smoke artifacts must remain ignored under `data/processed/`.
