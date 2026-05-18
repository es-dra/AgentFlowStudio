# Phase 13 Product Smoke Report

Date: 2026-05-19

Purpose: verify the current CLI-first technical MVP can run a complete local
Golden Path from source video and ClipPlan to `finished_package_manifest.json`.

## Environment

- Python: 3.12.12
- FFmpeg: available
- FFprobe: available
- Source video: `data/raw/demo_real_video/input.mp4`
- BGM: `data/raw/demo_bgm/bgm.wav`
- ClipPlan: `examples/demo_real_video/clip_plan.json`
- Subtitle transcript: `examples/demo_subtitles/transcript.json`

Local media and generated run artifacts are ignored by git.

## Run Directories

```text
data/processed/runs/golden_path_phase13_real_clips
data/processed/runs/golden_path_phase13_final_video
data/processed/runs/golden_path_phase13_subtitles
data/processed/runs/golden_path_phase13_subtitled_video
data/processed/runs/golden_path_phase13_cover
data/processed/runs/golden_path_phase13_bgm
data/processed/runs/golden_path_phase13_package
```

## Workflow Results

| Step | Workflow | Inspect | Review |
| --- | --- | --- | --- |
| Real clips | `clip_plan_to_real_clips.yaml` | 11 passed / 0 failed / 0 warnings | 15 passed / 0 failed / 0 warnings |
| Final video | `clips_to_final_video.yaml` | 10 passed / 0 failed / 0 warnings | 15 passed / 0 failed / 0 warnings |
| Subtitles | `transcript_to_subtitles.yaml` | 12 passed / 0 failed / 0 warnings | 20 passed / 0 failed / 0 warnings |
| Subtitle burn-in | `final_video_with_subtitles.yaml` | 11 passed / 0 failed / 0 warnings | 19 passed / 0 failed / 0 warnings |
| Cover | `final_video_to_cover.yaml` | 10 passed / 0 failed / 0 warnings | 18 passed / 0 failed / 0 warnings |
| BGM mix | `final_video_with_bgm.yaml` | 13 passed / 0 failed / 0 warnings | 21 passed / 0 failed / 0 warnings |
| Package manifest | `final_video_package.yaml` | 11 passed / 0 failed / 0 warnings | 18 passed / 0 failed / 0 warnings |

## Generated Product Artifacts

```text
data/processed/runs/golden_path_phase13_real_clips/clips/clip_001.mp4
data/processed/runs/golden_path_phase13_final_video/final_video.mp4
data/processed/runs/golden_path_phase13_subtitles/subtitles.srt
data/processed/runs/golden_path_phase13_subtitled_video/final_video_with_subtitles.mp4
data/processed/runs/golden_path_phase13_cover/cover.jpg
data/processed/runs/golden_path_phase13_bgm/final_video_with_bgm.mp4
data/processed/runs/golden_path_phase13_package/finished_package_manifest.json
```

Observed sizes:

```text
clip_001.mp4                         1,938,512 bytes
final_video.mp4                      1,938,635 bytes
subtitles.srt                              225 bytes
final_video_with_subtitles.mp4       2,078,607 bytes
cover.jpg                              131,174 bytes
final_video_with_bgm.mp4             1,936,548 bytes
finished_package_manifest.json           1,521 bytes
```

Final video metadata:

```text
status: succeeded
duration_sec: 10.02322
width: 720
height: 1280
codec: h264
input_clip_count: 1
```

BGM output metadata:

```text
status: succeeded
duration_sec: 10.022005
width: 720
height: 1280
codec: h264
mix_strategy: mix_with_original
bgm_volume: 0.2
original_audio_volume: 1.0
```

Finished package assets:

```text
final_video
subtitled_video
bgm_video
cover_image
review_report
```

## Decision

Product smoke status: passed.

The Phase 13 complete Golden Path produced a real final video, subtitle file,
subtitle-burned video, cover image, BGM-mixed video, package manifest, quality
reports, and review reports with zero failed checks and zero warnings.

## Boundaries

This smoke did not validate:

- real ASR quality
- remote provider behavior
- automatic visual highlight detection
- automatic music selection
- publishing/upload
- Web UI
- physical package directory or zip export
