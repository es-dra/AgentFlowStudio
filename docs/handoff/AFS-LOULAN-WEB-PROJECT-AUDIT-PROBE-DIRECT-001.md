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
- The inspector now also surfaces package-audit summary sync facts when the
  probe includes `afs_package_audit_summary_sync`.
- The inspector also surfaces CLI summary probe facts when the probe includes
  `afs_package_audit_summary_cli_probe`.
- Added a focused static Web test for direct selected-file recognition.

## Inspector Facts

The direct artifact view surfaces:

- `manifest_reference_audit`
- `text_encoding_audit`
- `promotion_gate`
- `b01_feedback_loop_gate`
- `b01_pending_decisions`
- `b01_operator_entrypoint`
- `b01_operator_pending_decisions`
- `b01_operator_steps`
- `b01_operator_blocked_until_count`
- `b01_operator_recommendations`
- `b01_operator_pending_operator_decisions`
- `eligible_refs`
- `blocked_refs`
- `provider_calls_started`
- `writes_long_term_memory`
- `package_audit_summary_sync`
- `package_manifest_errors`
- `package_invalid_asset_types`
- `package_invalid_statuses`
- `package_text_errors`
- `package_phase_failures`
- `package_phase_pending_b01`
- `package_summary_eligible_refs`
- `package_summary_blocked_refs`
- `package_summary_provider_calls_started`
- `package_summary_writes_long_term_memory`
- `package_audit_summary_cli`
- `package_cli_stdout_lines`
- `package_cli_eligible_refs`
- `package_cli_blocked_refs`
- `package_cli_provider_calls_started`
- `package_cli_writes_long_term_memory`

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
    "b01_operator_entrypoint": "blocked_pending_human_review",
    "b01_operator_pending_decisions": "5",
    "b01_operator_steps": "6",
    "b01_operator_blocked_until_count": "4",
    "b01_operator_recommendations": "5",
    "b01_operator_pending_operator_decisions": "5",
    "eligible_refs": "3",
    "blocked_refs": "90",
    "package_audit_summary_sync": "pass_b01_still_blocked",
    "package_manifest_errors": "0",
    "package_invalid_asset_types": "0",
    "package_invalid_statuses": "0",
    "package_text_errors": "0",
    "package_phase_failures": "0",
    "package_phase_pending_b01": "5",
    "package_summary_eligible_refs": "3",
    "package_summary_blocked_refs": "90",
    "package_audit_summary_cli": "pass_b01_still_blocked",
    "package_cli_stdout_lines": "3",
    "package_cli_eligible_refs": "3",
    "package_cli_blocked_refs": "90",
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
