# AFS-LOULAN-WEB-DECISION-WORKSHEET-001 - Web Decision Worksheet Rendering

## Task

Render `agentflow_loulan_decision_worksheet` in the Web memory workbench when
the operator selects the JSON artifact explicitly.

## Goal

Make the no-call Loulan decision worksheet visible in the canvas workbench as a
manual-fill layer after decision review and before context bundle projection.

The Web view must show:

- workspace normalization for `loulanDecisionWorksheet`;
- bundle card for the decision worksheet;
- protocol control for decision worksheet;
- next-pass status/action using `worksheet_status`;
- selected-file inspector facts for rows and no-acceptance boundaries;
- timeline node for Decision Worksheet.

## Non-goals

- Do not add browser editing or decision persistence.
- Do not auto-scan Loulan directories.
- Do not write Company memory or project files from the browser.
- Do not call providers.
- Do not treat worksheet rows as human acceptance.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Deep
Why this mode: The slice touches Web artifact recognition, Loulan protocol
projection, no-claim boundaries, module factoring, and multi-session records.
Subagent needed: no
Close condition: selected-file rendering, focused tests, and handoff recorded.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `tests/test_web_memory_loulan_decision_context_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed run outputs

## Acceptance Criteria

- [x] Workspace normalization exposes `loulanDecisionWorksheet`.
- [x] Bundle summary includes "Decision worksheet".
- [x] Protocol controls include "decision worksheet".
- [x] Next pass shows worksheet status and no acceptance claim.
- [x] Inspector shows rows, manual template decisions, provider flag, and
      human acceptance flag.
- [x] Timeline includes "Decision Worksheet".
- [x] No browser persistence, project-file writes, provider calls, or approval
      inference are added.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-DECISION-WORKSHEET-001.md
```
