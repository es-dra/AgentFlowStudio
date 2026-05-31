# AFS-LOULAN-WEB-B01-APPLY-PLAN-DIRECT-001

Status: Direct selected-file recognition for the Loulan B01 decision apply plan
draft implemented.

## Scope

The Web Artifact Workspace now recognizes:

```json
{
  "artifact_type": "loulan_b01_decision_apply_plan_draft"
}
```

and the filename alias:

```text
b01_decision_apply_plan_draft.json
```

as a known memory-review artifact.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan B01 decision apply plan draft` |
| Memory source status | `Selected files` |
| Artifact inspector | shows B01 block, preconditions, planned mutations, blocked mutations, and no-apply/no-provider/no-memory boundaries |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not fill or apply decisions, mutate project manifests, promote
  keyframes, run context projection, call providers, copy media, persist browser
  edits, or write durable Memory.
- The real plan remains `blocked_until_validation_ready` because the five local
  B01 shot decisions are still pending.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/manifests/b01_decision_apply_plan_draft.json
```

Observed facts:

```json
{
  "artifactType": "loulan_b01_decision_apply_plan_draft",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan B01 decision apply plan draft",
  "memoryBundleCount": 1,
  "sourceStatus": "Selected files",
  "status": "blocked_until_validation_ready",
  "block_id": "B01",
  "preconditions": "3",
  "planned_mutations": "5",
  "blocked_mutations": "5",
  "dry_run_plan_only": "true",
  "applies_status_changes": "false",
  "provider_calls_started": "false",
  "writes_long_term_memory": "false"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py -q
# 3 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
# 25 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 750 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 apply blocked until the operator fills and validates all five local
  B01 shot decisions.
- Remaining direct selected-file candidates include Loulan request planning
  manifests such as `image2_requests.json` and `kling_i2v_requests.json`.
