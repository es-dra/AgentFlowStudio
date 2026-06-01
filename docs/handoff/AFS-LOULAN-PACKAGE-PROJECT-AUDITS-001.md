# AFS-LOULAN-PACKAGE-PROJECT-AUDITS-001

## Scope

Surface Loulan project-level audit gates in the no-call memory package and Web
Memory Workbench review path.

## What Changed

- `loulan-memory-package` now reads these optional `project_manifest.json`
  fields:
  - `manifest_reference_audit`
  - `manifest_reference_audit_report`
  - `manifest_reference_audit_status`
  - `text_encoding_audit`
  - `text_encoding_audit_report`
  - `text_encoding_audit_status`
- The package writes them under `project_audits`.
- The Markdown package report shows both audit statuses.
- Memory Workbench package review shows:
  - a `Project audits` bundle card;
  - `manifest reference audit` and `text encoding audit` protocol controls;
  - inspector facts for both audit statuses.
- Loulan package inspector facts were moved to
  `apps/web/memory-workbench-loulan-package-inspector.js` so the generic
  inspector stays below the project file-size target.

## Real Probe

Input:

```text
D:\Projects\LoulanSceneAssets
```

Output:

```text
data/processed/runs/loulan_memory_package/local_probe_package_blocked_count_sync/
```

Observed state:

- `project_audits.manifest_reference.status`: `pass`
- `project_audits.text_encoding.status`: `pass`
- Promotion gate: `blocked`
- Eligible refs: `3`
- Blocked refs: `90`
- B01 feedback loop gate: `blocked_pending_human_review`
- Provider calls: not started
- Durable Memory write: false

## Verification

```powershell
pytest tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py -q
```

Result: `6 passed`.

Additional checks:

- Full suite: `pytest -q` -> `754 passed`.
- Refresh suite: `.venv\Scripts\python.exe -B -m pytest --assert=plain -q` ->
  `763 passed`.
- Real `loulan-memory-package` probe over `D:\Projects\LoulanSceneAssets`
  passed.
- Web view probe over the real package showed `Project audits`,
  `manifest reference audit`, and `text encoding audit`.
- Output safety scan over the real package probe found no `D:\`, `C:\`,
  provider URL, token, signed URL, API key, `.mp4`, or `.mov`.
- Current Loulan registry includes additional blocked review evidence after the
  project-audit probe, so the live package now reports 90 blocked refs.
- Refresh package output parsed as 3 eligible refs, 90 blocked refs, manifest
  reference audit `pass`, text encoding audit `pass`, phase gate
  `blocked_until_b01_human_review`, no provider calls, and no durable Memory
  write.
- Modified/new code files are under 300 effective lines.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No B01 decision apply.
- No human acceptance recorded.
- No durable Memory write.
- No Company knowledge-base material copied into the repo.
