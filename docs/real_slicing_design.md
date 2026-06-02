# Real Slicing Design

Phase 8 adds a standalone minimal FFmpeg slicing PoC without replacing the
stable mock workflow.

## Current Boundary

The default workflow path remains mock-only:

```text
scripts.json -> clip_plans.json -> slice_manifest.json + clips/*.txt
```

`mock_slice` writes text placeholders and never reads media, invokes FFmpeg, or
emits `.mp4` files.

Real slicing is available only through the standalone PoC command:

```powershell
.venv\Scripts\afs slice-real --video <local_input.mp4> --clip-plans <clip_plans.json> --output data/outputs/real_slicing_demo
```

## Minimal Real Slicing PoC

Real slicing uses a separate entry point and is not a silent replacement for
`mock_text_to_slices.yaml`.

Expected input:

- a source video path
- validated `ClipPlan` objects loaded from `clip_plans.json`
- one or more `ClipSegment` records with `start_sec` and `end_sec`
- a configured FFmpeg executable

Expected output:

- clipped `.mp4` files
- `real_slice_manifest.json` with status, clip paths, source plan IDs,
  durations, and any per-clip errors

## Time Mapping

For each `ClipSegment`:

```text
start_sec = segment.start_sec
duration_sec = segment.end_sec - segment.start_sec
```

The minimal FFmpeg command contract is:

```text
ffmpeg -y -ss <start_sec> -i <input_video> -t <duration_sec> <output_video>
```

Phase 8 executes this command through `subprocess.run(...)` using a list of
arguments, not a shell string.

## FFmpeg Probe

`check_ffmpeg_available()` calls:

```text
ffmpeg -version
```

The probe returns structured availability information instead of requiring FFmpeg to be installed during tests.

`slice-real` also reports a clear failed manifest when the configured FFmpeg
executable is missing.

## Explicitly Out Of Scope

- subtitle burn-in
- vertical crop or aspect-ratio adaptation
- BGM and multi-track timelines
- cover generation
- encoding optimization
- batch retry policy
- replacing the mock workflow
- generating or committing sample video assets

## Phase 9 Real Workflow Boundary

Phase 9 connects real slicing to the workflow engine as a separate
`real_video` workflow:

```text
ROI settings + input video + ClipPlan
  -> video_metadata.json
  -> clip_plan_validation.json
  -> real_slice_manifest.json
  -> clips/*.mp4, when FFmpeg is available and validation passes
```

The workflow still does not perform ASR, highlight detection, subtitles, BGM,
cover generation, multi-track timelines, or final-video assembly.

Validation hard failures, such as missing FFmpeg, missing duration, unsafe
output names, or segments outside video duration, write reviewable artifacts
before the workflow fails. ROI mismatches are advisory by default.
