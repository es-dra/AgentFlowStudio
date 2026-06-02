# AFS-PRODUCTION-MEMORY-OPERATOR-READINESS-COCKPIT-001

Status: verified locally on
`codex/afs-production-memory-operator-readiness-cockpit-001`.

## Scope

Add a read-only operator readiness cockpit for selected production-memory
operator-loop manifests that already contain a ready next-operator start
packet.

This slice improves the top Memory Workbench status and summary layer. It does
not add directory scanning, browser persistence, workflow execution, provider
execution, or automatic ref following.

## Implementation Files

- `apps/web/memory-workbench-demo-checklist.js`
- `apps/web/memory-workbench-demo-summary.js`
- `apps/web/memory-workbench-studio-render.js`
- `tests/test_web_static_production_memory_operator_readiness_cockpit.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior

- Detects selected `agentflow_production_memory_operator_loop_run` views that
  include `next_operator_start_packet`.
- Replaces demo rehearsal semantics with operator start semantics:
  - `Can start`;
  - `Start blockers`;
  - `Do not claim`.
- Builds an `Operator readiness checklist` with:
  - source loaded;
  - operator loop ready;
  - output artifacts visible;
  - post-check artifacts visible;
  - start packet ready;
  - provider/write boundaries disabled;
  - non-claim boundaries visible.
- Builds an `Operator Readiness Summary` with start packet, readiness controls,
  and claim-boundary cards.
- Keeps the prior demo checklist behavior for non-operator-readiness views.

## Boundaries

- Selected local JSON only.
- No provider call.
- No Company KB write.
- No durable memory write.
- No workflow execution from Web.
- No directory scan.
- No browser persistence.
- No automatic ref following.
- No project-specific behavior.
- No human acceptance claim.
- No business validation claim.
- No provider success claim.
- No memory promotion claim.

## Verification

Red test:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_readiness_cockpit.py -q
```

Result before implementation: failed because the selected operator-loop
manifest still built `Demo-ready checklist`.

Green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_readiness_cockpit.py -q
```

Result: `1 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_readiness_cockpit.py tests\test_web_static_production_memory_operator_loop.py tests\test_web_memory_canvas_static.py tests\test_web_memory_static_structure.py tests\test_web_static_production_memory_next_operator_start_packet.py -q
```

Result: `15 passed`.

JS syntax:

```powershell
node --check apps\web\memory-workbench-demo-checklist.js
node --check apps\web\memory-workbench-demo-summary.js
node --check apps\web\memory-workbench-studio-render.js
```

Result: passed.

Expanded Web/static memory suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests -k "web_static or web_memory" -q
```

Result: `83 passed, 799 deselected`.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `882 passed` on Python 3.12.12.

Diff and sensitive scans:

```powershell
git diff --check
```

Result: exit 0 with CRLF normalization warnings only.

Added-line sensitive scan and project-specific term scan were clean. The Web
forbidden-behavior scan only matched documented `No directory scan` boundary
text in this handoff.

## Remaining Risks

- Browser-level smoke was not run in this slice; static Web tests verified the
  selected-file data model and rendered status payload.
- This readiness cockpit is machine-verified structure/runtime evidence only.
  It is not human acceptance, business validation, provider success, durable
  memory, Company KB promotion, or automatic memory promotion.
