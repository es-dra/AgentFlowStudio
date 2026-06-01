# AFS-LOULAN-WEB-MANIFEST-SET-SUMMARY-001

Status: Loulan selected-manifest-set summary implemented.

## Scope

When an operator selects multiple Loulan top-level manifest JSON files without
selecting a full `agentflow_loulan_memory_package`, the Memory Workbench now
builds a Loulan project-level cockpit instead of falling back to the static
fixture view.

The summary is driven only by selected local JSON payloads:

- B01 gate/status manifests
- `asset_registry.json`
- `next_context_bundle_draft.json`
- `image2_requests.json`
- `kling_i2v_requests.json`
- character, prop, and shot-list manifests

## Web Surfaces

| Surface | Behavior |
|---|---|
| Contract type | `loulan_manifest_set` |
| Project summary | Shows selected manifest count, target block, project id, horizontal manifest review format, and no-provider route. |
| Bundle summary | Shows manifest coverage, asset registry counts, B01 pending decisions, request manifest counts, project manifest coverage, and context draft status. |
| Memory loaded | Shows eligible context refs first, then blocked refs with status-specific promotion blockers. |
| Protocol controls | Shows B01 human review status plus image/video/provider/media/durable-memory no-call boundaries. |
| Next pass | Keeps B02 blocked until B01 human review and promotion gates are satisfied. |

## Boundary Evidence

- The view reads only selected JSON files already loaded into browser memory.
- It does not scan `D:\Projects\LoulanSceneAssets`.
- It does not copy media, call Image2/Kling/providers, execute context
  projection, promote candidates, persist browser edits, or write durable
  Memory.
- `eligible_context_refs` are displayed as next-context candidates, not as
  approved human acceptance or durable memory runtime proof.

## Real Local Probe

```powershell
node --input-type=module
# read all *.json files under D:/Projects/LoulanSceneAssets/manifests
```

Observed:

```json
{
  "contract_type": "loulan_manifest_set",
  "state": "blocked_until_b01_human_review",
  "project": "9 selected Loulan manifests; target B02; loulan_scene_assets",
  "asset_registry": "87 assets; 3 eligible, 84 blocked",
  "b01": "5 pending B01 decisions",
  "requests": "38 Image2 requests; 38 Kling I2V requests",
  "project_manifests": "38 shots; character assets selected: true; prop assets selected: true",
  "next_pass": "B02 blocked: 3 eligible refs, 84 blocked refs",
  "provider_calls_started": "false",
  "new_media_generated": "false",
  "durable_memory_write": "false",
  "artifact_inspector_count": 9
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_manifest_set_summary.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py -q
# 24 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 754 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep real generation blocked until B01 human decisions and provider gates are
  explicitly resolved.
- Use the manifest-set summary as a fast Web review cockpit for Loulan asset
  governance before preparing later B02 context or request previews.
