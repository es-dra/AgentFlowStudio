# AFS-LOULAN-CONTEXT-PROBE-001 - Real Loulan No-Call Context Probe

## Task

Run the current Loulan B01 no-call chain against
`D:\Projects\LoulanSceneAssets` and verify the new API workbench context
projection input on real local assets.

## Goal

Confirm that the real Loulan package can flow through:

```text
package -> api preview -> human review pack -> decision template
-> context bundle projection -> api preview with context projection
```

The expected current result is a blocked next pass because the decision template
is unfilled. The API workbench must not fall back to package-level eligible refs
when that blocked projection is supplied.

## Non-goals

- Do not call providers.
- Do not fill human decisions.
- Do not restructure Loulan source files.
- Do not commit ignored run outputs.
- Do not write Company memory or claim product acceptance.

## Owner Role

Memory / Evidence Steward + Provider Adapter Agent + Harness / QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Deep
Why this mode: Real local asset probe touches memory package, API plan, review,
decision, context projection, and claim-boundary evidence.
Subagent needed: no
Close condition: ignored probe outputs are written, summarized, and tracked.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- ignored output under `data/processed/runs/loulan_api_context_probe/`
- `docs/handoff/AFS-LOULAN-CONTEXT-PROBE-001.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider configs, local secrets, generated media, or committed examples

## Acceptance Criteria

- [x] Real Loulan package command completes without provider calls.
- [x] Package-only API preview remains dry-run only.
- [x] Human review pack and decision template are generated without approval.
- [x] Unfilled template blocks context bundle projection.
- [x] API preview with blocked projection has zero requests and
      `context_projection_not_ready`.
- [x] Probe outputs remain ignored local artifacts.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-memory-package --project-root "D:\Projects\LoulanSceneAssets" --created-at "2026-06-01T15:00:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\01_package
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\01_package\loulan_memory_package.json --created-at "2026-06-01T15:05:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\02_api_package_only
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-human-review-pack --package data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\01_package\loulan_memory_package.json --api-plan data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\02_api_package_only\loulan_api_workbench_plan.json --project-root "D:\Projects\LoulanSceneAssets" --block-id B01 --created-at "2026-06-01T15:10:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\03_human_review
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-template --review-pack data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\03_human_review\loulan_human_review_pack.json --created-at "2026-06-01T15:15:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\04_decision_template
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\03_human_review\loulan_human_review_pack.json --decisions data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\04_decision_template\loulan_decisions.template.json --created-at "2026-06-01T15:20:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\05_context_from_template
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --package data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\01_package\loulan_memory_package.json --context-projection data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\05_context_from_template\loulan_context_bundle_projection.json --created-at "2026-06-01T15:25:00+08:00" --output data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\06_api_with_blocked_context
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-CONTEXT-PROBE-001.md
```
