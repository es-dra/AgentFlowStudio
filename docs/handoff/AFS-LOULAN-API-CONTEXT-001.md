# AFS-LOULAN-API-CONTEXT-001

Status: Loulan API workbench context projection input implemented and verified.

## What Changed

- Added optional context projection support to
  `build_loulan_api_workbench_plan`.
- Added `--context-projection` to `loulan-api-workbench-plan`.
- Split context projection validation and reference selection into
  `agentflow.memory.loulan_api_context`.
- API request previews now record `source_context_projection_id` when supplied.
- When a supplied projection is blocked, the API workbench blocks the request
  manifest and does not fall back to package-level eligible refs.
- Web artifact inspector now shows the API plan context projection status.
- Updated the committed API workbench example and contract doc.

## Current Capability

The command can still run package-only:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package <loulan_memory_package.json> --created-at "2026-06-01T13:00:00+08:00" --output data\processed\runs\loulan_api_workbench\plan
```

It can also run with an explicit projection:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package <loulan_memory_package.json> --context-projection <loulan_context_bundle_projection.json> --created-at "2026-06-01T13:00:00+08:00" --output data\processed\runs\loulan_api_workbench\plan
```

The projection path is read-only. It must already contain explicit human
decisions projected into a context bundle.

## Safety Boundaries

- No provider calls.
- No provider config, credentials, bearer headers, signed URLs, or response
  URLs are read or persisted.
- No generated media is written or committed.
- No Company memory write or durable Memory runtime.
- No approval is inferred from review packs, templates, or package status.
- Human acceptance, provider smoke, business validation, and durable memory
  remain unclaimed.

## Verification Snapshot

Verification completed on this workstation:

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py -q
# 10 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py tests\test_loulan_context_bundle.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
# 46 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain
# 707 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --help
# passed; shows --context-projection

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

Edge headless loaded `http://127.0.0.1:8769/#memory` without detected module or
syntax error markers.

## Next Work

- Run a real Loulan B01 human review and fill the decision file manually.
- Re-run `loulan-context-bundle`, then `loulan-api-workbench-plan` with
  `--context-projection`.
- Only after local provider config and `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`
  are explicitly authorized should a live image adapter smoke be added.
