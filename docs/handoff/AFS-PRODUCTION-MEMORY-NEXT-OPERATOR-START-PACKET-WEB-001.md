# AFS-PRODUCTION-MEMORY-NEXT-OPERATOR-START-PACKET-WEB-001

Status: verified locally on
`codex/afs-production-memory-next-operator-start-packet-web-001`.

## Scope

Render selected `agentflow_production_memory_next_operator_start_packet`
artifacts in the read-only generic Web memory workbench.

This is the Web counterpart of
`AFS-PRODUCTION-MEMORY-NEXT-OPERATOR-START-PACKET-001`: an operator can select
a local `next_operator_start_packet.json` and inspect machine startup
readiness before beginning the recorded next operator action.

## Implementation Files

- `apps/web/memory-workbench-production-next-operator-start.js`
- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_web_static_production_memory_next_operator_start_packet.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior

- Recognizes `next_operator_start_packet.json` and
  `agentflow_production_memory_next_operator_start_packet`.
- Renders a read-only canvas with:
  - start packet status;
  - checked package items;
  - blocked items and failed controls;
  - next operator action;
  - no-provider controls;
  - Company KB and durable-memory write-disabled boundaries;
  - non-claim boundaries.
- Adds inspector facts for start packet status, readiness, checked item count,
  next operator action, package check status, provider state, durable-memory
  write state, and Company KB write state.

## Boundaries

- Selected local JSON only.
- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution from Web.
- No automatic ref following.
- No Web scan or persistence.
- No project-specific inspector behavior.
- No human acceptance claim.
- No business validation claim.
- No provider success claim.
- No memory promotion claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_next_operator_start_packet.py -q
```

Result before implementation: failed because the selected start packet source
role was `unclassified` and no dedicated Web view existed.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_next_operator_start_packet.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_next_operator_start_packet.py tests\test_production_memory_next_operator_start_packet.py tests\test_web_static_production_memory_operator_run_package_check.py tests\test_web_static_production_memory_operator_run_package.py tests\test_cli_command_registry_boundaries.py -q
```

Result: `15 passed`.

Expanded Web/static memory suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests -k "web_static or web_memory" -q
```

Result: `81 passed, 797 deselected`.

JS syntax:

```powershell
node --check apps\web\artifact-contracts.js
node --check apps\web\artifact-workspace.js
node --check apps\web\memory-workbench-controller.js
node --check apps\web\memory-workbench-inspector.js
node --check apps\web\memory-workbench-production-inspector-facts.js
node --check apps\web\memory-workbench-production-next-operator-start.js
```

Result: passed.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `878 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0 with CRLF normalization warnings only.

## Remaining Risks

- Browser-level smoke was not run because Browser control tools were not
  exposed in this thread.
- This Web view is machine-verified structure/runtime evidence only. It is not
  human acceptance, business validation, provider success, durable memory,
  Company KB promotion, or automatic memory promotion.
