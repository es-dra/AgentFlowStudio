# AFS-PRODUCTION-MEMORY-OPERATOR-MANIFEST-CHECK-WEB-001

Status: verified locally on
`codex/afs-production-memory-operator-manifest-check-web-001`.

## Scope

Render selected `agentflow_production_memory_operator_manifest_check` reports
in the existing read-only generic Web memory workbench.

This complements the no-provider operator-loop manifest check writer. It gives
operators a static Web canvas for the check report without following checked
refs or executing any workflow from the browser.

## Implementation Files

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `apps/web/memory-workbench-production-operator-manifest-check.js`
- `tests/test_web_static_production_memory_operator_manifest_check.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Rendered Surfaces

When `operator_manifest_check.json` is selected, the Web view shows:

- manifest check status;
- checked refs count and checked artifact refs;
- missing refs, mismatched refs, unsafe refs;
- failed nodes and failed controls;
- no-provider, provider-not-started, durable-memory-write-disabled, and
  Company-KB-write-disabled controls;
- non-claim boundaries for human acceptance, business validation, durable
  memory, and Company KB writes;
- a next-pass action that is ready only when the check passed and the report
  marks `ready_for_next_pass: true`.

## Boundaries

- No provider call.
- No workflow execution from Web.
- No ref following.
- No Web scan/persistence.
- No Company KB write.
- No durable memory write.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification So Far

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_manifest_check.py -q
```

Result before implementation: failed because the selected
`operator_manifest_check.json` source role was still `unclassified` and no
dedicated Web view existed.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_manifest_check.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_manifest_check.py tests\test_web_static_production_memory_operator_loop.py tests\test_production_memory_operator_manifest_check.py tests\test_production_memory_operator_loop_manifest_check.py -q
```

Result: `12 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest (Get-ChildItem tests -File -Filter 'test_web*.py') -q
```

Result: `91 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `799 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: passed with CRLF normalization warnings only.

High-risk added-diff/new-file sensitive scan was clean. A broad keyword scan
also found existing policy text in project records and the intentional
`document.cookie` forbidden-string assertion in the new static boundary test;
no secret value was found.

## Line Counts

Measured by PowerShell LINQ physical line counts:

- `apps/web/memory-workbench-production-operator-manifest-check.js`: 160 lines
- `tests/test_web_static_production_memory_operator_manifest_check.py`: 125 lines
- `apps/web/artifact-workspace.js`: 294 lines
- `apps/web/memory-workbench-inspector.js`: 241 lines
- `apps/web/memory-workbench-production-inspector-facts.js`: 166 lines

## Remaining Risks

- Browser-level smoke was not run because Browser control tools were not
  exposed in this turn.
- This is a static machine-rendering check, not human acceptance, business
  validation, provider success, or durable Memory OS behavior.
