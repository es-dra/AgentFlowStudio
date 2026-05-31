# AFS-LOULAN-B01-DECISION-IMPORT-001 - Loulan B01 Decision Import

## Task

Add a no-call bridge that imports explicit local Loulan B01 shot decisions into
the existing AFS promotion-decision contract.

## Goal

Prepare the next safe handoff after the operator fills B01 decisions:

```text
Loulan local B01 decision file + AFS human review pack
-> AFS promotion decisions
-> decision review / worksheet / intake
-> context bundle projection
```

The bridge must keep pending decisions pending and must not infer approval from
candidate keyframes or review evidence.

## Non-goals

- Do not generate images or videos.
- Do not call Kling, image providers, LLMs, ASR, or external services.
- Do not approve, promote, or accept B01 shots automatically.
- Do not write durable Memory runtime state or Company memory.
- Do not copy media from `D:\Projects\LoulanSceneAssets`.

## Owner Role

Memory / Evidence Steward + Workflow Engineer + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds a deterministic importer, CLI command, contract,
real no-call probe, and project records without provider or Web UI work.
Subagent needed: no
Close condition: focused and Loulan decision-chain tests pass, real pending
probe is recorded, and handoff/tracker records are updated.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- `agentflow/memory/loulan_b01_decision_import.py`
- `apps/cli/loulan_b01_decision_import_command.py`
- `apps/cli/command_registry.py`
- `tests/test_loulan_b01_decision_import.py`
- `docs/loulan_b01_decision_import_contract.md`
- ignored output under `data/processed/runs/loulan_b01_decision_import/`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- Loulan media assets
- Company source knowledge base
- provider configs, local secrets, signed URLs, or generated media

## Acceptance Criteria

- [x] CLI writes `loulan_b01_decisions.imported.json` and Markdown report.
- [x] Imported output keeps `agentflow_loulan_promotion_decisions`.
- [x] Ready B01 shot decisions overlay matching required decision slots.
- [x] Pending local B01 decisions stay pending.
- [x] Partial imports continue to block decision intake until all required rows
      are complete.
- [x] Provider calls, human acceptance, business validation, and durable memory
      remain explicitly unclaimed.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_b01_decision_import.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_b01_decision_import.py tests\test_loulan_decision_intake.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-B01-DECISION-IMPORT-001.md
```
