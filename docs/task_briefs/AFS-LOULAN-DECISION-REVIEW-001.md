# AFS-LOULAN-DECISION-REVIEW-001 - Loulan Decision Review Pack

## Task

Add a no-call Loulan decision review pack that turns a human review pack plus a
decision template or filled decision file into a bounded operator gap report.

## Goal

Make the current 47 real Loulan pending decisions reviewable before context
projection:

```text
human review pack + decisions -> decision review pack -> filled decisions
-> context bundle projection
```

The review pack must show missing, pending, invalid, and ready decision states
without approving assets, calling providers, or writing Company memory.

## Non-goals

- Do not call providers.
- Do not fill or approve human decisions.
- Do not restructure Loulan source files.
- Do not commit ignored run outputs.
- Do not write Company memory or claim product acceptance.

## Owner Role

Memory / Evidence Steward + Workflow Engineer + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Deep
Why this mode: The slice touches Loulan memory protocol, CLI surface, contract
examples, real local probe evidence, and claim-boundary records.
Subagent needed: no
Close condition: command, contracts, tests, real no-call probe, and handoff are
recorded.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- `agentflow/memory/loulan_decision_review_pack.py`
- `apps/cli/loulan_decision_review_command.py`
- `apps/cli/command_registry.py`
- Loulan decision review tests and contract examples
- `docs/loulan_decision_review_pack_contract.md`
- ignored output under `data/processed/runs/loulan_decision_review_pack/`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed run outputs

## Acceptance Criteria

- [x] CLI writes `loulan_decision_review_pack.json` and Markdown report.
- [x] Pack records missing, pending, invalid, and ready decision states.
- [x] Pack supports real Loulan `asset:*` decision refs.
- [x] Contract example and registry include the new artifact type.
- [x] Real no-call probe summarizes 47 pending decisions without approval.
- [x] Provider calls, human acceptance, business validation, and durable memory
      remain explicitly unclaimed.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-review-pack --review-pack data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\03_human_review\loulan_human_review_pack.json --decisions data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\04_decision_template\loulan_decisions.template.json --created-at "2026-06-01T16:00:00+08:00" --output data\processed\runs\loulan_decision_review_pack\real_probe_2026_06_01
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-DECISION-REVIEW-001.md
```
