# AFS-LOULAN-PACKAGE-B01-CROSSWALK-001 - Loulan B01 Decision Crosswalk Intake

## Task

Let `loulan-memory-package` read the optional Loulan
`manifests/afs_b01_decision_crosswalk.json` artifact and expose its safe
decision-layer summary to CLI/Web consumers.

## Goal

Make the B01 human-review blockage precise:

```text
Loulan local 5-shot B01 gate
-> AFS 7-slot B01 import gate
-> AFS broader 47-slot decision-review gate
```

The package must preserve this distinction without treating any layer as human
acceptance or durable Memory.

## Non-goals

- Do not fill B01 decisions.
- Do not approve Zhou Tong character slots.
- Do not generate, copy, or inspect media.
- Do not call image/video/LLM/ASR providers.
- Do not execute context projection or API previews.
- Do not write durable Memory runtime state.

## Owner Role

Memory / Evidence Steward + Web UI Agent + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice adds a small package reader module, package example,
Web summary/protocol/timeline display, real no-call probe, and regression tests.
Subagent needed: no
Close condition: package and Web tests pass, real probe shows 5/7/47 decision
layers, and safety scan finds no unsafe output.
```

## Write Scope

- `agentflow/memory/loulan_feedback_gates.py`
- `agentflow/memory/loulan_package.py`
- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-loulan-artifacts.js`
- `examples/agentflow/loulan_memory_package.example.json`
- Loulan package/Web tests
- `TASK_TRACKER.md`, `DEVLOG.md`, and this handoff/task brief

## Acceptance Criteria

- [x] Package includes `feedback_loop_gates.b01_decision_crosswalk`.
- [x] Package validates crosswalk safety flags: no provider call, no media
      generation, no human acceptance, no long-term memory write.
- [x] Package summary preserves local 5-shot, AFS 7-slot, and broader 47-slot
      counts.
- [x] CLI Markdown report shows B01 decision crosswalk status.
- [x] Web bundle/protocol/timeline show the crosswalk without execution or
      persistence.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T06:58:00+08:00" --output data\processed\runs\loulan_memory_package\b01_crosswalk_probe
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-PACKAGE-B01-CROSSWALK-001.md
```
