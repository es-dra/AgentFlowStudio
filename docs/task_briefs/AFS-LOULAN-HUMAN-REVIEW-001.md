# AFS-LOULAN-HUMAN-REVIEW-001 - Loulan B01 Human Review Pack

## Task

Prepare a no-call B01 human review pack from the current Loulan memory package,
API dry-run plan, and manifest-declared review evidence.

## Goal

Create an AgentFlow review artifact that lets a person decide which B01
keyframes and character anchors should be approved, rejected, repaired, or
promoted for next-pass context reuse.

## Non-goals

- Do not approve or reject assets automatically.
- Do not call image, video, LLM, ASR, or external download providers.
- Do not write Company knowledge or durable Memory runtime.
- Do not restructure `D:\Projects\LoulanSceneAssets`.
- Do not commit generated media, provider credentials, signed URLs, or local
  absolute asset paths.

## Owner Role

Memory / Evidence Steward + Web UI Agent + QA Reviewer

## Branch

```text
codex/loulan-memory-pilot
```

## Write Scope

- `agentflow/memory/`
- `apps/cli/`
- `apps/web/`
- `examples/agentflow/`
- focused contract, CLI, and Web static tests
- tracker, DEVLOG, and handoff docs

## Acceptance Criteria

- [x] `agentflow_loulan_human_review_pack` contract example is committed.
- [x] CLI writes review pack JSON, shot review cards, promotion decision
      drafts, feedback event draft, and Markdown report.
- [x] Current B01 real probe keeps human acceptance unrecorded and blocks next
      pass until B01-S03 rejected evidence and candidate character anchors are
      reviewed.
- [x] Web memory workbench can inspect the human review pack with the Loulan
      package and API plan.
- [x] No provider call, generated media commit, durable memory write, human
      acceptance, provider smoke, or business validation claim.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_human_review_pack.py tests\test_web_memory_loulan_human_review_static.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-human-review-pack --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --api-plan data\processed\runs\loulan_api_workbench\local_probe\loulan_api_workbench_plan.json --project-root "D:\Projects\LoulanSceneAssets" --block-id B01 --created-at "2026-06-01T11:00:00+08:00" --output data\processed\runs\loulan_human_review_pack\local_probe
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\loulan-human-review-pack
.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
git diff --check
```

## Remote Provider Policy

No remote provider is authorized in this task. Live image or video execution
requires a separate task with explicit provider config and capability gate.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-HUMAN-REVIEW-001.md
```
