# AFS-LOULAN-API-WORKBENCH-001 - Loulan API Workbench Dry-Run Plan

## Task

Add the first dry-run API workbench skeleton for Loulan image generation.

## Goal

Turn a selected `agentflow_loulan_memory_package` into reviewable provider
request-preview artifacts:

```text
reference pack
-> prompt compiler preview
-> request manifest
-> response ledger
-> QA gate
-> promotion gate
```

## Non-goals

- Do not call image or video providers.
- Do not read provider config, credentials, or local secrets.
- Do not persist generated media, provider task URLs, or response payloads.
- Do not promote candidate memory or write Company knowledge.
- Do not bypass human review when Loulan assets are candidate or rejected.

## Owner Role

Provider Adapter Agent + Security / Secret Audit Agent + Web UI Agent

## Branch

```text
codex/loulan-memory-pilot
```

## Write Scope

- `agentflow/memory/`
- `apps/cli/`
- `apps/web/`
- `examples/agentflow/`
- focused contract, CLI, and Web static tests
- tracker, DEVLOG, and handoff docs

## Acceptance Criteria

- [x] `agentflow_loulan_api_workbench_plan` contract example is committed.
- [x] CLI writes reference pack, prompt preview, request manifest, response
      ledger, QA/promotion gates, full plan JSON, and Markdown report.
- [x] Reference packs use approved refs and sha256 values only.
- [x] Current real Loulan local probe blocks request previews because no
      approved anchor has been promoted for API reuse.
- [x] Web memory workbench can inspect a selected Loulan API plan together with
      the Loulan package.
- [x] No provider call, secret persistence, generated media commit, durable
      memory write, human acceptance, or business validation claim.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py tests\test_web_memory_loulan_package_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T09:00:00+08:00" --output data\processed\runs\loulan_memory_package\local_probe
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --created-at "2026-06-01T10:00:00+08:00" --output data\processed\runs\loulan_api_workbench\local_probe
```

## Remote Provider Policy

No remote provider is authorized in this task. Live image execution requires a
separate task, explicit provider config, and `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-API-WORKBENCH-001.md
```
