# Real Slicing Design

Phase 7 prepares NarratoCut for future FFmpeg-based slicing without replacing the stable mock workflow.

## Current Boundary

The current slicing path is mock-only:

```text
scripts.json -> clip_plans.json -> slice_manifest.json + clips/*.txt
```

`mock_slice` writes text placeholders and never reads media, invokes FFmpeg, or emits `.mp4` files.

## Future Real Slicing Contract

Real slicing should use a separate entry point and workflow, not a silent replacement for `mock_text_to_slices.yaml`.

Expected input:

- a source video path
- a validated `ClipPlan`
- one or more `ClipSegment` records with `start_sec` and `end_sec`
- a configured FFmpeg executable

Expected output:

- clipped `.mp4` files
- a slice manifest with status, clip paths, source plan IDs, durations, and any per-clip errors

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

Phase 7 only builds this command. It does not execute FFmpeg.

## FFmpeg Probe

`check_ffmpeg_available()` calls:

```text
ffmpeg -version
```

The probe returns structured availability information instead of requiring FFmpeg to be installed during tests.

## Explicitly Out Of Scope

- subtitle burn-in
- vertical crop or aspect-ratio adaptation
- BGM and multi-track timelines
- cover generation
- encoding optimization
- batch retry policy
- replacing the mock workflow
