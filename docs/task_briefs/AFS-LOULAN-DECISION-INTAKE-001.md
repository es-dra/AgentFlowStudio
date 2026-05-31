# AFS-LOULAN-DECISION-INTAKE-001 - Loulan Decision Intake

## Task

Add a no-call Loulan decision intake report that validates manually filled
decisions from a decision worksheet before context bundle projection.

## Goal

Provide a gate between manual worksheet filling and context projection:

```text
decision worksheet + manually filled decisions -> intake report
-> context bundle projection
```

The intake report must prove only structural readiness for
`loulan-context-bundle`. It must not approve assets, call providers, write
Company memory, or claim product acceptance.

## Non-goals

- Do not call providers.
- Do not fill or approve human decisions.
- Do not run context bundle projection automatically.
- Do not restructure Loulan source files.
- Do not commit ignored run outputs.
- Do not write Company memory or claim product acceptance.

## Owner Role

Memory / Evidence Steward + Workflow Engineer + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds a focused deterministic validator, CLI, contract
example, real no-call probe, and project records without Web UI changes.
Subagent needed: no
Close condition: command, contracts, tests, real blocked probe, and handoff are
recorded.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- `agentflow/memory/loulan_decision_intake.py`
- `apps/cli/loulan_decision_intake_command.py`
- `apps/cli/command_registry.py`
- Loulan decision intake tests and contract examples
- `docs/loulan_decision_intake_contract.md`
- ignored output under `data/processed/runs/loulan_decision_intake/`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed run outputs

## Acceptance Criteria

- [x] CLI writes `loulan_decision_intake_report.json` and Markdown report.
- [x] Report validates required refs, allowed decisions, human reviewer,
      evidence refs, review notes, and unexpected refs.
- [x] Unfilled worksheet decisions block with pending manual decisions.
- [x] Worksheet JSON cannot be passed as a decisions file.
- [x] Contract example and registry include the new artifact type.
- [x] Provider calls, human acceptance, business validation, and durable memory
      remain explicitly unclaimed.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-DECISION-INTAKE-001.md
```
