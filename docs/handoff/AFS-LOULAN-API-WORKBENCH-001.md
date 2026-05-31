# AFS-LOULAN-API-WORKBENCH-001

Status: no-call Loulan API workbench dry-run plan implemented.

## What Changed

- Added `agentflow.memory.loulan_api_workbench` to build
  `agentflow_loulan_api_workbench_plan` from a Loulan memory package.
- Added `loulan-api-workbench-plan` CLI.
- Added sanitized contract example
  `examples/agentflow/loulan_api_workbench_plan.example.json`.
- Added `docs/loulan_api_workbench_contract.md` and registered the contract in
  the AgentFlow registry and audit report.
- Extended the Web memory workbench to recognize a selected Loulan API plan and
  show adapter, request preview, response ledger, QA gate, and promotion gate
  status beside the Loulan package.
- Extended Loulan package asset entries with sha256 values so reference packs
  can use hashes instead of local file paths.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --created-at "2026-06-01T10:00:00+08:00" --output data\processed\runs\loulan_api_workbench\local_probe
```

writes:

- `loulan_api_workbench_plan.json`
- `reference_pack.json`
- `prompt_compiler_preview.json`
- `request_manifest.json`
- `response_ledger.json`
- `qa_promotion_gates.json`
- `loulan_api_workbench_plan.md`

On the current real Loulan local probe, the reference pack is blocked and zero
requests are previewed because the current asset refs remain candidate or
rejected rather than approved/promoted for API reuse.

## Safety Boundaries

- No provider calls.
- No provider config, credential, bearer header, signed URL, or response URL is
  read or persisted.
- No generated media is committed.
- No Company memory write or durable Memory runtime.
- No human acceptance, provider smoke, business validation, or quality claim.
- Promotion remains blocked until provider response, QA, human review, and an
  explicit promotion decision exist.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py tests\test_web_memory_loulan_package_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
# 36 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --created-at "2026-06-01T10:00:00+08:00" --output data\processed\runs\loulan_api_workbench\local_probe
# succeeded; reference pack blocked; requests previewed 0; provider calls not started

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\loulan-api-workbench
# 688 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

Ignored local probe output:

```text
data/processed/runs/loulan_api_workbench/local_probe/
```

Browser-level Web check loaded `http://127.0.0.1:8769/#memory` in the Codex
in-app browser with no console errors.

## Next Work

- Run a human Loulan B01 review and explicitly promote or reject selected
  character anchors.
- After at least one anchor is approved/promoted, rerun the API workbench plan
  and inspect the generated request preview in Web.
- Add a live image adapter only in a separate task with explicit provider config
  and image capability gate.
