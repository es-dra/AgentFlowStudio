# AFS-LOULAN-PILOT-001 - Loulan Memory Pilot Package

## Task

Turn `D:\Projects\LoulanSceneAssets` into a read-only AgentFlow Studio pilot
package for the Memory Production Architecture.

## Goal

Define and implement the first no-call Loulan package contract:

```text
project manifest
-> shot list
-> asset library
-> review / run evidence
-> promotion gate
-> next context bundle draft
-> canvas workbench projection
```

## Non-goals

- Do not restructure or move Loulan source files.
- Do not turn Loulan into an independent app in this slice.
- Do not start image, video, LLM, ASR, or external download calls.
- Do not write to Company knowledge base or durable Memory runtime.
- Do not commit generated media, provider credentials, signed URLs, or local
  absolute asset paths.

## Owner Role

Memory / Evidence Steward + Web UI Agent + QA Reviewer

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
- project tracker, memory contract, DEVLOG, and handoff docs

## Do Not Touch

- `D:\Projects\LoulanSceneAssets` source structure
- `D:\Learning materials\Learning_notes\Company`
- provider config files, `.env`, `.dev.vars`, or `configs/models.yaml`
- generated media or runtime artifacts outside ignored `data/processed/`

## Acceptance Criteria

- [x] A sanitized `agentflow_loulan_memory_package` example is committed.
- [x] A CLI command builds the package from explicit Loulan manifests.
- [x] The package blocks candidate, rejected, expired, and missing-hash assets
      from next context.
- [x] The package marks unsafe built-in image generation as blocked until an API
      workbench/provider ledger exists.
- [x] The Web memory workbench can render the Loulan package as a canvas-first
      read-only review surface.
- [x] The output distinguishes structure verification, runtime verification,
      human acceptance, provider smoke, business validation, and durable Memory
      runtime.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_contract_examples.py tests\test_cli_command_registry_boundaries.py tests\test_web_memory_static_structure.py tests\test_web_memory_sample_static.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T09:00:00+08:00" --output data\processed\runs\loulan_memory_package\local_probe
.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
pytest
git diff --check
```

## Remote Provider Policy

Default work is no-call. Live provider work requires a separate user-approved
task and the matching explicit capability gate for image or video generation.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-PILOT-001.md
```
