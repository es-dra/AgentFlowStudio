# AFS-LOULAN-WEB-B01-CROSSWALK-DIRECT-001

Status: Direct selected-file recognition for the Loulan B01 decision crosswalk
implemented.

## Scope

The Web Artifact Workspace now recognizes:

```json
{
  "artifact_type": "loulan_afs_b01_decision_crosswalk"
}
```

and the filename alias:

```text
afs_b01_decision_crosswalk.json
```

as a known memory-review artifact.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan B01 decision crosswalk` |
| Memory source status | `Selected files` |
| Artifact inspector | shows 5 local shot decisions, 7 AFS import decisions, and 47 broader review decisions |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not fill decisions, approve assets, run context projection, call
  providers, copy media, persist browser edits, or write durable Memory.
- The main inspector module remains under the project file-size target by
  moving B01-specific facts into `memory-workbench-loulan-b01-inspector.js`.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
# 4 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_loulan_memory_package.py -q
# 14 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 744 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 context and generation blocked until the operator fills the five
  local B01 shot decisions.
- If operators select only the crosswalk JSON, they can now inspect the 5/7/47
  split without regenerating a full Loulan package.
