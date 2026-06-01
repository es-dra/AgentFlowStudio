# AFS-LOULAN-PACKAGE-PHASE-GATE-AUDIT-001

## Scope

Surface the Loulan asset-governance phase audit in the no-call memory package
and Web Memory Workbench package review path.

## What Changed

- `loulan-memory-package` now reads these optional `project_manifest.json`
  fields:
  - `asset_governance_phase_audit`
  - `asset_governance_phase_audit_report`
  - `asset_governance_phase_audit_status`
- The package writes the audit under `project_audits.phase_gate`.
- The Markdown package report shows the phase gate audit status.
- Memory Workbench package review shows:
  - `phase gate` in the `Project audits` bundle card;
  - `phase gate audit` in protocol controls;
  - `phase_gate_audit` in inspector facts.

## Real Probe

Input:

```text
D:\Projects\LoulanSceneAssets
```

Output:

```text
data/processed/runs/loulan_memory_package/local_probe_package_blocked_count_sync/
```

Observed state:

- `project_audits.phase_gate.status`: `blocked_until_b01_human_review`
- `project_audits.phase_gate.artifact_ref`: `reviews/asset_governance_phase_audit.json`
- `project_audits.phase_gate.report_ref`: `reviews/asset_governance_phase_audit.md`
- Manifest reference audit: `pass`
- Text encoding audit: `pass`
- Promotion gate: `blocked`
- Eligible refs: `3`
- Blocked refs: `90`
- Provider calls: not started
- Durable Memory write: false

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_web_static_loulan_project_audit_probe.py -q
.venv\Scripts\python.exe -B -m pytest --assert=plain -q
.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
git diff --check
```

Results:

- Focused package/Web tests: `5 passed`.
- Related Loulan package/probe tests: `6 passed`.
- Full suite: `755 passed`.
- Refresh suite: `.venv\Scripts\python.exe -B -m pytest --assert=plain -q` ->
  `763 passed`.
- Staging preflight: pass.
- `git diff --check`: no whitespace errors; CRLF touch warnings only.
- Real package output safety scan found no `D:\`, `C:\`, `file://`,
  provider URL, token, signed URL, API key, `.mp4`, or `.mov`.
- Refresh package output parsed as 3 eligible refs, 90 blocked refs, manifest
  reference audit `pass`, text encoding audit `pass`, phase gate
  `blocked_until_b01_human_review`, no provider calls, and no durable Memory
  write.
- Modified code files remain under 300 lines.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No B01 decision apply.
- No human acceptance recorded.
- No durable Memory write.
- No Company knowledge-base material copied into the repo.
