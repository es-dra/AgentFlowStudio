# AFS-LOULAN-WEB-REQUEST-MANIFESTS-DIRECT-001

Status: Direct selected-file recognition for Loulan generation request
manifests implemented.

## Scope

The Web Artifact Workspace now recognizes these filename aliases:

```text
image2_requests.json
kling_i2v_requests.json
```

as known memory-review artifacts:

```json
{
  "artifact_type": "loulan_image2_request_manifest"
}
```

```json
{
  "artifact_type": "loulan_kling_i2v_request_manifest"
}
```

## Web Surfaces

| Surface | Image2 behavior | Kling I2V behavior |
|---|---|---|
| Artifact classification | `known_contract` | `known_contract` |
| Source role | `Loulan Image2 request manifest` | `Loulan Kling I2V request manifest` |
| Memory source status | `Selected files` | `Selected files` |
| Artifact inspector | shows request count, model, blocks, status counts, aspect ratio, and no-provider boundary | shows request count, model, blocks, blocked status counts, durations, and no-provider boundary |

## Boundary Evidence

- These are read-only selected-file projections.
- They do not call Image2, Kling, or any provider.
- They do not generate media, mutate request manifests, execute API preview,
  persist browser edits, or write durable Memory.
- Request counts and statuses are planning evidence, not approval or execution.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/manifests/image2_requests.json
# read D:/Projects/LoulanSceneAssets/manifests/kling_i2v_requests.json
```

Observed facts:

```json
[
  {
    "artifactType": "loulan_image2_request_manifest",
    "artifactClass": "known_contract",
    "sourceRole": "Loulan Image2 request manifest",
    "memoryBundleCount": 1,
    "sourceStatus": "Selected files",
    "status": "review ready",
    "requests": "38",
    "models": "chatgpt_image2",
    "blocks": "B01, B02, B03, B04, B05, B06, B07, B08",
    "status_counts": "horizontal_keyframe_candidate_pending_review: 5, planned: 33",
    "aspect_ratios": "16:9",
    "provider_calls_started": "false"
  },
  {
    "artifactType": "loulan_kling_i2v_request_manifest",
    "artifactClass": "known_contract",
    "sourceRole": "Loulan Kling I2V request manifest",
    "memoryBundleCount": 1,
    "sourceStatus": "Selected files",
    "status": "blocked",
    "requests": "38",
    "models": "kling-v3",
    "blocks": "B01, B02, B03, B04, B05, B06, B07, B08",
    "status_counts": "generated_from_chatgpt_image2_refined_v2_pending_human_review: 1, blocked_until_keyframe_exists: 37",
    "durations": "3, 2, 4",
    "provider_calls_started": "false"
  }
]
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_request_manifests.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
# 27 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 752 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep real generation blocked until B01 human decisions and provider gates are
  explicitly resolved.
- With `image2_requests.json` and `kling_i2v_requests.json` recognized, the
  current Loulan top-level manifests are now inspectable through selected-file
  Web review surfaces.
