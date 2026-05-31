# AFS-LOULAN-ASSET-REGISTRY-001 - Loulan Asset Registry Gate

## Task

Let `loulan-memory-package` consume an optional unified Loulan asset registry
while preserving the legacy character manifest path.

## Goal

Support a single asset inventory surface for characters, scenes, props, VFX,
keyframes, feedback, and provider run evidence. Only `approved_anchor` and
`promoted_reusable` assets can enter the next context draft.

## Non-goals

- Do not restructure `D:\Projects\LoulanSceneAssets`.
- Do not scan arbitrary directories.
- Do not call providers or read provider credentials.
- Do not write Company knowledge or durable Memory runtime.

## Owner Role

Memory / Evidence Steward + QA Reviewer

## Acceptance Criteria

- [x] Optional `manifests/asset_registry.json` is detected.
- [x] `asset_inventory` reports type/status counts without absolute paths.
- [x] Registry mode blocks `candidate`, `route_failed`, `source_reference`,
      `needs_repair`, `superseded`, and `rejected` assets.
- [x] `blocked_refs_by_reason` preserves route-failure evidence.
- [x] API workbench and human review pack can read registry-backed assets.
- [x] Legacy `character_assets.json` behavior remains covered.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_loulan_memory_package_registry.py tests\test_loulan_api_workbench.py tests\test_loulan_human_review_pack.py -q
```

## Remote Provider Policy

No remote provider is authorized in this task.
