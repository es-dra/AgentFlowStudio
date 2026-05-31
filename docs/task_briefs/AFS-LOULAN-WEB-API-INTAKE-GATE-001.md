# AFS-LOULAN-WEB-API-INTAKE-GATE-001 - Web API Intake Gate

## Task

Render API workbench plan `context_projection.decision_intake_gate` in the
memory workbench.

## Goal

When an operator selects only a Loulan API workbench plan plus the package, the
Workbench should still show the context projection intake gate carried into
the API request preview layer.

## Non-goals

- Do not execute API workbench actions in Web.
- Do not persist decisions or context projections.
- Do not infer approval from `not_supplied`.
- Do not call image, video, ASR, LLM, or external providers.
- Do not write durable Memory or Company knowledge-base content.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: Narrow selected-file Web projection change with static tests.
Subagent needed: no
Close condition: protocol and inspector show API context intake gate without
persistence, execution, or provider calls.
```

## Write Scope

- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-inspector.js`
- `tests/test_web_memory_loulan_package_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] Protocol controls include `api context intake gate`.
- [x] API workbench inspector exposes `context_intake_gate`.
- [x] `not_supplied` remains visible as evidence, not approval.
- [x] Rendering stays read-only and selected-file only.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_package_static.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-API-INTAKE-GATE-001.md
```
