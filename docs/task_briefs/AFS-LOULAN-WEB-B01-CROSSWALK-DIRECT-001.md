# AFS-LOULAN-WEB-B01-CROSSWALK-DIRECT-001 - Direct B01 Crosswalk Selected-File Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected Loulan
`afs_b01_decision_crosswalk.json` file as a memory-review artifact.

## Goal

Close this no-call review path:

```text
Loulan B01 decision crosswalk JSON
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show the 5-shot local gate, 7-slot AFS import gate,
and 47-slot broader review gate without promoting any decision.

## Non-goals

- Do not fill B01 decisions.
- Do not approve AFS decision slots.
- Do not call providers or generate media.
- Do not execute context projection or API preview.
- Do not persist browser edits or durable Memory.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified Web no-call review surface.
Subagent needed: no
Close condition: Direct crosswalk JSON is recognized as a known memory artifact
and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-b01-inspector.js`
- `tests/test_web_static_artifact_workspace.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_afs_b01_decision_crosswalk` is recognized from both
      `artifact_type` and `afs_b01_decision_crosswalk.json`.
- [x] The direct crosswalk artifact participates in `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows local 5-shot, AFS 7-slot, and broader 47-slot counts.
- [x] Inspector keeps provider-call and human-acceptance flags false.
- [x] Inspector B01-specific logic is split from the main inspector module.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-CROSSWALK-DIRECT-001.md
```
