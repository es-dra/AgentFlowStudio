# AFS-LOULAN-WEB-ASSET-REGISTRY-DIRECT-001

Status: Direct selected-file recognition for the Loulan unified asset registry
implemented.

## Scope

The Web Artifact Workspace now recognizes:

```json
{
  "artifact_type": "loulan_unified_asset_registry"
}
```

and the filename alias:

```text
asset_registry.json
```

as a known memory-review artifact.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan unified asset registry` |
| Memory source status | `Selected files` |
| Artifact inspector | shows total assets, type counts, status counts, missing hash/ref counts, source-quality issue count, and no-call boundary flags |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not mutate the registry, promote candidate assets, copy media, scan
  local directories, call providers, or write durable Memory.
- The registry inspector reports blocked status when blocked asset statuses are
  present; it does not convert candidates into reusable context.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/manifests/asset_registry.json
```

Observed facts:

```json
{
  "artifactType": "loulan_unified_asset_registry",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan unified asset registry",
  "memoryBundleCount": 1,
  "sourceStatus": "Selected files",
  "status": "blocked",
  "total_assets": "85",
  "type_counts": "character: 26, feedback: 20, keyframe: 5, prop: 3, run_evidence: 28, scene: 1, vfx: 2",
  "status_counts": "approved_anchor: 3, candidate: 60, needs_repair: 14, route_failed: 4, superseded: 4",
  "missing_sha256": "1",
  "missing_refs": "7",
  "source_quality_issues": "10",
  "provider_calls_started": "false",
  "writes_long_term_memory": "false"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_asset_registry.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_asset_registry.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py tests\test_loulan_memory_package.py -q
# 19 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 748 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 context and generation blocked until the operator fills the five
  local B01 shot decisions.
- If operators need to inspect generation request planning directly, add a
  separate no-call selected-file projection for Loulan request manifests.
