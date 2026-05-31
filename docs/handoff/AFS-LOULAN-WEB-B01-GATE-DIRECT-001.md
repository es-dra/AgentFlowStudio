# AFS-LOULAN-WEB-B01-GATE-DIRECT-001

Status: Direct selected-file recognition for the Loulan B01 feedback-loop gate
implemented.

## Scope

The Web Artifact Workspace now recognizes this direct local gate artifact:

```json
{
  "artifact_type": "loulan_afs_b01_feedback_loop_gate"
}
```

and the filename alias:

```text
afs_b01_feedback_loop_gate.json
```

as a known memory-review artifact. This allows the operator to inspect the B01
gate without first regenerating or selecting the full Loulan memory package.

## Web Surfaces

| Surface | Behavior |
|---|---|
| Artifact classification | `known_contract` |
| Source role | `Loulan B01 feedback loop gate` |
| Memory source status | `Selected files` |
| Artifact inspector | shows B01 status, pending decisions, validation/apply status, context readiness, human acceptance, and provider-call flags |

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not fill decisions, apply decisions, run context projection, call
  providers, copy media, persist browser edits, or write durable Memory.
- Candidate/blocked B01 state remains blocked until human review fills all
  required B01 decisions.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
# 3 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_loulan_memory_package.py -q
# 13 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 743 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Next Work

- Continue to treat the local Loulan B01 gate as blocked until
  `D:\Projects\LoulanSceneAssets` reports ready human decisions.
- After ready decisions exist, rerun Loulan validation/apply, AFS B01 import,
  decision intake, context bundle, API preview, and package/Web review in that
  order.
