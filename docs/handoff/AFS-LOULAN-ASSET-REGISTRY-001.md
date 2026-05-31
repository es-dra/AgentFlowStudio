# AFS-LOULAN-ASSET-REGISTRY-001

Status: optional Loulan unified asset registry gate implemented.

## What Changed

- Added `agentflow.memory.loulan_assets` for registry and legacy asset
  projection helpers.
- Updated `agentflow.memory.loulan_package` to emit `project_summary` and
  `asset_inventory`.
- Updated Loulan API workbench and human review pack readers to use registry
  assets when present, while keeping legacy `asset_summary` compatibility.
- Registry mode keeps `approved_anchor` and `promoted_reusable` as the only
  context-eligible statuses.
- Split registry-focused Loulan package tests into
  `tests/test_loulan_memory_package_registry.py` to keep files small.

## Boundary

This is a file-protocol projection only. It does not scan arbitrary Loulan
folders, call providers, copy media, write Company memory, or claim human
acceptance.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_loulan_memory_package_registry.py tests\test_loulan_api_workbench.py tests\test_loulan_human_review_pack.py -q
# 15 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain
# 704 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed
```

## Next Work

- Add a real Loulan `manifests/asset_registry.json` only after the asset project
  is ready for that source-of-truth file.
- Rerun `loulan-memory-package` and inspect `asset_inventory` before promotion.
