# AFS-LOULAN-WEB-B01-STATUS-DIRECT-001 - Direct B01 Validation/Apply Status Recognition

## Task

Let the Web Artifact Workspace recognize directly selected Loulan B01
validation and apply-result JSON outputs as read-only memory-review artifacts.

## Goal

Close this no-call operator review path:

```text
Loulan B01 validation/apply result JSON
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show whether the B01 human decision file is still
blocked before importing, projecting context, or previewing provider requests.

## Non-goals

- Do not fill or apply B01 decisions.
- Do not import AFS promotion decisions.
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
Close condition: B01 validation/apply outputs are recognized as known memory
artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-loulan-b01-inspector.js`
- `tests/test_web_static_loulan_b01_status_artifacts.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_b01_decision_validation_report` is recognized from both
      `artifact_type` and known validation report filenames.
- [x] `loulan_b01_decision_apply_result` is recognized from both
      `artifact_type` and `b01_decision_apply_result.json`.
- [x] Both artifacts participate in `workspace.memoryBundle`.
- [x] Validation report inspector shows decision counts and blocked status.
- [x] Apply result inspector shows apply/requested/applied/validation status.
- [x] Inspector keeps provider-call and durable-memory flags false.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-STATUS-DIRECT-001.md
```
