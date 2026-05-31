# AFS-LOULAN-WEB-B01-GATE-DIRECT-001 - Direct B01 Gate Selected-File Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected Loulan
`afs_b01_feedback_loop_gate.json` file as a memory-review artifact, even when
the full `loulan-memory-package` output is not selected.

## Goal

Close this no-call review path:

```text
Loulan local B01 feedback loop gate JSON
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show the B01 gate status without turning it into
human acceptance, context execution, provider execution, or durable Memory.

## Non-goals

- Do not fill B01 decisions.
- Do not generate or copy media.
- Do not call image/video/LLM/ASR providers.
- Do not execute context projection or API previews.
- Do not write browser edits or durable Memory state.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection, memory source
classification, and inspector facts with a focused regression test.
Subagent needed: no
Close condition: Direct gate JSON is recognized as a known memory artifact and
the Web/Loulan static regression suite passes.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `tests/test_web_static_artifact_workspace.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_afs_b01_feedback_loop_gate` is recognized from both
      `artifact_type` and `afs_b01_feedback_loop_gate.json`.
- [x] The direct gate artifact participates in `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows B01 gate status, pending decisions, validation/apply
      status, context readiness, human acceptance flag, and provider-call flag.
- [x] The artifact remains read-only and non-promotional.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_loulan_memory_package.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-B01-GATE-DIRECT-001.md
```
