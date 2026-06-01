# AFS-LOULAN-WEB-ASSET-HEALTH-DIRECT-001

## Scope

Recognize the Loulan `asset_registry_health_report.json` file as a read-only
Memory Workbench selected-file artifact.

## What Changed

- Added the `loulan_asset_registry_health_report` contract alias for
  `asset_registry_health_report.json`.
- Extended the Loulan registry inspector so the health report shares the same
  asset-health fact surface as the full registry.
- Added machine-readable Loulan health evidence at
  `D:\Projects\LoulanSceneAssets\reviews\asset_registry_health_report.json`.

## Real Probe

Input:

```text
D:\Projects\LoulanSceneAssets\reviews\asset_registry_health_report.json
```

Observed selected-file state:

- Artifact type: `loulan_asset_registry_health_report`
- Artifact class: `known_contract`
- Source role: `Loulan asset registry health report`
- Memory bundle count: `1`
- Status: `blocked_pending_human_review`
- Total assets: `86`
- Eligible refs: `3`
- Blocked refs: `83`
- Missing sha256: `0`
- Missing refs: `0`
- Source quality issues: `0`
- Provider calls started: `false`
- Writes long-term memory: `false`

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_asset_registry.py -q
```

Result: `2 passed`.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No package regeneration required for direct file review.
- No B01 decision apply.
- No context projection.
- No human acceptance recorded.
- No durable Memory write.
