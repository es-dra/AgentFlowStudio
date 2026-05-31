# AFS-LOULAN-WEB-DECISION-INTAKE-001 - Loulan Web Decision Intake

## Task

Render `agentflow_loulan_decision_intake_report` in the Web memory workbench
when the operator selects the JSON artifact explicitly.

## Goal

Make the pre-context decision gate visible beside worksheet and context bundle
artifacts. Operators should see whether the manually filled decision file is
ready for `loulan-context-bundle`.

## Non-goals

- Do not add browser editing or decision persistence.
- Do not run context projection from the browser.
- Do not auto-scan Loulan directories.
- Do not write Company memory or project files from the browser.
- Do not call providers or infer approval.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds selected-file rendering and a focused Web static
test without changing provider or project-file write surfaces.
Subagent needed: no
Close condition: selected-file rendering, focused tests, and handoff recorded.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `tests/test_web_memory_loulan_decision_context_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] Workspace normalization exposes `loulanDecisionIntakeReport`.
- [x] Bundle summary includes "Decision intake report".
- [x] Protocol controls include "decision intake".
- [x] Next pass shows intake status and does not infer readiness.
- [x] Inspector shows context-bundle readiness, ready/pending/invalid counts,
      and human-acceptance boundary.
- [x] Timeline includes "Decision Intake".
- [x] No browser persistence, project-file writes, provider calls, context
      execution, or approval inference are added.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-DECISION-INTAKE-001.md
```
