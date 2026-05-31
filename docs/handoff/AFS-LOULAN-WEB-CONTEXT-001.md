# AFS-LOULAN-WEB-CONTEXT-001

Status: Web Memory Workbench read-only Loulan decision/context rendering
implemented.

## What Changed

- `artifact-workspace.js` now normalizes Loulan decision templates and context
  bundle projections.
- `memory-workbench-loulan-package.js` adds decision-template and
  context-bundle cards, protocol controls, next-pass details, and timeline
  nodes.
- `memory-workbench-inspector.js` adds labels and facts for both artifact
  types.
- Added `tests/test_web_memory_loulan_decision_context_static.py`.

## Boundary

The Web UI only renders selected files. It does not persist browser decisions,
write project files, call providers, follow refs, or promote memory.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_loulan_decision_context_static.py -q
# 4 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain
# 704 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed
```

Edge headless loaded `http://127.0.0.1:8769/#memory` from a temporary local
static server. The DOM contained the Memory Workbench marker and no module or
JavaScript error markers were detected.

## Next Work

- Use a browser pass to inspect layout after the broader verification suite.
- When real human decisions exist, load the resulting projection beside the
  package and review pack.
