# AFS-LOULAN-WEB-CONTEXT-DRAFT-DIRECT-001 - Direct Loulan Next Context Draft Recognition

## Task

Let the Web Artifact Workspace recognize a directly selected Loulan
`next_context_bundle_draft.json` file as a read-only memory-review artifact.

## Goal

Close this no-call next-pass review path:

```text
Loulan next generation context bundle draft
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show the B02 target, eligible refs, blocked refs,
review-evidence refs, and provider/human gate status without running context
projection or provider preview.

## Non-goals

- Do not unlock the B01 human-review gate.
- Do not execute context projection or API preview.
- Do not promote candidate assets or write durable Memory.
- Do not call providers or generate media.
- Do not copy media or scan local directories.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified no-call Web review surface.
Subagent needed: no
Close condition: Direct Loulan next-context draft files are recognized as known
memory artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-context-draft-inspector.js`
- `tests/test_web_static_loulan_context_draft.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `loulan_next_generation_context_bundle_draft` is recognized from both
      `artifact_type` and `next_context_bundle_draft.json`.
- [x] The direct draft participates in `workspace.memoryBundle`.
- [x] Memory Workbench source status becomes `Selected files`.
- [x] Inspector shows target next block, eligible refs, blocked refs by status,
      review evidence refs, and gate statuses.
- [x] Inspector keeps provider-call, new-media, and durable-memory flags false.
- [x] Main inspector stays under the project file-size target by delegating
      draft facts to a focused module.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_context_draft.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-CONTEXT-DRAFT-DIRECT-001.md
```
