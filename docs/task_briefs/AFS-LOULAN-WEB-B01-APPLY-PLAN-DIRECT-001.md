# AFS-LOULAN-WEB-B01-APPLY-PLAN-DIRECT-001 - Direct B01 Apply Plan Draft Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected Loulan
`b01_decision_apply_plan_draft.json` file as a read-only memory-review
artifact.

## Goal

Close this no-call operator review path:

```text
Loulan B01 decision apply plan draft
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show why B01 apply remains blocked without applying
status changes or promoting keyframes.

## Non-goals

- Do not fill or apply B01 decisions.
- Do not mutate the asset registry, shot list, or next context draft.
- Do not execute context projection or API preview.
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
Close condition: Direct B01 apply plan drafts are recognized as known memory
artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-loulan-b01-inspector.js`
- `tests/test_web_static_loulan_b01_status_artifacts.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_b01_decision_apply_plan_draft` is recognized from both
      `artifact_type` and `b01_decision_apply_plan_draft.json`.
- [x] The direct apply plan participates in `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows block ID, preconditions, planned mutations, and blocked
      mutation count.
- [x] Inspector keeps dry-run, no-apply, no-provider, and no-memory-write
      boundaries explicit.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-APPLY-PLAN-DIRECT-001.md
```
