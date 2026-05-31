# AFS-LOULAN-PACKAGE-B01-CROSSWALK-001

Status: Loulan B01 decision crosswalk intake implemented.

## Scope

`loulan-memory-package` now reads optional:

```text
manifests/afs_b01_decision_crosswalk.json
```

and emits:

```text
feedback_loop_gates.b01_decision_crosswalk
```

The field is a sanitized no-call summary that distinguishes local B01 shot
review from AFS-side import and broader asset governance.

## Real Probe

Command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T06:58:00+08:00" --output data\processed\runs\loulan_memory_package\b01_crosswalk_probe
```

Result:

| Check | Result |
|---|---|
| Package status | written |
| Crosswalk status | blocked_pending_human_review |
| Local B01 shot gate | 5 decisions |
| AFS B01 import gate | 7 decisions |
| AFS broader decision review gate | 47 target refs |
| Unsafe output scan | no matches |

## Web Surfaces

| Surface | Behavior |
|---|---|
| Bundle summary | shows `B01 decision crosswalk` with 5 local shot decisions and 7 AFS import slots |
| Protocol controls | shows crosswalk blocked status |
| Timeline | adds `B01 Decision Crosswalk` |

## Boundary Evidence

- The package is a read-only projection of a local crosswalk manifest.
- It does not fill decisions, approve assets, run context projection, call
  providers, copy media, persist browser edits, or write durable Memory.
- Filling the five local B01 shot decisions must not be treated as broad AFS
  asset approval.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
# 5 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py -q
# 13 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 743 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only

Select-String -Path data\processed\runs\loulan_memory_package\b01_crosswalk_probe\loulan_memory_package.json -Pattern 'D:\\|C:\\|file://|Bearer |signed_url|token=|api_key|secret_key|\.mp4|\.mov'
# no matches
```

## Next Work

- Keep B01 context and generation blocked until the operator fills the five
  local B01 shot decisions.
- After those import into AFS, decide whether the remaining Zhou Tong slots and
  broader asset-governance slots are in scope for the next context bundle.
