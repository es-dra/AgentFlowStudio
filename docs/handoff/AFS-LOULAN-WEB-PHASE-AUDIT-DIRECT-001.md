# AFS-LOULAN-WEB-PHASE-AUDIT-DIRECT-001

## Scope

Recognize a directly selected Loulan `asset_governance_phase_audit.json` file
as a read-only Memory Workbench artifact.

## What Changed

- Added the `loulan_asset_governance_phase_audit` contract alias for
  `asset_governance_phase_audit.json`.
- Added `apps/web/memory-workbench-loulan-phase-audit-inspector.js`.
- Wired the inspector into Memory Workbench artifact titles, focus targets,
  status, and facts.
- Extended the existing project-audit-probe direct inspector so it also shows
  `phase_gate_audit` when the probe JSON includes the package phase gate.

## Real Probe

Input:

```text
D:\Projects\LoulanSceneAssets\reviews\asset_governance_phase_audit.json
```

Observed selected-file state:

- Artifact type: `loulan_asset_governance_phase_audit`
- Artifact class: `known_contract`
- Source role: `Loulan asset governance phase audit`
- Memory bundle count: `1`
- Status: `blocked_until_b01_human_review`
- Focus targets: `project`, `review`, `next-pass`
- Facts:
  - phases: `5`
  - passed: `4`
  - blocked expected: `1`
  - failures: `0`
  - registry assets: `87`
  - eligible context refs: `3`
  - blocked context refs: `84`
  - pending B01 decisions: `5`
  - provider calls started: `false`
  - writes long-term memory: `false`
  - new media generated: `false`

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_project_audit_probe.py tests\test_web_static_loulan_phase_audit.py -q
```

Result: `2 passed`.

Refresh checks after current Loulan count sync:

- Related direct-probe tests: `4 passed`.
- Full AFS suite: `763 passed`.
- Staging preflight: pass.
- `git diff --check`: no whitespace errors; CRLF touch warnings only.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No package regeneration required for direct file review.
- No B01 decision apply.
- No context projection.
- No human acceptance recorded.
- No durable Memory write.
