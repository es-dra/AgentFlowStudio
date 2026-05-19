# NarratoCut

[中文 README](README.zh-CN.md)

NarratoCut is a Python-based, CLI-first technical MVP for AI-assisted short
video production workflows. It is currently an artifact-driven workflow system:
each major step writes readable JSON or media artifacts, and those artifacts can
be inspected and reviewed after a run.

The project is clean-room. The previous AVP workspace is reference material
only and is not used as a source-code base.

## Current Status

NarratoCut is now a CLI-first technical MVP for developer-facing short-video
generation workflows. It is not yet a consumer product, SaaS app, desktop app,
or Web UI product.

The current product path is:

```text
video / transcript / clip_plan
  -> highlight_plan
  -> clip_plan.json
  -> real clips
  -> final_video.mp4
  -> subtitles.srt
  -> final_video_with_subtitles.mp4
  -> cover.jpg
  -> final_video_with_bgm.mp4
  -> finished_package_manifest.json
  -> inspect/review
```

Supported today:

- deterministic script/transcript highlight workflows
- mock and explicit opt-in OpenAI-compatible ASR paths
- local faster-whisper ASR path for offline product smokes
- ClipPlan validation against probed video metadata
- real FFmpeg slicing from existing ClipPlans
- simple final-video assembly from real clips
- final video quality hardening with FFmpeg warning classification
- subtitle export to SRT
- subtitle burn-in for existing videos and SRT files
- cover image export from an existing final video
- local BGM mixing with bounded volume settings
- finished package manifest indexing
- `inspect-run` and `review-run` reports for generated run artifacts
- `draft-plan` for static workflow plans

Not included yet:

- one-command end-to-end product workflow
- Web UI or desktop UI
- automatic music selection or licensing management
- transition templates or multi-track timeline editing
- visual highlight detection from video frames
- publishing/upload integrations
- physical package directory or zip export
- hosted API, database, queue, or SaaS runtime

## Project Layout

```text
apps/                 CLI, API, and future web entrypoints
narratocut/           Core Python package
workflows/            YAML workflow definitions
prompts/              Auditable prompt templates
configs/              Example configuration and tool catalog files
examples/             User-facing demo inputs
data/                 Local runtime data; generated files are ignored
docs/                 Architecture, contracts, roadmap, and smoke docs
tests/                Automated tests and fixtures
```

## Requirements

- Python 3.12 is recommended.
- The project declares `>=3.11,<3.13`.
- Python 3.13 is not recommended yet because media, ASR, and model-adjacent
  dependencies may lag the newest runtime.
- FFmpeg and FFprobe are required for real slicing, final video assembly,
  subtitle burn-in, cover export, and BGM mix workflows.
- Remote LLM and ASR calls are disabled by default.

## Quick Start

PowerShell:

```powershell
cd D:\Projects\NarratoCut
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m pytest
.venv\Scripts\ncut version
```

Run the default mock workflow:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```

Expected generated files include:

```text
manifest.json
run_manifest.json
trace.json
quality_report.json
review_report.json
hooks.json
scripts.json
clip_plans.json
slice_manifest.json
clips/
```

Generated files under `data/processed/`, `data/reports/`, and local media under
`data/raw/` are ignored by git.

## Product Golden Path

For a product-level local smoke after Phase 13, use the Golden Path:

```text
source video + clip_plan
  -> real clips
  -> final_video.mp4
  -> subtitles.srt
  -> final_video_with_subtitles.mp4
  -> cover.jpg
  -> final_video_with_bgm.mp4
  -> finished_package_manifest.json
  -> inspect/review
```

See [`docs/golden_path.md`](docs/golden_path.md) for the required local files,
commands, expected artifacts, and acceptance criteria.

## Main Workflows

Planning and transcript workflows:

- `workflows/script_to_highlight_plan.yaml`
- `workflows/transcript_to_highlight_clip_plan.yaml`
- `workflows/video_to_transcript.yaml`
- `workflows/video_to_transcript_real_asr.yaml`
- `workflows/video_to_highlight_clip_plan.yaml`
- `workflows/video_to_highlight_clip_plan_real_asr.yaml`
- `workflows/video_to_finished_package_local_asr.yaml`
- `workflows/video_script_to_finished_package_local_asr.yaml`

Execution and product artifact workflows:

- `workflows/clip_plan_to_real_clips.yaml`
- `workflows/video_to_real_clips.yaml`
- `workflows/clips_to_final_video.yaml`
- `workflows/transcript_to_subtitles.yaml`
- `workflows/final_video_with_subtitles.yaml`
- `workflows/final_video_to_cover.yaml`
- `workflows/final_video_with_bgm.yaml`
- `workflows/final_video_package.yaml`

Workflow details are documented in [`workflows/README.md`](workflows/README.md).

## Artifact and Review Model

NarratoCut treats generated files as first-class contracts. Important artifacts
include:

```text
run_manifest.json
trace.json
quality_report.json
review_report.json
real_slice_manifest.json
final_video_manifest.json
subtitle_manifest.json
subtitle_burn_manifest.json
cover_manifest.json
audio_mix_manifest.json
finished_package_manifest.json
```

`inspect-run` writes `quality_report.json`.
`review-run` reads the run artifacts and writes `review_report.json`.

Contract references:

- [`docs/run_contract.md`](docs/run_contract.md)
- [`docs/workflow_plan_contract.md`](docs/workflow_plan_contract.md)
- [`docs/agent_reviewer_contract.md`](docs/agent_reviewer_contract.md)
- [`docs/tool_contracts.md`](docs/tool_contracts.md)
- [`docs/current_architecture.md`](docs/current_architecture.md)

## Remote Provider Boundary

The default model and ASR paths are local/mock. Standard CLI and workflow
commands do not need API keys and do not access the network.

Remote LLM calls require:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_LLM="true"
```

Remote ASR calls require:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
```

Local model settings belong in `configs/models.yaml`, which is ignored by git.
Commit only example configuration files such as `configs/models.example.yaml`.

## FFmpeg Boundary

Check local FFmpeg and FFprobe availability:

```powershell
.venv\Scripts\ncut ffmpeg-check --json
```

If FFmpeg is missing, mock workflows can still run. Real media workflows need
FFmpeg/FFprobe.

## Development Checks

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m compileall apps narratocut tests
git diff --check
.venv\Scripts\python -m apps.cli.main --help
.venv\Scripts\python -m apps.cli.main version
```

## License

MIT License. See [LICENSE](LICENSE).
