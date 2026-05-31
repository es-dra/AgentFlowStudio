# AFS-LOULAN-WEB-MANIFEST-SET-SUMMARY-001 - Loulan Selected Manifest Set Summary

## Task

Let the Memory Workbench summarize a selected set of Loulan top-level manifest
JSON files as one project-level no-call cockpit when a full
`agentflow_loulan_memory_package` is not selected.

## Goal

Close this review path:

```text
multiple Loulan manifest JSON files
-> Web selected files
-> Loulan manifest-set cockpit
-> blocked next-pass summary
```

The operator should immediately see manifest coverage, asset status, B01
pending decisions, request counts, provider gates, and next-pass blockers.

## Non-goals

- Do not call Image2, Kling, or any provider.
- Do not generate images or videos.
- Do not scan the Loulan asset directory.
- Do not mutate manifests, registries, shot lists, or request plans.
- Do not execute context projection or API preview.
- Do not infer approval from `eligible_context_refs`.
- Do not persist browser edits or durable Memory.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds deterministic selected-file Web summarization
and verified no-call evidence over the real Loulan manifests.
Subagent needed: no
Close condition: A selected Loulan manifest set shows project-level blocked
status and existing Loulan Web regressions pass.
```

## Write Scope

- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-loulan-manifest-set.js`
- `tests/test_web_static_loulan_manifest_set_summary.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] Selecting multiple Loulan direct manifests without a full package builds
      `contract_type: loulan_manifest_set`.
- [x] The view reports selected manifest count, B01 decision blocker, request
      counts, asset registry counts, project manifest coverage, and B02 next
      context blocker.
- [x] Eligible context refs and blocked refs are separated visually and do not
      imply durable Memory or approval.
- [x] Provider/image/video/media/durable-memory gates remain no-call and
      blocked.
- [x] Real `D:\Projects\LoulanSceneAssets\manifests` probe produces a blocked
      B02 manifest-set summary with 12 selected manifests.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_manifest_set_summary.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_manifest_set_summary.py tests\test_web_static_loulan_project_manifests.py tests\test_web_static_loulan_request_manifests.py tests\test_web_static_loulan_b01_status_artifacts.py tests\test_web_static_loulan_context_draft.py tests\test_web_static_loulan_asset_registry.py tests\test_web_static_artifact_workspace.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-WEB-MANIFEST-SET-SUMMARY-001.md
```
