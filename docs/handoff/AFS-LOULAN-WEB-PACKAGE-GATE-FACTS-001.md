# AFS-LOULAN-WEB-PACKAGE-GATE-FACTS-001

Date: 2026-06-01

Owner role: Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Scope

Expose the full selected `agentflow_loulan_memory_package` gate chain in the
Memory Workbench artifact inspector.

This is a Web selected-file projection only. It does not regenerate the package,
scan Loulan directories, call providers, apply B01 decisions, project context,
promote assets, copy media, persist browser edits, or write durable Memory.

## Implementation

- Extended `loulanPackageFacts` with package-level promotion and next-context
  status facts.
- Surfaced B01 validation/apply/context readiness, human acceptance, media
  generation, and operator next-context facts directly in the selected package
  inspector.
- Kept the existing audit facts for manifest reference, text encoding, and
  phase gate summaries.

## Inspector Facts Added

- `promotion_gate`
- `next_context_status`
- `context_rule`
- `b01_validation_status`
- `b01_apply_status`
- `b01_context_projection_ready`
- `b01_human_acceptance_recorded`
- `b01_media_generation_started`
- `b01_operator_apply_status`
- `b01_operator_next_context`
- `writes_long_term_memory`

## Real Local Probe

Input:

```text
data/processed/runs/loulan_memory_package/local_probe_root_summary_chain_after_loulan_writeback/loulan_memory_package.json
```

Observed selected package projection:

```json
{
  "artifactType": "agentflow_loulan_memory_package",
  "status": "review ready",
  "facts": {
    "shots": "38",
    "eligible_refs": "3",
    "blocked_refs": "90",
    "promotion_gate": "blocked",
    "next_context_status": "promotion_decision_required",
    "context_rule": "only approved_anchor or promoted_reusable assets may enter context",
    "manifest_reference_audit": "pass",
    "text_encoding_audit": "pass",
    "phase_gate_audit": "blocked_until_b01_human_review",
    "feedback_gate_b01": "blocked_pending_human_review",
    "b01_operator_entrypoint": "blocked_pending_human_review",
    "b01_pending_decisions": "5",
    "b01_validation_status": "blocked_pending_human_review",
    "b01_apply_status": "blocked_validation_not_ready",
    "b01_context_projection_ready": "false",
    "b01_human_acceptance_recorded": "false",
    "b01_media_generation_started": "false",
    "b01_operator_apply_status": "blocked_validation_not_ready",
    "b01_operator_next_context": "blocked_until_b01_human_review",
    "writes_long_term_memory": "false",
    "provider_calls_started": "false"
  }
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_package_static.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py tests\test_web_static_loulan_project_audit_probe.py tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_governance_audits.py -q
# 11 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 763 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

git diff --check
# passed; CRLF warnings only
```

## Next Work

- Keep B01 and B02 blocked until human review decisions are explicitly filled
  and validated.
- Use this package inspector as review evidence only; it is not approval,
  acceptance, promotion, context execution, provider smoke, or durable Memory.
