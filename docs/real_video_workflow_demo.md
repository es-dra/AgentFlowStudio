# Real Video Workflow Demo

Phase 9 adds an ROI-aware real video workflow without changing the default mock
pipeline.

The workflow takes one local video, one ROI settings file, and one `ClipPlan`.
It writes execution artifacts first. Inspection and review remain separate
commands.

```text
run-workflow -> inspect-run -> review-run
```

## Current Capability

Phase 9 is the real video execution foundation. It can:

- read local FFmpeg / FFprobe availability
- read video metadata from a local mp4
- load ROI settings and one provided `ClipPlan`
- validate the plan against video duration, output path safety, FFmpeg
  availability, and ROI advisory constraints
- execute real FFmpeg slicing into `.mp4` clips
- write reviewable run artifacts for `inspect-run` and `review-run`

The current workflow executes a manual `ClipPlan`. It does not decide which
moments are highlights.

## Not Included Yet

Phase 9 does not include:

- automatic highlight or viral-moment detection
- ASR or timestamped transcript generation
- script/transcript-to-ClipPlan generation
- clip assembly into a final video
- subtitle burn-in
- BGM, cover generation, or multi-track timelines
- Web UI, API server, database, queue, or agent runtime

## Next Roadmap

Planned follow-up phases:

- Phase 10: script / timestamped transcript highlight detection
- Phase 11: video ASR to timestamped transcript, then highlights and clip plan
- Phase 12: clip assembly MVP, with subtitle and user-provided BGM as later P1
  work
- Phase 13: Web UI v0
- Phase 14: agent runtime / workflow-as-tool

## Local Video

Place a local demo video here:

```text
data/raw/demo_real_video/input.mp4
```

Do not commit the video file. Media files under `data/raw/` are ignored.

## FFmpeg Configuration

Check local tools:

```powershell
.venv\Scripts\afs ffmpeg-check --json
```

If tools are not on `PATH`, set environment variables:

```powershell
$env:NCUT_FFMPEG_PATH="<FFMPEG_BIN_DIR>/ffmpeg.exe"
$env:NCUT_FFPROBE_PATH="<FFMPEG_BIN_DIR>/ffprobe.exe"
```

Or create a local ignored config file from `configs/ffmpeg.example.yaml`:

```yaml
ffmpeg_path: "<FFMPEG_BIN_DIR>/ffmpeg.exe"
ffprobe_path: "<FFMPEG_BIN_DIR>/ffprobe.exe"
timeout_sec: 30
```

## Inputs

Committed example files:

```text
examples/demo_real_video/input.example.json
examples/demo_real_video/roi_config.json
examples/demo_real_video/clip_plan.json
```

Phase 9 supports one local video, one `ROISettings`, one `ClipPlan`, and many
segments inside that plan.

## Run

```powershell
.venv\Scripts\afs run-workflow `
  --workflow workflows/real_video_roi_to_clips.yaml `
  --input examples/demo_real_video/input.example.json `
  --output data/processed/runs/demo_real_video
```

Expected run artifacts:

```text
run_manifest.json
trace.json
video_metadata.json
roi_config.json
clip_plan.json
clip_plan_validation.json
real_slice_manifest.json
clips/
```

`run-workflow` does not write `quality_report.json`.

## Inspect And Review

```powershell
.venv\Scripts\afs inspect-run --run-dir data/processed/runs/demo_real_video
.venv\Scripts\afs review-run --run-dir data/processed/runs/demo_real_video
```

`inspect-run` writes `quality_report.json`.
`review-run` writes `review_report.json`.

## Failure Behavior

If FFmpeg or FFprobe is unavailable, the workflow still writes reviewable
artifacts where possible. The run may fail, but `run_manifest.json`,
`trace.json`, `video_metadata.json`, `clip_plan_validation.json`, and
`real_slice_manifest.json` should explain why.

Common fixes:

- install FFmpeg / FFprobe
- set `NCUT_FFMPEG_PATH`
- set `NCUT_FFPROBE_PATH`
- keep clip segments within the video duration
- use a plain file name for `ClipPlan.output_name`
