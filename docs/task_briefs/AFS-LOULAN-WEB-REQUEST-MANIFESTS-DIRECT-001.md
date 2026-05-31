# AFS-LOULAN-WEB-REQUEST-MANIFESTS-DIRECT-001 - Direct Loulan Request Manifest Recognition

## Task

Let the Web Artifact Workspace recognize directly selected Loulan generation
request manifests as read-only memory-review artifacts:

- `image2_requests.json`
- `kling_i2v_requests.json`

## Goal

Close this no-call generation-planning review path:

```text
Loulan generation request manifest
-> Web selected files
-> Memory Workbench source status
-> Artifact inspector facts
```

The selected-file path must show planned request counts, model coverage, block
coverage, status counts, and provider-call boundaries without starting any
provider request.

## Non-goals

- Do not call Image2, Kling, or any provider.
- Do not generate images or videos.
- Do not mutate request manifests or generated media records.
- Do not execute context projection or API preview.
- Do not persist browser edits or durable Memory.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes selected-file detection and inspector facts,
then records a verified no-call Web review surface.
Subagent needed: no
Close condition: Direct Image2/Kling request manifests are recognized as known
memory artifacts and Web/Loulan regression tests pass.
```

## Write Scope

- `apps/web/artifact-contracts.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-request-manifest-inspector.js`
- `tests/test_web_static_loulan_request_manifests.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] `image2_requests.json` is recognized as
      `loulan_image2_request_manifest`.
- [x] `kling_i2v_requests.json` is recognized as
      `loulan_kling_i2v_request_manifest`.
- [x] Both direct manifests participate in `workspace.memoryBundle`.
- [x] Inspector shows request count, models, blocks, status counts, image
      aspect ratios, video durations, and provider-call boundary.
- [x] Kling plans with blocked requests surface `blocked` status while Image2
      plans without blocked requests remain `review ready`.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_request_manifests.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_b01_decision_import.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-REQUEST-MANIFESTS-DIRECT-001.md
```
