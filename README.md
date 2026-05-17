# NarratoCut

[中文 README](README.zh-CN.md)

NarratoCut is a Python-based MVP for AI-assisted short video production workflows.
It currently supports text-to-hook analysis, mock script generation, clip planning, mock slicing, workflow run contracts, run inspection, agent-readable run review reports, static workflow plan drafts, a lightweight model gateway, FFmpeg readiness checks, and a standalone minimal real slicing PoC.

This is a clean-room project. The previous AVP workspace is reference material only and is not used as a source code base.

## Current Status

NarratoCut is a CLI-first, schema-first, workflow-first prototype. The default pipeline is local and mock-driven:

```text
text -> hooks -> scripts -> clip_plans -> mock clips
```

Implemented capabilities:

- ROI / hook analysis with a local mock provider
- Mock short-video script generation
- Deterministic ClipPlan generation
- Mock slicing output with `slice_manifest.json` and `.txt` placeholder clips
- Sequential YAML workflow execution
- Run contract artifacts: `run_manifest.json`, `trace.json`, and `quality_report.json`
- `ncut inspect-run` for local harness inspection of workflow run directories
- `ncut review-run` for agent-readable `review_report.json` generation
- `ncut draft-plan` for static `workflow_plan.json` draft generation
- Model Gateway Lite with mock default and optional OpenAI-compatible provider code path
- FFmpeg availability probe
- Real slicing command contract
- Standalone `ncut slice-real` PoC for local FFmpeg slicing from clip plans

Not implemented yet:

- full real FFmpeg video slicing workflow
- subtitle burn-in
- vertical crop or aspect-ratio adaptation
- BGM, cover generation, or multi-track timelines
- web UI, API server, database, queue, or hosted SaaS runtime

## Project Layout

```text
apps/                 CLI, API, and future web entrypoints
narratocut/           Core Python package
workflows/            YAML workflow definitions
prompts/              Auditable prompt templates
configs/              Example configuration files
examples/             User-facing demo inputs
data/                 Local runtime data; generated files are ignored
docs/                 Architecture and operating notes
tests/                Automated tests and fixtures
```

## Requirements

- Python 3.12 is recommended.
- The project declares `>=3.11,<3.13`.
- Python 3.13 is not recommended yet because ASR, video, and model-adjacent dependencies often lag the newest runtime.
- FFmpeg is optional at this stage. `ffmpeg-check` only probes local availability.

## Quick Start

PowerShell:

```powershell
cd D:\Projects\NarratoCut
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m pytest
.venv\Scripts\ncut version
```

Run the full mock workflow:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
```

Expected generated files:

```text
data/processed/runs/demo_full_mock/
+-- manifest.json
+-- run_manifest.json
+-- trace.json
+-- quality_report.json
+-- hooks.json
+-- scripts.json
+-- clip_plans.json
+-- slice_manifest.json
+-- clips/
    +-- clip_plan_script_mock_001.txt
    +-- clip_plan_script_mock_002.txt
    +-- clip_plan_script_mock_003.txt
```

Generated files under `data/processed/` are ignored by git.

Inspect the generated run:

```powershell
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
```

Generate an agent-readable review report:

```powershell
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```

Generate a static workflow plan draft:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/reports/workflow_plan.json
```

Run contract details are documented in [`docs/run_contract.md`](docs/run_contract.md).
The reviewer contract is documented in [`docs/agent_reviewer_contract.md`](docs/agent_reviewer_contract.md).
The workflow plan contract is documented in [`docs/workflow_plan_contract.md`](docs/workflow_plan_contract.md).

## Model Gateway Boundary

The default provider is `mock`, so the standard CLI and workflow commands do not need an API key and do not access the network.

Remote LLM calls are disabled by default. Set `NARRATOCUT_ALLOW_REMOTE_LLM=true` only when real provider calls are intended.

Local model settings belong in `configs/models.yaml`, which is ignored by git. Commit only `configs/models.example.yaml`.

## FFmpeg Boundary

Check local FFmpeg availability:

```powershell
.venv\Scripts\ncut ffmpeg-check
```

If FFmpeg is not installed or not on `PATH`, this command reports an unavailable status. That is acceptable for the current MVP.

Run the standalone minimal real slicing PoC:

```powershell
.venv\Scripts\ncut slice-real --video <local_input.mp4> --clip-plans <clip_plans.json> --output data/outputs/real_slicing_demo
```

This command is separate from the default mock workflow. It requires local
FFmpeg and local video input, writes `real_slice_manifest.json`, and may generate
`.mp4` outputs under the chosen output directory. It does not burn subtitles,
crop video, add BGM, create covers, or run a full production timeline.

## Development Checks

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m compileall -q apps narratocut tests
.venv\Scripts\ncut --help
.venv\Scripts\ncut version
.venv\Scripts\ncut draft-plan --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/reports/workflow_plan.json
.venv\Scripts\ncut slice-real --help
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```
