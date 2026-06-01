# AFS-LOULAN-WEB-PROJECT-AUDIT-PROBE-DIRECT-001

Date: 2026-06-01

Owner role: Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Scope

Recognize a directly selected Loulan AFS project audit package probe JSON in
the Web Artifact Workspace.

The target artifact is:

```json
{
  "artifact_type": "loulan_afs_project_audit_package_probe"
}
```

Filename alias:

```text
afs_project_audit_package_probe.json
```

## Implementation

- Added the artifact alias and Loulan memory-artifact type registration.
- Added a focused project-audit-probe inspector module.
- Routed the Memory Workbench inspector title, status, facts, and focus targets
  through the new module.
- Added a focused static Web test for direct selected-file recognition.

## Inspector Facts

The direct artifact view surfaces:

- `manifest_reference_audit`
- `text_encoding_audit`
- `promotion_gate`
- `b01_feedback_loop_gate`
- `b01_pending_decisions`
- `eligible_refs`
- `blocked_refs`
- `provider_calls_started`
- `writes_long_term_memory`

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not regenerate the Loulan package.
- It does not scan directories.
- It does not call image, video, LLM, ASR, or external download providers.
- It does not copy media.
- It does not execute context projection.
- It does not infer B01 acceptance or promote candidate assets.
- It does not write durable Memory.

## Real Local Probe

Input:

```text
D:/Projects/LoulanSceneAssets/reviews/afs_project_audit_package_probe.json
```

Observed direct Web projection:

```json
{
  "artifactType": "loulan_afs_project_audit_package_probe",
  "artifactClass": "known_contract",
  "sourceRole": "Loulan AFS project audit package probe",
  "memoryBundleCount": 1,
  "status": "pass_b01_still_blocked",
  "facts": {
    "manifest_reference_audit": "pass",
    "text_encoding_audit": "pass",
    "promotion_gate": "blocked",
    "b01_feedback_loop_gate": "blocked_pending_human_review",
    "b01_pending_decisions": "5",
    "eligible_refs": "3",
    "blocked_refs": "89",
    "provider_calls_started": "false",
    "writes_long_term_memory": "false"
  }
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_audit_probe.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_audit_probe.py tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_package_static.py -q
# 14 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 755 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 and B02 blocked until human review decisions are explicitly filled
  and validated.
- Use the project audit probe as review evidence only; it is not approval,
  acceptance, promotion, or durable memory.
