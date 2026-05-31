# AFS-LOULAN-CONTEXT-PROBE-001

Status: real Loulan no-call context probe completed.

## Probe Scope

Input source:

```text
D:\Projects\LoulanSceneAssets
```

Ignored output root:

```text
data/processed/runs/loulan_api_context_probe/real_probe_2026_06_01/
```

Executed chain:

```text
01_package
02_api_package_only
03_human_review
04_decision_template
05_context_from_template
06_api_with_blocked_context
```

## Result Summary

| Check | Result |
|---|---|
| Shots indexed | 38 |
| Registry assets indexed | 85 |
| Package eligible refs | 3 |
| Package blocked refs | 88 |
| Package-only API preview | ready, 1 request preview |
| Human review next pass | blocked_until_human_review |
| Required human decisions | 47 |
| Decision template | pending_human_input, 47 slots |
| Context projection from unfilled template | blocked_invalid_decisions |
| API preview with blocked projection | blocked, 0 requests |
| API context blocking reason | context_projection_not_ready |

## Boundary Evidence

- `provider_calls_started` remained `false` across package, API previews,
  review pack, decision template, and context projection.
- `writes_long_term_memory` remained `false` across the same artifacts.
- The blocked context projection prevented fallback to package-level eligible
  refs in the final API preview.
- No Company source files, Loulan source files, provider configs, secrets, or
  generated media were modified.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_staging_preflight.py tests\test_agentflow_roadmap_docs.py -q
# 21 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Notes

PowerShell `ConvertFrom-Json` without explicit UTF-8 handling produced noisy
parsing output on Chinese Loulan content. The probe summary above was produced
with Python `json.load(..., encoding="utf-8-sig")` and the underlying JSON
files parsed successfully.

## Next Work

- Manually fill a Loulan decision file from the 47 decision slots.
- Re-run `loulan-context-bundle` with the filled decision file.
- Re-run `loulan-api-workbench-plan --context-projection` and inspect whether
  the next-pass reference pack is ready for preview.
- Keep any live image call blocked until a separate task explicitly authorizes
  `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` and provider config.
