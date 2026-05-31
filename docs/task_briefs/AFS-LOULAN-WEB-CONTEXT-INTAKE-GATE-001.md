# AFS-LOULAN-WEB-CONTEXT-INTAKE-GATE-001 - Web Context Intake Gate

## Task

Render `decision_intake_gate` from selected Loulan context bundle projection
artifacts in the memory workbench.

## Goal

Make the pre-context intake gate visible to operators when they inspect a
context projection, so a projection cannot look ready while hiding whether the
validated intake report was supplied.

## Non-goals

- Do not edit or persist decisions in the browser.
- Do not execute context projection from Web.
- Do not infer approval from `not_supplied` or blocked gates.
- Do not call image, video, ASR, LLM, or external providers.
- Do not write durable Memory or Company knowledge-base content.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: Narrow Web projection change with static selected-file tests.
Subagent needed: no
Close condition: bundle card, protocol control, inspector facts, and timeline
show the context projection intake gate without persistence or execution.
```

## Write Scope

- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `tests/test_web_memory_loulan_decision_context_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] Context bundle card detail includes intake gate status.
- [x] Protocol control detail includes intake gate status.
- [x] Inspector facts expose `decision_intake_gate` and
      `context_bundle_ready`.
- [x] Timeline detail includes intake gate status.
- [x] Rendering stays read-only and selected-file only.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-CONTEXT-INTAKE-GATE-001.md
```
