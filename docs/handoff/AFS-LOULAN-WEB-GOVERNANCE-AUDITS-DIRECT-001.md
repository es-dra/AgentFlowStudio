# AFS-LOULAN-WEB-GOVERNANCE-AUDITS-DIRECT-001

## Scope

Recognize directly selected Loulan governance audit JSON files as read-only
Memory Workbench artifacts.

## What Changed

- Added contract aliases for:
  - `loulan_manifest_reference_audit` / `manifest_reference_audit.json`
  - `loulan_text_encoding_audit` / `text_encoding_audit.json`
- Added `apps/web/memory-workbench-loulan-governance-audit-inspector.js`.
- Wired both audit types into Memory Workbench artifact title, focus target,
  status, and inspector fact routing.

## Real Probe

Inputs:

```text
D:\Projects\LoulanSceneAssets\reviews\manifest_reference_audit.json
D:\Projects\LoulanSceneAssets\reviews\text_encoding_audit.json
```

Observed selected-file state:

- Manifest reference audit:
  - artifact type: `loulan_manifest_reference_audit`
  - artifact class: `known_contract`
  - source role: `Loulan manifest reference audit`
  - status: `pass`
  - JSON files checked: `14`
  - registry assets: `87`
  - errors: `0`
  - missing sha256: `0`
  - missing files: `0`
  - absolute refs: `0`
  - secret-like refs: `0`
  - invalid asset types: `0`
  - invalid statuses: `0`
- Text encoding audit:
  - artifact type: `loulan_text_encoding_audit`
  - artifact class: `known_contract`
  - source role: `Loulan text encoding audit`
  - status: `pass`
  - text files checked: `268`
  - decode errors: `0`
  - marker hits: `0`
  - errors: `0`

Both direct probes show:

- memory bundle count: `1`
- provider calls started: `false`
- writes long-term memory: `false`
- new media generated: `false`

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_governance_audits.py tests\test_web_static_loulan_phase_audit.py -q
```

Result: `3 passed`.

Refresh checks after current Loulan count sync:

- Related direct-probe tests: `4 passed`.
- Full AFS suite: `763 passed`.
- Staging preflight: pass.
- `git diff --check`: no whitespace errors; CRLF touch warnings only.

Refresh checks after canonical registry type/status audit:

- Manifest reference audit direct view now surfaces invalid asset types `0` and
  invalid statuses `0`.
- Related governance/phase/project-audit tests: `4 passed`.
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
