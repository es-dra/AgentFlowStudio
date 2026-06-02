# AFS-PRODUCTION-MEMORY-OPERATOR-MANIFEST-CHECK-001

Status: verified locally on
`codex/afs-production-memory-operator-manifest-check-001`.

## Scope

Add a read-only consistency check for
`agentflow_production_memory_operator_loop_run` manifests.

The check verifies the artifact refs emitted by the no-provider operator-loop
command so an unattended run can distinguish "manifest exists" from "manifest
is still traceable to its generated JSON/Markdown artifacts."

## Implementation Files

- `agentflow/memory/production_operator_manifest_check.py`
- `apps/cli/production_memory_operator_manifest_check_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_operator_manifest_check.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior Boundary

The command is read-only except for an optional explicit report path:

```powershell
production-memory-loop-check-operator-manifest <production_memory_operator_loop_run.json> --output <report.json>
```

It does not execute a workflow, follow refs from Web, call providers, write
Company KB, write durable memory, or promote feedback/candidates.

## Checks

- manifest kind is `agentflow_production_memory_operator_loop_run`
- required output artifact refs exist under the manifest directory or explicit
  `--artifact-root`
- JSON artifact `kind` or `artifact_type` matches the manifest-listed
  artifact type
- markdown reports are existence-checked only
- absolute and parent-traversal refs are unsafe
- node statuses `blocked`, `failed`, `missing`, `error`, and `unknown` fail
  the check
- controls must all be `passed`
- provider calls, long-term memory writes, and Company KB writes must remain
  disabled

The report is a machine check artifact, not human acceptance or business
validation.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_manifest_check.py -q
```

Result before implementation: failed during collection because
`agentflow.memory.production_operator_manifest_check` did not exist.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_manifest_check.py -q
```

Result: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_loop.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `14 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow\memory\production_operator_manifest_check.py apps\cli\production_memory_operator_manifest_check_command.py apps\cli\command_registry.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed and lists
`production-memory-loop-check-operator-manifest`.

CLI smoke wrote ignored artifacts under
`data/processed/runs/production_memory_loop/operator_manifest_check` and the
check report passed with 15 checked refs, 0 missing refs, 0 mismatched refs,
0 failed nodes, and 0 failed controls.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `795 passed`.

## Remaining Risks

- This slice checks manifest/ref consistency only. It does not prove human
  acceptance, business validation, provider success, or durable Memory OS
  behavior.
