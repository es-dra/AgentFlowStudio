# DEVLOG

## 2026-05-16 - Phase 4 Model Gateway Lite

- Added a lightweight model gateway layer with config loading, provider errors, `ModelGateway`, and a minimal OpenAI-compatible provider.
- Kept existing ROI and workflow commands on the default mock path; no CLI command requires API keys or network access.
- Added `NARRATOCUT_ALLOW_REMOTE_LLM=true` as an explicit provider-side guard before OpenAI-compatible HTTP calls.
- Updated example model and environment configuration without storing secrets.
- Verification: `pytest` passed with 37 tests, `compileall` passed, and the mock CLI/workflow commands still generated local ignored artifacts under `data/processed/runs/`.
