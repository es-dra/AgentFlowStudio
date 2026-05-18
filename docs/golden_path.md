# Phase 13 Complete Golden Path

This document defines a local product smoke for the current CLI-first technical
MVP. It verifies that the Phase 12 and Phase 13 workflows can produce a
finished package manifest from local ignored media.

The Golden Path is not a consumer one-click workflow yet. It is a developer
acceptance path for the current artifact-driven product surface.

For the Phase 14.0B quality-warning baseline, see
[`docs/product_quality_smoke.md`](product_quality_smoke.md).

## Goal

Run this path:

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

## Local Requirements

Required local tools:

- Python 3.12
- installed editable NarratoCut environment
- FFmpeg and FFprobe available on `PATH`, or configured locally

Required local ignored media:

```text
data/raw/demo_real_video/input.mp4
data/raw/demo_bgm/bgm.wav
```

The repository does not commit these media files.

## Recommended Run Names

Use a dated or stable local run prefix. Example:

```text
data/processed/runs/golden_path_phase13_real_clips
data/processed/runs/golden_path_phase13_final_video
data/processed/runs/golden_path_phase13_subtitles
data/processed/runs/golden_path_phase13_subtitled_video
data/processed/runs/golden_path_phase13_cover
data/processed/runs/golden_path_phase13_bgm
data/processed/runs/golden_path_phase13_package
```

Input bundles can be written under `data/processed/runs/` because that location
is ignored by git.

## Step 1: ClipPlan To Real Clips

Create a local input bundle:

```json
{
  "video_path": "data/raw/demo_real_video/input.mp4",
  "clip_plan_path": "examples/demo_real_video/clip_plan.json",
  "output_clips_dir": "clips"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/clip_plan_to_real_clips.yaml --input data/processed/runs/golden_path_phase13_clip_plan_to_real_clips_input.json --output data/processed/runs/golden_path_phase13_real_clips
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_real_clips
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_real_clips
```

Expected key artifacts:

```text
video_metadata.json
clip_plan.json
clip_plan_validation.json
real_slice_manifest.json
clips/
quality_report.json
review_report.json
```

## Step 2: Real Clips To Final Video

Create a local input bundle:

```json
{
  "real_slice_manifest_path": "data/processed/runs/golden_path_phase13_real_clips/real_slice_manifest.json",
  "output_name": "final_video.mp4"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/clips_to_final_video.yaml --input data/processed/runs/golden_path_phase13_clips_to_final_video_input.json --output data/processed/runs/golden_path_phase13_final_video
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_final_video
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_final_video
```

Expected key artifacts:

```text
real_slice_manifest.json
assembly_plan.json
concat_list.txt
final_video.mp4
final_video_manifest.json
quality_report.json
review_report.json
```

## Step 3: Transcript To Subtitles

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/transcript_to_subtitles.yaml --input examples/demo_subtitles/transcript_to_subtitles_input.example.json --output data/processed/runs/golden_path_phase13_subtitles
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_subtitles
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_subtitles
```

Expected key artifacts:

```text
subtitles.srt
subtitle_manifest.json
quality_report.json
review_report.json
```

## Step 4: Burn Subtitles Into Final Video

Create a local input bundle:

```json
{
  "final_video_path": "data/processed/runs/golden_path_phase13_final_video/final_video.mp4",
  "subtitles_path": "data/processed/runs/golden_path_phase13_subtitles/subtitles.srt",
  "output_name": "final_video_with_subtitles.mp4"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_with_subtitles.yaml --input data/processed/runs/golden_path_phase13_final_video_with_subtitles_input.json --output data/processed/runs/golden_path_phase13_subtitled_video
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_subtitled_video
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_subtitled_video
```

Expected key artifacts:

```text
final_video_with_subtitles.mp4
subtitle_burn_manifest.json
quality_report.json
review_report.json
```

## Step 5: Export Cover

Create a local input bundle:

```json
{
  "final_video_path": "data/processed/runs/golden_path_phase13_final_video/final_video.mp4",
  "cover_time_sec": 1.0,
  "output_name": "cover.jpg"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_to_cover.yaml --input data/processed/runs/golden_path_phase13_final_video_to_cover_input.json --output data/processed/runs/golden_path_phase13_cover
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_cover
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_cover
```

Expected key artifacts:

```text
cover.jpg
cover_manifest.json
quality_report.json
review_report.json
```

## Step 6: Mix Local BGM

Create a local input bundle:

```json
{
  "final_video_path": "data/processed/runs/golden_path_phase13_final_video/final_video.mp4",
  "bgm_path": "data/raw/demo_bgm/bgm.wav",
  "bgm_volume": 0.2,
  "original_audio_volume": 1.0,
  "mix_strategy": "mix_with_original",
  "output_name": "final_video_with_bgm.mp4"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_with_bgm.yaml --input data/processed/runs/golden_path_phase13_final_video_with_bgm_input.json --output data/processed/runs/golden_path_phase13_bgm
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_bgm
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_bgm
```

Expected key artifacts:

```text
final_video_with_bgm.mp4
audio_mix_manifest.json
quality_report.json
review_report.json
```

## Step 7: Write Finished Package Manifest

Create a local input bundle:

```json
{
  "package_id": "golden_path_phase13",
  "final_video_path": "data/processed/runs/golden_path_phase13_final_video/final_video.mp4",
  "subtitled_video_path": "data/processed/runs/golden_path_phase13_subtitled_video/final_video_with_subtitles.mp4",
  "bgm_video_path": "data/processed/runs/golden_path_phase13_bgm/final_video_with_bgm.mp4",
  "cover_path": "data/processed/runs/golden_path_phase13_cover/cover.jpg",
  "review_report_path": "data/processed/runs/golden_path_phase13_final_video/review_report.json",
  "final_video_manifest_path": "data/processed/runs/golden_path_phase13_final_video/final_video_manifest.json",
  "real_slice_manifest_path": "data/processed/runs/golden_path_phase13_real_clips/real_slice_manifest.json",
  "clip_plan_path": "data/processed/runs/golden_path_phase13_real_clips/clip_plan.json",
  "subtitle_manifest_path": "data/processed/runs/golden_path_phase13_subtitles/subtitle_manifest.json",
  "audio_mix_manifest_path": "data/processed/runs/golden_path_phase13_bgm/audio_mix_manifest.json"
}
```

Run:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_package.yaml --input data/processed/runs/golden_path_phase13_package_input.json --output data/processed/runs/golden_path_phase13_package
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/golden_path_phase13_package
.venv\Scripts\ncut review-run --run-dir data/processed/runs/golden_path_phase13_package
```

Expected key artifacts:

```text
finished_package_manifest.json
quality_report.json
review_report.json
```

## Acceptance Criteria

A Golden Path smoke passes when:

- each workflow returns `success`
- each `inspect-run` has `0 failed`
- each `review-run` has `0 failed`
- `final_video_package` review may return `warning` when product-quality
  evidence is present but the current demo is not product-ready
- warnings are allowed only when they are explicit and non-blocking, such as
  known FFmpeg DTS warnings, duration drift warnings, or product-quality smoke
  warnings
- no generated media or run artifacts are committed to git

## Product-Quality Smoke Warnings

The Golden Path is an engineering smoke first. When the package input declares
quality evidence paths, `review-run` also reports product-quality warnings for
known demo limitations.

Current demo limitations that should be surfaced as warnings:

- `single_clip_only`: the demo ClipPlan produces one clip, not a multi-moment
  edit
- `clip_starts_at_zero_only`: the demo cut starts at `0s`, so it should not be
  mistaken for automatic highlight selection
- `no_highlight_evidence`: the package cannot prove that clip choices came from
  ranked highlights
- `subtitle_source_video_missing`: the demo subtitle transcript is not tied to
  the source video
- `subtitle_duration_exceeds_primary_video`: subtitle timing may exceed the
  assembled video duration
- `bgm_quality_unverified`: local BGM was mixed successfully but not judged for
  musical/content fit

For product-quality acceptance, the goal is not `0 warnings`; the goal is that
engineering failures are zero and quality limitations are explicit.

## Known Boundaries

This smoke does not verify:

- real ASR quality
- remote provider behavior
- automatic visual highlight detection
- music recommendation
- publishing/upload
- Web UI
- physical package directory or zip export
