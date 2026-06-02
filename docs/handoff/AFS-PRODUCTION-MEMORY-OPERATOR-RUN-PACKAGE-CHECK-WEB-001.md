# AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-WEB-001

Status: verified locally on
`codex/afs-production-memory-operator-run-package-check-web-001`.

## Scope

Render selected `agentflow_production_memory_operator_run_package_check`
artifacts in the read-only generic Web memory workbench.

This is the Web counterpart of
`AFS-PRODUCTION-MEMORY-OPERATOR-RUN-PACKAGE-CHECK-001`: the next operator can
select a local `operator_run_package_check.json` report and inspect whether
the final run package is ready for handoff.

## Implementation Files

- `apps/web/memory-workbench-production-operator-run-package-check.js`
- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_web_static_production_memory_operator_run_package_check.py`
- `docs/architecture/production_memory_architecture.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior

- Recognizes `operator_run_package_check.json` and
  `agentflow_production_memory_operator_run_package_check`.
- Renders a read-only canvas with:
  - package-check status;
  - checked package items;
  - missing, mismatched, unsafe, and blocked refs;
  - failed controls;
  - no-provider controls;
  - non-claim boundaries;
  - next-operator handoff readiness.
- Adds inspector facts for check status, package status, ready-for-handoff,
  checked item count, ref blockers, failed controls, provider state,
  durable-memory write state, and Company KB write state.

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

## Verification So Far

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package_check.py -q
```

Result before implementation: failed because the check report source role was
still `unclassified` and no dedicated Web view existed.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package_check.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_run_package_check.py tests\test_web_static_production_memory_operator_run_package.py tests\test_web_static_production_memory_operator_manifest_check.py tests\test_web_static_artifact_workspace.py tests\test_web_static_artifact_boundaries.py tests\test_production_memory_operator_run_package_check.py tests\test_contract_examples.py -q
```

Result: `43 passed`.

Expanded Web static suite:

```powershell
$files = (Get-ChildItem -Path tests -Filter 'test_web_static*.py' | Sort-Object Name).FullName
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest @files -q
```

Result: `50 passed`.

JS syntax:

```powershell
node --check apps\web\memory-workbench-production-operator-run-package-check.js
node --check apps\web\memory-workbench-controller.js
node --check apps\web\memory-workbench-inspector.js
node --check apps\web\memory-workbench-production-inspector-facts.js
node --check apps\web\artifact-contracts.js
```

Result: passed.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `823 passed`.

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

Measured by PowerShell physical line counts:

- `apps/web/memory-workbench-production-operator-run-package-check.js`: 155
  lines
- `tests/test_web_static_production_memory_operator_run_package_check.py`: 119
  lines
- `apps/web/memory-workbench-controller.js`: 79 lines
- `apps/web/memory-workbench-inspector.js`: 236 lines
- `apps/web/memory-workbench-production-inspector-facts.js`: 190 lines
- `apps/web/artifact-contracts.js`: 101 lines

## Remaining Risks

- Browser-level smoke has not been run yet in this slice.
- The Web view is machine-verified structure/runtime evidence only, not human
  acceptance, business validation, provider success, durable Memory OS
  behavior, or Company KB promotion.
