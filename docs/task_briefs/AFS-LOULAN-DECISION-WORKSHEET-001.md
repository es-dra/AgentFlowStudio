# AFS-LOULAN-DECISION-WORKSHEET-001 - Loulan Decision Worksheet

## Task

Add a no-call Loulan decision worksheet that turns
`agentflow_loulan_decision_review_pack` into copy-only manual fill rows.

## Goal

Give the operator a tighter manual fill surface for the current 47 Loulan
pending decisions:

```text
decision review pack -> decision worksheet -> manually filled decisions
-> context bundle projection
```

The worksheet must keep decision fields empty and must not approve, reject,
promote, merge, expire, repair, or infer human acceptance.

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
Mode: Standard
Why this mode: The slice adds a focused deterministic artifact, CLI, contract
example, real no-call probe, and project records without Web UI changes.
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

- `agentflow/memory/loulan_decision_worksheet.py`
- `apps/cli/loulan_decision_worksheet_command.py`
- `apps/cli/command_registry.py`
- Loulan decision worksheet tests and contract examples
- `docs/loulan_decision_worksheet_contract.md`
- ignored output under `data/processed/runs/loulan_decision_worksheet/`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed run outputs

## Acceptance Criteria

- [x] CLI writes `loulan_decision_worksheet.json` and Markdown report.
- [x] Worksheet rows expose empty manual fill fields and copy-target JSON.
- [x] Ready rows remain non-acceptance evidence and do not become approval
      claims.
- [x] Contract example and registry include the new artifact type.
- [x] Real no-call probe writes 47 manual-fill rows without approval.
- [x] Provider calls, human acceptance, business validation, and durable memory
      remain explicitly unclaimed.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_worksheet.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-DECISION-WORKSHEET-001.md
```
