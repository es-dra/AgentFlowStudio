# AFS-LOULAN-WEB-CONTEXT-DRAFT-DIRECT-001

Status: Direct selected-file recognition for the Loulan next generation context
bundle draft implemented.

## Scope

The Web Artifact Workspace now recognizes:

```json
{
  "artifact_type": "loulan_next_generation_context_bundle_draft"
}
```

and the filename alias:

```text
next_context_bundle_draft.json
```

as a known memory-review artifact.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan next context bundle draft` |
| Memory source status | `Selected files` |
| Artifact inspector | shows B02 target, eligible refs, blocked refs by status, review evidence refs, B01/provider gates, and no-call boundary flags |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not unlock B01 human review, execute context projection, preview API
  requests, promote candidate assets, copy media, scan local directories, call
  providers, or write durable Memory.
- `blocked_until_b01_human_review` remains the draft status until explicit
  operator decisions are provided.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/manifests/next_context_bundle_draft.json
```

Observed facts:

```json
{
  "artifactType": "loulan_next_generation_context_bundle_draft",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan next context bundle draft",
  "memoryBundleCount": 1,
  "sourceStatus": "Selected files",
  "status": "blocked_until_b01_human_review",
  "target_next_block": "B02",
  "eligible_context_refs": "3",
  "blocked_refs_by_status": "candidate: 60, needs_repair: 14, route_failed: 4, superseded: 4",
  "review_evidence_refs": "28",
  "b01_keyframe_human_review": "blocked",
  "provider_image_gate": "blocked_not_authorized",
  "provider_video_gate": "blocked_not_authorized",
  "provider_calls_started": "false",
  "new_media_generated": "false",
  "durable_memory_write": "false",
  "eligible_refs_match_package": "true"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_context_draft.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py tests\test_loulan_memory_package.py -q
# 20 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 749 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B02 generation blocked until the five local B01 shot decisions are
  filled and validated.
- Remaining direct selected-file candidates include Loulan request planning
  manifests such as `image2_requests.json` and `kling_i2v_requests.json`.
