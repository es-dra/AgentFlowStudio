# NarratoCut

[中文 README](README.zh-CN.md)

NarratoCut is a Python-based MVP for AI-assisted short video production workflows.
It currently supports text-to-hook analysis, mock script generation, clip planning, mock slicing, a lightweight model gateway, and FFmpeg readiness checks for future real slicing.

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
- Model Gateway Lite with mock default and optional OpenAI-compatible provider code path
- FFmpeg availability probe
- Real slicing command contract

Not implemented yet:

- real FFmpeg video slicing workflow
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

Phase 7 only defines the real slicing command contract. It does not execute real FFmpeg slicing and does not generate `.mp4` outputs.

## Development Checks

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m compileall -q apps narratocut tests
.venv\Scripts\ncut --help
.venv\Scripts\ncut version
```
