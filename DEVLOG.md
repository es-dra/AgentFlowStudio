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
