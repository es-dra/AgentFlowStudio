# AFS-LOULAN-WEB-ASSET-REGISTRY-DIRECT-001 - Direct Loulan Asset Registry Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected Loulan
`asset_registry.json` file as a read-only memory-review artifact.

## Goal

Close this no-call asset-governance review path:

```text
Loulan unified asset registry
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show registry health and promotion boundaries
without requiring a regenerated Loulan memory package.

## Non-goals

- Do not mutate the Loulan registry.
- Do not promote candidate assets.
- Do not write durable Memory.
- Do not call providers or generate media.
- Do not copy media or scan local directories.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified no-call Web review surface.
Subagent needed: no
Close condition: Direct Loulan asset registries are recognized as known memory
artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-registry-inspector.js`
- `tests/test_web_static_loulan_asset_registry.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_unified_asset_registry` is recognized from both `artifact_type`
      and `asset_registry.json`.
- [x] The direct registry participates in `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows total assets, type counts, status counts, missing hash,
      missing refs, and source-quality issue counts.
- [x] Inspector keeps provider-call and durable-memory flags false.
- [x] Main inspector stays under the project file-size target by delegating
      registry facts to a focused module.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_asset_registry.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_asset_registry.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-ASSET-REGISTRY-DIRECT-001.md
```
