# AFS-LOULAN-WEB-B01-DECISION-IMPORT-001 - Loulan B01 Import Web Visibility

## Task

Surface B01 decision-import summaries in the static Memory Workbench when an
operator selects an imported `agentflow_loulan_promotion_decisions` file.

## Goal

Make the AFS Web review lane show that a selected decision file came from the
local B01 decision import bridge and whether it has ready or pending decisions.

The Web view must remain read-only and must not turn imported decisions into
approval, acceptance, context projection, or provider execution.

## Non-goals

- Do not add editing or persistence in the browser.
- Do not call providers or run context projection.
- Do not change the decision JSON contract.
- Do not copy Loulan media or read project directories automatically.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice updates static selected-file rendering and tests only;
no provider, persistence, or runtime execution is involved.
Subagent needed: no
Close condition: Web static tests show bundle, protocol, inspector, timeline,
and next-pass views all preserve the B01 import boundary.
```

## Write Scope

- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `apps/web/memory-workbench-inspector.js`
- `tests/test_web_memory_loulan_decision_context_static.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] Bundle summary titles imported files as `B01 decision import`.
- [x] Protocol controls show imported-ready and pending counts.
- [x] Next-pass action uses `Decision import` rather than a generic template
      label when `import_summary` is present.
- [x] Artifact inspector shows source block, imported-ready count, pending
      count, skipped count, and no-acceptance boundary.
- [x] Timeline distinguishes B01 decision imports from plain templates.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_static_structure.py tests\test_web_memory_sample_static.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-DECISION-IMPORT-001.md
```
