# DEVLOG

## 2026-05-16 - Phase 4 Model Gateway Lite

- Added a lightweight model gateway layer with config loading, provider errors, `ModelGateway`, and a minimal OpenAI-compatible provider.
- Kept existing ROI and workflow commands on the default mock path; no CLI command requires API keys or network access.
- Added `NARRATOCUT_ALLOW_REMOTE_LLM=true` as an explicit provider-side guard before OpenAI-compatible HTTP calls.
- Updated example model and environment configuration without storing secrets.
- Verification: `pytest` passed with 37 tests, `compileall` passed, and the mock CLI/workflow commands still generated local ignored artifacts under `data/processed/runs/`.

## 2026-05-16 - Phase 5 ClipPlan + Slicing MVP

- Added deterministic `ShortVideoScript -> ClipPlan` planning and mock slicing that writes `.txt` placeholder clips plus `slice_manifest.json`.
- Kept Phase 5 free of FFmpeg, real media reads, real `.mp4` generation, network calls, Web/API, database, queues, and complex workflow DAGs.
- Added CLI commands `generate-clip-plans` and `mock-slice`; CLI remains a thin wrapper over `narratocut.slicing_sop`.
- Verification: `pytest` passed with 41 tests, `compileall` passed, and the Phase 5 CLI chain generated `clip_plans.json`, `slice_manifest.json`, and 3 ignored mock clip files under `data/processed/runs/demo_phase5/`.

## 2026-05-16 - Phase 6 Workflow Full Mock Pipeline

- Added workflow nodes `generate_clip_plans` and `mock_slice`, reusing the Phase 5 slicing SOP without FFmpeg or real media access.
- Added `workflows/mock_text_to_slices.yaml` for the full mock chain: text -> hooks -> scripts -> clip_plans -> mock clips.
- Updated workflow docs with the full mock run command and expected artifacts.
- Verification: full mock workflow test passed and CLI run generated `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, and 3 ignored `.txt` mock clip files.

## 2026-05-16 - Phase 7 Real Slicing Design + FFmpeg Probe

- Added `ffmpeg_probe` for structured FFmpeg availability checks without requiring FFmpeg during tests.
- Added `real_slicer` command-contract helpers that build, but do not execute, minimal FFmpeg slice commands.
- Added `ffmpeg-check` CLI as an informational local probe; it does not alter mock workflows or require real video assets.
- Added real slicing design notes documenting the current mock boundary and future FFmpeg input/output contract.

## 2026-05-17 - Phase 7.5 Run Contract + Harness Inspection Baseline

- Added standardized run contract artifacts for workflow runs: `run_manifest.json` and `trace.json`.
- Added harness quality checks and run inspection that write `quality_report.json` without moving quality decisions into workflow nodes.
- Added `ncut inspect-run --run-dir ...` to inspect generated workflow run directories and return a non-zero exit code when quality checks fail.
- Documented the run contract boundary in `docs/run_contract.md` and updated workflow/README guidance.
- Verification: `pytest` passed with 57 tests, `compileall` passed, `ncut version` returned `0.1.0`, the full mock workflow generated the run contract artifacts, `inspect-run` reported `12 passed / 0 failed / 0 warnings`, and `git diff --check` passed with line-ending warnings only.

## 2026-05-17 - Phase 7.6 Agent Reviewer Contract

- Added a read-only harness reviewer that reads an existing workflow run and writes `review_report.json`.
- Added `ncut review-run --run-dir ...` for agent-readable review report generation with `passed`, `warning`, and `failed` status aggregation.
- Kept the reviewer outside workflow execution: it does not rerun workflows, call FFmpeg, call remote LLMs, or modify source run artifacts.
- Documented the reviewer contract in `docs/agent_reviewer_contract.md`.

## 2026-05-17 - Phase 7.7 Workflow Plan Draft

- Added a static workflow planner that converts workflow YAML and a planned input file into `workflow_plan.json`.
- Added `ncut draft-plan --workflow ... --input ... --output ...` without executing workflow nodes or creating run artifacts.
- Used `configs/tool_catalog.yaml` only to enrich plan step purpose text; workflow YAML remains the source of step order and outputs.
- Kept planning separate from execution, FFmpeg, remote LLMs, Web/API, database, queue, and agent runtime.
- Documented the planning contract in `docs/workflow_plan_contract.md`.
