# AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-WEB-001

Status: verified locally on
`codex/afs-production-memory-operator-run-package-web-001`.

## Scope

Render selected `agentflow_production_memory_operator_run_package` artifacts in
the read-only generic Web memory workbench.

This completes the Web counterpart of
`AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-001`: an operator can select the
final no-provider run package JSON and see the package status, manifest-check
status, handoff status, package items, blockers, controls, non-claim
boundaries, and next operator action.

## Implementation Files

- `apps/web/memory-workbench-production-operator-run-package.js`
- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_web_static_production_memory_operator_run_package.py`
- `docs/architecture/production_memory_architecture.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior

- Recognizes `operator_run_package.json` and
  `agentflow_production_memory_operator_run_package`.
- Adds `productionMemoryOperatorRunPackage` to the normalized workspace.
- Renders a read-only canvas with:
  - package status;
  - manifest-check status;
  - handoff status;
  - package items;
  - blocked items;
  - no-provider controls;
  - non-claim boundaries;
  - recorded next operator action.
- Adds inspector facts for package status, manifest-check status, handoff
  status, package item count, blocked item count, next operator action,
  provider state, durable-memory write state, and Company KB write state.

## Boundaries

- Selected local JSON only.
- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution from Web.
- No ref following.
- No Web scan or persistence.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package.py -q
```

Result before implementation: failed because the run package source role was
still `unclassified` and no dedicated Web view existed.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package.py tests\test_web_static_production_memory_operator_handoff_packet.py tests\test_web_static_production_memory_operator_manifest_check.py tests\test_web_static_production_memory_operator_loop.py tests\test_web_static_artifact_workspace.py tests\test_web_static_artifact_boundaries.py tests\test_production_memory_operator_run_package.py tests\test_contract_examples.py -q
```

Result: `47 passed`.

Expanded Web static suite:

```powershell
$files = (Get-ChildItem -Path tests -Filter 'test_web_static*.py' | Sort-Object Name).FullName
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest @files -q
```

Result: `48 passed`.

JS syntax:

```powershell
node --check apps\web\memory-workbench-production-operator-run-package.js
node --check apps\web\artifact-contracts.js
node --check apps\web\artifact-workspace.js
node --check apps\web\memory-workbench-controller.js
node --check apps\web\memory-workbench-inspector.js
node --check apps\web\memory-workbench-production-inspector-facts.js
```

Result: passed.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `817 passed`.

`git diff --check` passed with CRLF normalization warnings only.

High-risk added-diff and new-file sensitive scans were clean.

## Line Counts

Measured by PowerShell physical line counts:

- `apps/web/memory-workbench-production-operator-run-package.js`: 155 lines
- `tests/test_web_static_production_memory_operator_run_package.py`: 129 lines
- `apps/web/artifact-workspace.js`: 298 lines
- `apps/web/memory-workbench-controller.js`: 81 lines
- `apps/web/memory-workbench-inspector.js`: 251 lines
- `apps/web/memory-workbench-production-inspector-facts.js`: 193 lines
- `apps/web/artifact-contracts.js`: 103 lines

## Remaining Verification

- Staged diff and staged sensitive-content checks before commit.

## Remaining Risks

- Browser-level smoke has not been run yet in this slice.
- The Web view is machine-verified structure/runtime evidence only, not human
  acceptance, business validation, provider success, durable Memory OS
  behavior, or Company KB promotion.
