# AFS-LOULAN-WEB-PROJECT-MANIFESTS-DIRECT-001 - Direct Loulan Project Manifest Recognition

## Task

Let the Web Artifact Workspace recognize directly selected Loulan project
manifests as read-only memory-review artifacts:

- `character_assets.json`
- `character_asset_versions.json`
- `prop_asset_versions.json`
- `shot_list.json`

## Goal

Close this no-call project-asset review path:

```text
Loulan project manifest
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show project inventory status without scanning the
Loulan asset directory, promoting candidates, or starting generation.

## Non-goals

- Do not call Image2, Kling, or any provider.
- Do not generate images or videos.
- Do not mutate project manifests, registries, shot lists, or generated media
  records.
- Do not execute context projection or API preview.
- Do not infer approval from candidates, repair targets, or route failures.
- Do not persist browser edits or durable Memory.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified no-call Web review surface.
Subagent needed: no
Close condition: Direct project manifests are recognized as known memory
artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-project-manifest-inspector.js`
- `tests/test_web_static_loulan_project_manifests.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `character_assets.json` is recognized as
      `loulan_character_asset_manifest`.
- [x] `character_asset_versions.json` is recognized as
      `loulan_character_asset_versions`.
- [x] `prop_asset_versions.json` is recognized as
      `loulan_prop_asset_versions`.
- [x] `shot_list.json` is recognized as
      `loulan_shot_list_manifest`.
- [x] All four direct manifests participate in `workspace.memoryBundle`.
- [x] Inspector shows asset, character, prop, status, shot, block, quality
      status, and target-format facts where applicable.
- [x] All 12 top-level Loulan manifest JSON files under
      `D:\Projects\LoulanSceneAssets\manifests` are recognized as selected
      known memory artifacts.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-PROJECT-MANIFESTS-DIRECT-001.md
```
