# AFS-LOULAN-WEB-ROOT-PROJECT-MANIFEST-DIRECT-001

## Scope

Recognize the Loulan root `project_manifest.json` as a read-only Memory
Workbench selected-file artifact.

## What Changed

- Added the `loulan_root_project_manifest` contract alias for
  `project_manifest.json`.
- Reused the Loulan project-manifest inspector with a root-manifest branch.
- The inspector surfaces project-level status, audit gates, and B01/context
  blockers without reading any other file.

## Real Probe

Input:

```text
D:\Projects\LoulanSceneAssets\project_manifest.json
```

Observed selected-file state:

- Artifact type: `loulan_root_project_manifest`
- Artifact class: `known_contract`
- Source role: `Loulan root project manifest`
- Memory bundle count: `1`
- Status: `blocked_until_b01_human_review`
- Focus targets: `project`, `assets`, `review`, `next-pass`
- Facts:
  - project id: `loulan_scene_assets`
  - target format: `horizontal_16_9`
  - shots: `38`
  - current phase: `keyframe_only_horizontal_16_9`
  - claim level: `asset_registry_ready_b01_keyframes_pending_human_review`
  - manifest reference audit: `pass`
  - text encoding audit: `pass`
  - phase gate audit: `blocked_until_b01_human_review`
  - B01 validation: `blocked_pending_human_review`
  - next context: `blocked_until_b01_human_review`

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_governance_audits.py -q
```

Result: `4 passed`.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No package regeneration required for direct file review.
- No B01 decision apply.
- No context projection.
- No human acceptance recorded.
- No durable Memory write.
