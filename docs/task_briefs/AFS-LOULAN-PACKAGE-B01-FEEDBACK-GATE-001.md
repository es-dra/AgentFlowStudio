# AFS-LOULAN-PACKAGE-B01-FEEDBACK-GATE-001 - Loulan Package B01 Gate Intake

## Task

Let `loulan-memory-package` read the optional Loulan
`manifests/afs_b01_feedback_loop_gate.json` file and expose a safe B01 feedback
loop summary to CLI/Web consumers.

## Goal

Close the project-to-AFS loop for the current B01 gate:

```text
Loulan local B01 feedback loop gate
-> AFS Loulan memory package
-> Web workbench package summary / protocol / inspector / timeline
```

The summary must be no-call, no-media-copy, no-absolute-path, and non-acceptance.

## Non-goals

- Do not fill B01 decisions.
- Do not run context projection.
- Do not call image/video/LLM/ASR providers.
- Do not read or copy media files.
- Do not write durable Memory runtime state.

## Owner Role

Memory / Evidence Steward + Web UI Agent + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds an optional package field, example contract,
Web selected-file visibility, real no-call probe, and project records.
Subagent needed: no
Close condition: Loulan package and Web tests pass, real probe shows the B01
gate, and safety scans find no unsafe output.
```

## Write Scope

- `agentflow/memory/loulan_package.py`
- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `apps/web/memory-workbench-inspector.js`
- `examples/agentflow/loulan_memory_package.example.json`
- Loulan package/Web tests
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] Package includes `feedback_loop_gates.b01`.
- [x] Package rejects unsafe gate flags such as provider calls, media
      generation, human acceptance, or long-term memory writes.
- [x] CLI report shows B01 feedback loop gate status.
- [x] Web bundle/protocol/inspector/timeline show the B01 gate without
      execution or persistence.
- [x] Real no-call probe over `D:\Projects\LoulanSceneAssets` shows the gate is
      `blocked_pending_human_review` and contains no unsafe local path/media
      refs in the output.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T21:30:00+08:00" --output data\processed\runs\loulan_memory_package\b01_feedback_gate_probe
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-PACKAGE-B01-FEEDBACK-GATE-001.md
```
