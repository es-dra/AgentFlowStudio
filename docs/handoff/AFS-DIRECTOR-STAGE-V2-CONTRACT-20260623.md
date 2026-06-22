# AFS Director Stage V2 Contract Handoff

Date: 2026-06-23 by Codex
Branch: `codex/director-stage-v2-contract-20260623`
Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\director-stage-v2-contract-20260623`

## Scope

- Added a low-conflict Runtime-side Director Stage V2 contract/compiler foundation.
- Kept Studio frontend, storyboard, keyframe, asset popover, and context resolver files untouched.
- Kept provider gates unchanged and did not call remote LLM/image/video providers.

## Changed Files

- `apps/api/runtime_director_compiler_v2.py`
- `tests/test_runtime_director_compiler_v2.py`
- `docs/handoff/AFS-DIRECTOR-STAGE-V2-CONTRACT-20260623.md`

## Contract Boundary

- New contract entry is `DirectorSceneBlockingV1` in `apps/api/runtime_director_compiler_v2.py`.
- Compiler entry is `compile_director_scene_blocking`.
- V2 compiler consumes `camera`, `subjects`, `props`, `lights`, `stage`, and `exports`.
- `safe_exports` exposes only `screenshot_artifact_id` and `thumbnail_artifact_id`.
- Backend asset signatures from `visual_asset_signatures` override any frontend-provided subject signature.
- If V2 blocking is missing and a `fallback_setup` is provided, the compiler delegates to existing `compile_director_setup` and marks `trace_summary.fallback_source = director_setup_2d`.

## TDD Evidence

- Red 1: `tests/test_runtime_director_compiler_v2.py` failed with `ModuleNotFoundError` before the V2 module existed.
- Green 1: blank V2 blocking test passed after minimal contract/compiler skeleton.
- Red 2: semantic tests failed because camera, subjects, props, and backend asset signatures were not yet compiled.
- Green 2: V2 semantic tests passed after deterministic compiler logic.
- Red 3: fallback test failed with unexpected `fallback_setup` parameter.
- Green 3: fallback test passed after delegating to v1 compiler.

## Verification

- Focused baseline before edits: `pytest tests\test_runtime_director_compiler.py -q` -> 5 passed.
- Focused V2: `pytest tests\test_runtime_director_compiler_v2.py -q` -> 5 passed.
- Focused V1+V2: `pytest tests\test_runtime_director_compiler.py tests\test_runtime_director_compiler_v2.py -q` -> 10 passed.
- CLI help: `python -m apps.cli.main --help` -> passed.
- CLI version: `python -m apps.cli.main version` -> `0.1.0`.
- Full pytest: `python -m pytest` -> 607 passed, 520 deselected, 2 existing warnings.
- Diff whitespace check: `git diff --check` -> passed.

## Remaining

- V2 is not wired into Runtime request models, Studio save/load state, OpenAPI, keyframe context, or provider flows.
- No Three.js stage, screenshot artifact writer, or browser validation was implemented in this slice.
- Human acceptance and provider smoke remain unclaimed.
