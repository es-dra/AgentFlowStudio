# AFS-LOULAN-WEB-B01-STATUS-DIRECT-001

Status: Direct selected-file recognition for Loulan B01 validation and apply
status artifacts implemented.

## Scope

The Web Artifact Workspace now recognizes these B01 status artifacts:

```json
{
  "artifact_type": "loulan_b01_decision_validation_report"
}
```

```json
{
  "artifact_type": "loulan_b01_decision_apply_result"
}
```

Known filename aliases:

```text
human_review_decision_validation_report.json
b01_decision_validation_report.json
b01_decision_apply_result.json
```

## Web Surfaces

| Surface | Validation report behavior | Apply result behavior |
|---|---|---|
| Artifact classification | `known_contract` | `known_contract` |
| Source role | `Loulan B01 decision validation report` | `Loulan B01 decision apply result` |
| Memory source status | `Selected files` | `Selected files` |
| Artifact inspector | shows decision item counts and pending/approved/repair/rejected counts | shows apply requested/applied flags and validation status |

## Boundary Evidence

- These are read-only selected-file projections.
- They do not fill or apply decisions, import AFS promotion decisions, run
  context projection, call providers, copy media, persist browser edits, or
  write durable Memory.
- `blocked_pending_human_review` remains a true operator gate until the local
  B01 decision template is filled.

## Real Local Probe

```powershell
node --input-type=module
# read D:/Projects/LoulanSceneAssets/reviews/B01-horizontal-pack/human_review_decision_validation_report.json
```

Observed facts:

```json
{
  "artifactType": "loulan_b01_decision_validation_report",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan B01 decision validation report",
  "memoryBundleCount": 1,
  "sourceStatus": "Selected files",
  "status": "blocked_pending_human_review",
  "decision_items": "5",
  "pending_decisions": "5",
  "approved_decisions": "0",
  "repair_requested": "0",
  "rejected_decisions": "0",
  "human_acceptance_recorded": "false",
  "provider_calls_started": "false"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
# 22 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 747 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 context and generation blocked until the operator fills the five
  local B01 shot decisions.
- Use these direct status artifacts to confirm whether validation/apply remains
  blocked after the operator updates the local decision template.
