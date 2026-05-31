# AFS-LOULAN-WEB-DECISION-REVIEW-001 - Web Decision Review Rendering

## Task

Render `agentflow_loulan_decision_review_pack` in the Web memory workbench when
the operator selects the JSON artifact explicitly.

## Goal

Make the no-call Loulan decision review pack visible in the canvas workbench as
a review/gap layer between decision templates and context bundle projection.

The Web view must show:

- bundle card for the decision review pack;
- protocol control for decision review;
- next-pass status/action using the review pack status;
- inspector facts for pending/ready/missing slots and no-acceptance boundary;
- timeline node for Decision Review.

## Non-goals

- Do not add browser editing or decision persistence.
- Do not auto-scan Loulan directories.
- Do not write Company memory or project files.
- Do not call providers.
- Do not treat pending decision review as human acceptance.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Deep
Why this mode: The slice touches Web artifact recognition, Loulan protocol
projection, no-claim boundaries, and multi-session task records.
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

- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-package.js`
- `tests/test_web_memory_loulan_decision_context_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed run outputs

## Acceptance Criteria

- [x] Workspace normalization exposes `loulanDecisionReviewPack`.
- [x] Bundle summary includes "Decision review pack".
- [x] Protocol controls include "decision review".
- [x] Next pass shows the decision review status and no acceptance claim.
- [x] Inspector shows pending/ready/missing facts and provider/human flags.
- [x] Timeline includes "Decision Review".
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
docs/handoff/AFS-LOULAN-WEB-DECISION-REVIEW-001.md
```
