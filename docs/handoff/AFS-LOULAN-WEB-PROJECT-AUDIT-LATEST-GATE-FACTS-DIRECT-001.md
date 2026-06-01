# AFS-LOULAN-WEB-PROJECT-AUDIT-LATEST-GATE-FACTS-DIRECT-001

Date: 2026-06-01

Owner role: Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Scope

Add a stable `latest_gate_facts` fact to the directly selected Loulan
`afs_project_audit_package_probe.json` inspector.

The fact resolves the newest available gate-facts object from the project audit
probe, preferring a project-audit latest sync object when present, then the
root latest sync object, then the root/project/package gate-facts fallbacks.
This keeps the audit probe useful as the consolidated review entry point
without adding a new Web fact for every future Loulan sync object.

## Boundary Evidence

- This is a read-only selected-file projection.
- It does not regenerate the Loulan package.
- It does not scan directories.
- It does not call image, video, LLM, ASR, or external download providers.
- It does not apply B01 decisions or project B02 context.
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
  "status": "pass_b01_still_blocked",
  "latest_gate_facts": "blocked_until_b01_human_review",
  "package_gate_facts": "pass_b01_still_blocked",
  "root_gate_facts": "pass_b01_still_blocked",
  "package_gate_b01_apply": "blocked_validation_not_ready",
  "root_gate_next_context": "blocked_until_b01_human_review"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_audit_probe.py -q
# 1 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_audit_probe.py tests\test_web_static_loulan_project_manifests.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_governance_audits.py -q
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
- Treat the project audit probe as consolidated review evidence only; it is not
  approval, acceptance, promotion, context execution, provider smoke, or durable
  Memory.
