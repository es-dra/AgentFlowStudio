# AFS-PRODUCTION-MEMORY-NEXT-OPERATOR-START-PACKET-001

Status: verified locally on
`codex/afs-production-memory-next-operator-start-packet-001`.

## Scope

Generate a no-provider next-operator start packet from the final checked
operator run package.

This follows:

- `AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-001`
- `AFS-PRODUCTION-MEMORY-RUN-PACKAGE-CHECK-REPORT-001`
- `AFS-PRODUCTION-MEMORY-RUN-PACKAGE-CHECK-ACCEPTANCE-OVERLAY-001`

The start packet is a machine-readable and operator-readable launch artifact
for the next operator or agent after the final run package check has passed.
It does not execute the next pass.

## Implementation Files

- `agentflow/memory/production_operator_start_packet.py`
- `agentflow/memory/production_operator_start_packet_render.py`
- `apps/cli/production_memory_next_operator_start_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_next_operator_start_packet.py`
- `tests/test_cli_command_registry_boundaries.py`

## Behavior

`production-memory-loop-next-operator-start-packet` reads an explicit
`operator_run_package_check.json`. By default it uses the artifact root
recorded by the check to load:

- `operator_run_package/operator_run_package.json`
- `operator_handoff/operator_handoff_packet.json`

The command writes:

- `next_operator_start_packet.json`
- `next_operator_start_packet.md`

The builder refuses to create a packet unless:

- the run package check passed;
- `ready_for_handoff` is true;
- the run package is ready;
- the handoff packet is ready;
- package, handoff, and check source loop IDs match;
- package, handoff, and check next operator actions match;
- provider calls are not started;
- durable memory and Company KB writes are disabled;
- there are no missing refs, mismatched refs, unsafe refs, blocked items, or
  failed controls.

The packet preserves:

- checked package items;
- next operator action;
- operator handoff prompt;
- start requirements;
- acceptance feedback candidate promotion check summary when present;
- provider/write boundaries;
- non-claims and claim boundaries.

## Verification

Initial red result:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_next_operator_start_packet.py -q
```

The test failed because `agentflow.memory.production_operator_start_packet` did
not exist.

Green and regression results:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_next_operator_start_packet.py -q
```

Result: `6 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_next_operator_start_packet.py tests\test_production_memory_operator_run_package_check.py tests\test_production_memory_operator_run_package_check_acceptance_overlay.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `20 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed; command list includes
`production-memory-loop-next-operator-start-packet`.

CLI smoke:

```powershell
$root = 'data\processed\runs\production_memory_loop\next_operator_start_packet_smoke_20260602'
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples\agentflow\production_memory_loop.example.json --generated-at 2026-06-03T09:00:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --write-run-package-check --output "$root\operator_loop"
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-next-operator-start-packet "$root\operator_loop\operator_run_package_check\operator_run_package_check.json" --generated-at 2026-06-03T09:30:00+08:00 --output "$root\start_packet"
```

Result: start packet status `ready`; ignored runtime artifacts were written
under `data/processed/runs/production_memory_loop/next_operator_start_packet_smoke_20260602/`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `876 passed` on Python 3.12.12.

## Contract Boundaries

- No provider call was made.
- No Company KB write was made.
- No durable memory write was made.
- No next-pass execution was performed.
- No Loulan-specific behavior was added.
- Passing this packet gate is machine startup readiness only. It is not human
  acceptance, business validation, provider success, durable memory, Company KB
  promotion, or automatic memory promotion.

## Remaining Risks

- Web rendering for `agentflow_production_memory_next_operator_start_packet`
  was not added in this slice.
- Browser-level verification was not run because no Web surface changed.
- Optional gated image/video provider validation was not attempted and is not
  part of this no-provider milestone.
