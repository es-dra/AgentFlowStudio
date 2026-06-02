# Product Quality Smoke

This document defines how to read a product-level smoke after Phase 14.0B.

The key distinction is:

```text
engineering smoke:
  Did workflows execute and write valid artifacts?

product-quality smoke:
  Does the package expose whether the generated video is actually ready to show?
```

The current Golden Path is expected to pass engineering checks but return
product-quality warnings.

## Current Acceptance Target

For the current local demo:

```text
run-workflow final_video_package -> success
inspect-run final_video_package -> pass, 0 failed, explicit warnings allowed
review-run final_video_package -> warning, 0 failed, explicit warnings expected
```

This means the product test is useful, not that the generated video is good.

## Expected Warning Set

The current demo should surface these known limitations:

```text
product_quality_warning: single_clip_only
product_quality_warning: clip_starts_at_zero_only
product_quality_warning: no_highlight_evidence
product_quality_warning: subtitle_source_video_missing
product_quality_warning: subtitle_duration_exceeds_primary_video
product_quality_warning: bgm_quality_unverified
```

Phase 14.1 also adds a stricter subtitle timeline check:

```text
product_quality_warning: subtitle_timeline_not_final_video
```

This warning is expected when subtitle evidence still uses the source-video
timeline instead of the assembled final-video timeline.

These warnings mean:

- `single_clip_only`: the package contains a one-clip edit, not a multi-moment
  highlight cut.
- `clip_starts_at_zero_only`: all selected clips start at `0s`, so this is not
  proof of automatic highlight selection.
- `no_highlight_evidence`: clip metadata does not prove the cut came from ranked
  highlight evidence.
- `subtitle_source_video_missing`: subtitle metadata is not bound to a source
  video.
- `subtitle_duration_exceeds_primary_video`: subtitle timing is longer than the
  assembled primary video.
- `subtitle_timeline_not_final_video`: subtitle timing has not been remapped to
  the assembled final-video timeline.
- `bgm_quality_unverified`: BGM was technically mixed but not judged for music
  or content fit.

## Evidence Inputs

The package workflow can now accept optional evidence paths:

```json
{
  "final_video_manifest_path": "data/processed/runs/.../final_video_manifest.json",
  "real_slice_manifest_path": "data/processed/runs/.../real_slice_manifest.json",
  "clip_plan_path": "data/processed/runs/.../clip_plan.json",
  "subtitle_manifest_path": "data/processed/runs/.../subtitle_manifest.json",
  "audio_mix_manifest_path": "data/processed/runs/.../audio_mix_manifest.json"
}
```

When these paths are present, `finished_package_manifest.json` records them
under `evidence`, and package review can report product-quality warnings.

## Current Local Baseline

The local Phase 13 Golden Path package was rerun after Phase 14.0B with evidence
paths enabled.

Observed result:

```text
inspect-run:
  Status: pass
  Quality: 11 passed / 0 failed / 6 warnings

review-run:
  Status: warning
  Checks: 17 passed / 0 failed / 7 warnings
```

The extra review warning is the existing `quality_report_passed` roll-up check,
which becomes warning when the quality report itself contains warnings.

## Product-Quality Pass Criteria

A future product-quality pass should reduce or remove these warnings by
improving inputs and upstream capabilities:

- multi-clip ClipPlan with more than one selected moment
- clips that do not all start at `0s`
- auditable highlight evidence in clip segment metadata
- subtitle manifest bound to the same source video or derived final cut
- subtitle duration aligned with primary video duration
- BGM source marked or measured as quality-verified

Until then, the correct product verdict is:

```text
engineering path: pass
product quality: warning / not ready
```

## Phase 14.1 Product Golden Path Target

Phase 14.1 introduces ASR-first product workflows that are intended to clear the
six known warnings when the input evidence is good enough:

```text
video_to_finished_package_real_asr:
  source video
    -> real ASR transcript
    -> transcript highlights
    -> multi-segment ClipPlan
    -> real clips
    -> final_video.mp4
    -> clip-timeline subtitles
    -> verified BGM mix
    -> finished_package_manifest.json

video_script_to_finished_package_real_asr:
  source video + script
    -> real ASR transcript
    -> script highlights
    -> script_highlight_alignment.json
    -> timestamped highlights
    -> multi-segment ClipPlan
    -> real clips
    -> final video package
```

This is still ASR/text-first. It does not perform visual or multimodal video
highlight detection. The package can be considered product-quality acceptable
only when:

- at least two clips are selected
- selected clips do not all start at `0s`
- `clip_plan.json` carries highlight/ranking evidence
- `subtitle_manifest.json` has `timeline: "final_video"` and a source video
- subtitle duration stays within the primary video duration
- `audio_mix_manifest.json` has `quality_verified: true` from local BGM metadata

Real ASR remains explicit opt-in:

```powershell
$env:AFS_ALLOW_REMOTE_ASR="true"
$env:AFS_OPENAI_API_KEY="<your-local-key>"
```

Tests for these workflows continue to mock ASR and FFmpeg, so CI does not call
the network or require real media.
