# AFS-LOULAN-PILOT-001

Status: Loulan no-call pilot package and Web workbench projection implemented.

## What Changed

- Added `agentflow.memory.loulan_package` to build a sanitized
  `agentflow_loulan_memory_package` from explicit Loulan local manifests.
- Added `loulan-memory-package` CLI as the product-facing no-call entry point.
- Added a sanitized example package at
  `examples/agentflow/loulan_memory_package.example.json`.
- Registered the Loulan package in the AgentFlow contract example registry.
- Added Web memory workbench support so a selected Loulan package renders as a
  canvas-first review surface with Project, Shots, Assets, Memory Loaded,
  Baseline Plan, Memory-backed Plan, Review, Feedback, and Next Pass nodes.
- Added focused tests for package gating, CLI artifact writes, contract safety,
  and Web rendering.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T09:00:00+08:00" --output data\processed\runs\loulan_memory_package\local_probe
```

writes:

- `loulan_memory_package.json`
- `loulan_memory_package.md`

The current local Loulan probe indexed 38 shots, detected unsafe built-in image
route use, kept provider calls off, and blocked promotion because all current
character refs remain candidate or rejected.

## Safety Boundaries

- No provider calls.
- No Loulan source restructuring.
- No generated media committed.
- No Company knowledge-base write.
- No durable Memory runtime, DB, vector store, hosted service, or RAG.
- No human acceptance, provider smoke, business validation, or quality claim.
- Candidate, rejected, expired, and missing-hash assets are blocked from next
  context.

## Implemented Checks

- Required Loulan inputs: `project_manifest.json`,
  `manifests/shot_list.json`, and `manifests/character_assets.json`.
- Output rejects absolute local paths, generated media refs, bearer headers,
  signed URL fragments, and obvious provider secret keys.
- Provider route safety blocks built-in image generation when Loulan records the
  known image2 route failure.
- Next context bundle separates eligible and blocked memory refs.
- Web feedback draft is browser-local copy text and does not persist durable
  memory.
- Contract registry knows `agentflow_loulan_memory_package` as a supported
  AgentFlow example type.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
# 4 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_contract_examples.py tests\test_cli_command_registry_boundaries.py tests\test_web_memory_static_structure.py tests\test_web_memory_sample_static.py -q
# 38 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T09:00:00+08:00" --output data\processed\runs\loulan_memory_package\local_probe
# succeeded; 38 shots; promotion gate blocked; provider calls not started

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\loulan-memory-pilot
# 681 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

The ignored local probe output is under:

```text
data/processed/runs/loulan_memory_package/local_probe/
```

Browser-level Web check loaded `http://127.0.0.1:8769/#memory` in the Codex
in-app browser with no console errors and confirmed the Memory Workbench plus
sample bundle entry rendered.

## Next Work

- Add a stricter Loulan package schema validator once the source manifests
  stabilize.
- Extend the Web canvas with readiness filters for approved anchors versus
  blocked refs.
- Build the API workbench skeleton around dry-run request manifests, reference
  hashes, response ledger, QA gate, and promotion gate.
- Run a human B01 review and convert selected feedback into candidate memory for
  manual promotion.
