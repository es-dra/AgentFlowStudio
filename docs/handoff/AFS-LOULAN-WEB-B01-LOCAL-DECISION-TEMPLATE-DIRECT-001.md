# AFS-LOULAN-WEB-B01-LOCAL-DECISION-TEMPLATE-DIRECT-001

Status: Direct selected-file recognition for the local Loulan B01 human
decision template implemented.

## Scope

The Web Artifact Workspace now recognizes:

```json
{
  "artifact_type": "loulan_b01_human_review_decision_template"
}
```

and the filename alias:

```text
b01_human_review_decision_template.json
```

as a known memory-review artifact.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan B01 human decision template` |
| Memory source status | `Selected files` |
| Artifact inspector | shows five B01 decision items, five pending decisions, allowed decisions, and target shot IDs |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not fill decisions, import AFS promotion decisions, approve assets,
  run context projection, call providers, copy media, persist browser edits, or
  write durable Memory.
- The direct local template remains an operator review aid; `approve_anchor`,
  `request_repair`, or `reject` must still be filled explicitly before context
  projection can proceed.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/manifests/b01_human_review_decision_template.json
```

Observed facts:

```json
{
  "artifactType": "loulan_b01_human_review_decision_template",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan B01 human decision template",
  "memoryBundleCount": 1,
  "sourceStatus": "Selected files",
  "status": "pending_human_review",
  "decision_items": "5",
  "pending_decisions": "5",
  "target_shots": "B01-S01, B01-S02, B01-S03, B01-S04, B01-S05",
  "human_acceptance_recorded": "false",
  "provider_calls_started": "false"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
# 5 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
# 20 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 745 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 context and generation blocked until the operator fills the five
  local B01 shot decisions.
- After decisions are filled, use the existing B01 decision import and decision
  intake gates before context bundle projection.
