# Phase 14 Local ASR Product Acceptance

Date: 2026-05-19

## Scope

This acceptance pass verifies the local-ASR product Golden Path after adding
`faster-whisper` support and Chinese script-to-transcript alignment hardening.

It covers two cases:

1. Source video only.
2. Source video plus script.

The goal is product-chain closure, not final editorial approval.

## Local Inputs

Ignored local media:

- Video-only source: `data/raw/demo_real_video/input.mp4`
- Video+script source: `data/raw/demo_zombie/input.mp4`
- Video+script text: `data/raw/demo_zombie/script.txt`
- BGM: `data/raw/demo_bgm/bgm.wav`

Committed example workflow inputs:

- `examples/demo_asr/video_to_finished_package_local_asr_input.example.json`
- `examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json`

Local acceptance input bundles:

- `data/processed/product_acceptance_phase14_1/video_only_local_asr_input.json`
- `data/processed/product_acceptance_phase14_1/video_script_local_asr_input.json`

## ASR Settings

Local ASR uses:

- Provider: `faster-whisper`
- Model: `small`
- Device: `cpu`
- Compute type: `int8`
- VAD filter: enabled
- Model cache: `data/models/faster-whisper`

No API key is required. No remote ASR opt-in is required.

## Acceptance Runs

### Phase 14.2D Short Highlight Product Path

Latest run directories:

```text
data/processed/runs/product_acceptance_video_only_phase14_2d
data/processed/runs/product_acceptance_video_script_phase14_2d
```

These runs use the Phase 14.2D scoring-first product path:

```text
local ASR transcript
  -> candidate_windows.json
  -> highlight_score_report.json
  -> highlight_plan.json
  -> clip_plan.json
  -> real clips
  -> final package
```

Source video only result:

- Clips: 4
- Clip durations: 4.2s, 4.6s, 5.0s, 5.0s
- Final video duration: 18.82322s
- Duplicate source-window rejections: 1
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 36 passed / 0 failed / 0 warnings

Source video plus script result:

- Clips: 4
- Clip durations: 5.0s, 5.0s, 4.98s, 5.0s
- Final video duration: 20.00322s
- Script highlights aligned: 4
- Script highlights skipped: 0
- Duplicate source-window rejections: 7
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 37 passed / 0 failed / 0 warnings

Product acceptance judgment: Phase 14.2D fixes the earlier overlong clip/final
video failure. The current local product outputs are now shaped like short promo
cuts. Editorial selection quality is still deterministic and text-first; OCR,
visual, and audio evidence remain future improvements.

### Source Video Only

Run directory:

```text
data/processed/runs/product_acceptance_video_only_local_asr_small
```

Workflow:

```text
workflows/video_to_finished_package_local_asr.yaml
```

Result:

- Transcript segments: 27
- Highlights: 4
- Clips: 4
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 34 passed / 0 failed / 0 warnings
- Final output: `final_video_with_bgm.mp4`
- Package manifest: `finished_package_manifest.json`

### Source Video Plus Script

Run directory:

```text
data/processed/runs/product_acceptance_video_script_local_asr_small_window_003
```

Workflow:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

Result:

- Transcript segments: 8
- Script highlights aligned: 4
- Script highlights skipped: 0
- Clips: 4
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 35 passed / 0 failed / 0 warnings
- Final output: `final_video_with_bgm.mp4`
- Package manifest: `finished_package_manifest.json`

Alignment confidence values:

```text
0.03125, 0.107143, 0.034483, 0.04918
```

These values are acceptable for this local small-model smoke but should not be
treated as final editorial confidence.

## Cleanup

Removed stale Phase 14.1 acceptance runs:

- `product_acceptance_video_only`
- `product_acceptance_video_script`
- `product_acceptance_video_only_local_asr`
- `product_acceptance_video_script_local_asr`
- `product_acceptance_video_script_local_asr_low_conf`
- `product_acceptance_video_script_local_asr_small`
- `product_acceptance_video_script_local_asr_small_window`

Removed stale remote-ASR acceptance inputs:

- `video_only_input.json`
- `video_script_input.json`

Kept the two latest passing local-ASR acceptance runs and the local model cache.

## Current Product Judgment

The product chain is closed for both target cases:

```text
video/script
  -> local ASR transcript
  -> highlight plan
  -> clip plan
  -> real clips
  -> final video
  -> clip-timeline subtitles
  -> BGM mix
  -> finished package
  -> inspect/review
```

This supports product workflow acceptance.

It does not yet prove mature "viral clip" quality. Highlight selection is still
MVP-level and mostly transcript/script driven. The next quality step should add
an explicit highlight scoring and editorial review layer before slicing.
