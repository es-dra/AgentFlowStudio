# AFS-LOULAN-WEB-PROJECT-MANIFESTS-DIRECT-001

Status: Direct selected-file recognition for Loulan project manifests
implemented.

## Scope

The Web Artifact Workspace now recognizes these filename aliases:

```text
character_assets.json
character_asset_versions.json
prop_asset_versions.json
shot_list.json
```

as known read-only memory-review artifacts:

```text
loulan_character_asset_manifest
loulan_character_asset_versions
loulan_prop_asset_versions
loulan_shot_list_manifest
```

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | Each direct project manifest is `known_contract`. |
| Source role | The selected file gets a stable Loulan source role. |
| Memory source status | The Workbench reports `Selected files`. |
| Artifact inspector | Character/prop manifests show asset counts, characters or props, status counts, and no-memory boundary; shot lists show shot count, blocks, quality status counts, target formats, and scenes. |

## Boundary Evidence

- These are read-only selected-file projections.
- They do not scan directories, call providers, generate media, mutate Loulan
  manifests, execute context projection, persist browser edits, or write
  durable Memory.
- Candidate, repair, route-failed, and pending shot facts remain review
  evidence. They are not approval, acceptance, promotion, or reusable memory.

## Real Local Probe

```powershell
node --input-type=module
# read all *.json files under D:/Projects/LoulanSceneAssets/manifests
```

Observed all 12 top-level Loulan manifest JSON files as selected known memory
artifacts:

```json
[
  "afs_b01_decision_crosswalk.json",
  "afs_b01_feedback_loop_gate.json",
  "asset_registry.json",
  "b01_decision_apply_plan_draft.json",
  "b01_human_review_decision_template.json",
  "character_asset_versions.json",
  "character_assets.json",
  "image2_requests.json",
  "kling_i2v_requests.json",
  "next_context_bundle_draft.json",
  "prop_asset_versions.json",
  "shot_list.json"
]
```

Each parsed as `known_contract` with `memoryBundleCount: 1`.

## B01 Gate Probe

```powershell
python tools\validate_b01_decisions.py --project-root . --decisions manifests\b01_human_review_decision_template.json
# status: blocked_pending_human_review
# pending: 5

python tools\apply_b01_decisions.py --project-root . --decisions manifests\b01_human_review_decision_template.json
# status: blocked_validation_not_ready
# applied: false
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py -q
# 23 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 753 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 keyframes and request manifests blocked until human decisions are
  filled and validated.
- Use the direct project manifest inspectors as review evidence when preparing
  the next Loulan context bundle, but only approved or promoted registry assets
  may enter memory-backed context.
