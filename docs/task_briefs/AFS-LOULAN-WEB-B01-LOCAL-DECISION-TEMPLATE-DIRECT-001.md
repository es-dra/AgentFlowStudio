# AFS-LOULAN-WEB-B01-LOCAL-DECISION-TEMPLATE-DIRECT-001 - Direct Local B01 Decision Template Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected local Loulan
`b01_human_review_decision_template.json` file as a read-only memory-review
artifact.

## Goal

Close this no-call operator review path:

```text
Loulan local B01 human decision template
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show the five B01 shot decisions that currently
block next-pass context, without importing, approving, or promoting anything.

## Non-goals

- Do not fill B01 decisions.
- Do not import the local template into AFS promotion decisions.
- Do not run context projection or API preview.
- Do not call providers or generate media.
- Do not persist browser edits or durable Memory.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified no-call Web review surface.
Subagent needed: no
Close condition: Direct local B01 decision templates are recognized as known
memory artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-loulan-b01-inspector.js`
- `tests/test_web_static_artifact_workspace.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_b01_human_review_decision_template` is recognized from both
      `artifact_type` and `b01_human_review_decision_template.json`.
- [x] The direct local B01 decision template participates in
      `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows five decision items and five pending decisions.
- [x] Inspector lists allowed decisions and target B01 shots.
- [x] Inspector keeps provider-call and human-acceptance flags false.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-LOCAL-DECISION-TEMPLATE-DIRECT-001.md
```
