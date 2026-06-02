# AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-001

Status: verified locally on
`codex/afs-production-memory-operator-run-package-001`.

## Scope

Let `production-memory-loop-run-operator-no-provider` optionally write a final
operator run package after the manifest check and operator handoff packet.

This gives the next unattended operator one entry artifact that indexes the
full no-provider run, while preserving the existing evidence boundary:
manifest check and handoff readiness are still explicit artifacts.

## Implementation Files

- `agentflow/memory/production_operator_run_package.py`
- `agentflow/memory/production_operator_loop.py`
- `apps/cli/production_memory_operator_command.py`
- `tests/test_production_memory_operator_run_package.py`
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
  --output <dir>
```

`--write-run-package` writes:

```text
operator_manifest_check/operator_manifest_check.json
operator_handoff/operator_handoff_packet.json
operator_handoff/operator_handoff_packet.md
operator_run_package/operator_run_package.json
operator_run_package/operator_run_package.md
```

The option implicitly writes the operator manifest check and operator handoff
packet because the run package depends on both.

## Behavior

- The writer first writes the full operator-loop artifact chain and manifest.
- The manifest check runs against the written manifest path.
- The handoff packet is built from the manifest plus the check report.
- The run package is built from the manifest, manifest check, and handoff
  packet.
- The run package indexes the core manifest, check, handoff packet, handoff
  Markdown, and manifest output refs.
- The run package is not added to the manifest `output_artifacts`, avoiding a
  self-referential manifest check.
- CLI stdout reports `Operator run package: ready` when the package is ready.

## Boundaries

- No provider call.
- No Company KB write.
- No durable memory write.
- No next-pass execution.
- No automatic memory promotion.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package.py -q
```

Result before implementation: failed because
`agentflow.memory.production_operator_run_package` did not exist.

Additional red test: failed while the package still treated a mismatched
`source_operator_loop_id` in the handoff packet as ready.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package.py -q
```

Result: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_run_package.py tests\test_production_memory_operator_loop_manifest_check.py tests\test_production_memory_operator_handoff_packet.py tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_loop.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py -q
```

Result: `54 passed`.

Py compile:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_run_package.py agentflow\memory\production_operator_loop.py apps\cli\production_memory_operator_command.py tests\test_production_memory_operator_run_package.py
```

Result: passed.

CLI help:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider --help
```

Result: help lists `--write-run-package`.

CLI smoke:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T18:10:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --output data/processed/runs/production_memory_loop/operator_run_package_smoke
```

Result: wrote ignored runtime artifacts including:

```text
operator_manifest_check/operator_manifest_check.json
operator_handoff/operator_handoff_packet.json
operator_handoff/operator_handoff_packet.md
operator_run_package/operator_run_package.json
operator_run_package/operator_run_package.md
```

Smoke package fields:

```text
kind: agentflow_production_memory_operator_run_package
package_status: ready
manifest_check_status: passed
handoff_status: ready
provider_calls_started: false
writes_long_term_memory: false
writes_company_kb: false
```

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `815 passed`.

`git diff --check` passed with CRLF normalization warnings only.

High-risk added-diff and new-file sensitive scans were clean.

## Line Counts

Measured by PowerShell physical line counts:

- `agentflow/memory/production_operator_run_package.py`: 299 lines
- `agentflow/memory/production_operator_loop.py`: 280 lines
- `apps/cli/production_memory_operator_command.py`: 184 lines
- `tests/test_production_memory_operator_run_package.py`: 171 lines

## Remaining Verification

- Repeat staged diff and staged sensitive-content checks before commit.

## Remaining Risks

- The run package is an operator evidence entry point, not human acceptance,
  business validation, provider success, durable Memory OS behavior, or Company
  KB promotion.
- Generated smoke artifacts must remain ignored under `data/processed/`.
