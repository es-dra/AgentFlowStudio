# AFS-LOULAN-WEB-ROOT-LATEST-GATE-FACTS-PROJECT-AUDIT-SYNC-001

Date: 2026-06-01

Owner role: Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Scope

Teach the directly selected Loulan root `project_manifest.json` inspector to
prefer the project-audit latest gate-facts status when resolving
`latest_gate_facts`.

Priority order is now:

```text
afs_project_audit_latest_gate_facts_web_direct_probe_status
afs_latest_gate_facts_web_direct_probe_status
afs_root_project_audit_gate_facts_web_direct_probe_status
afs_project_audit_gate_facts_web_direct_probe_status
afs_root_gate_facts_web_direct_probe_status
afs_package_gate_facts_web_direct_probe_status
```

This keeps the root project entry point aligned with the consolidated project
audit review entry point without adding a new visible fact per sync object.

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
D:/Projects/LoulanSceneAssets/project_manifest.json
```

Observed direct Web projection:

```json
{
  "status": "blocked_until_b01_human_review",
  "latest_gate_facts": "blocked_until_b01_human_review"
}
```

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_project_audit_probe.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_governance_audits.py -q
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
- Treat root manifest direct facts as operator navigation evidence only; they
  are not approval, acceptance, promotion, context execution, provider smoke,
  or durable Memory.
