# Phase 14.4B Elastic Boundary Acceptance

Date: 2026-05-20

## Scope

This acceptance pass re-runs the two local product paths after Phase 14.4A
elastic short-clip boundary generation.

It verifies:

- The source-video-only path still produces a finished package.
- The source-video-plus-script path still produces a finished package.
- Selected clips stay in the short promo range.
- `package_report.md` exposes boundary evidence for selected clips.
- `inspect-run` and `review-run` still pass without warnings.

This pass validates execution and boundary explainability. It does not claim
that deterministic viral selection is editorially final.

## Inputs

Local ignored inputs:

- Video-only source: `data/raw/demo_real_video/input.mp4`
- Video+script source: `data/raw/demo_zombie/input.mp4`
- Video+script text: `data/raw/demo_zombie/script.txt`
- BGM: `data/raw/demo_bgm/bgm.wav`
- Faster-Whisper model cache: `data/models/faster-whisper`

Input bundles:

- `data/processed/product_acceptance_phase14_1/video_only_local_asr_input.json`
- `data/processed/product_acceptance_phase14_1/video_script_local_asr_input.json`

## Runs

### Source Video Only

Run directory:

```text
data/processed/runs/product_acceptance_video_only_phase14_4b
```

Workflow:

```text
workflows/video_to_finished_package_local_asr.yaml
```

Result:

- Candidate windows: 16
- Selected candidates: 4
- Clips: 4
- Clip durations: 4.2s, 4.6s, 4.79s, 4.59s
- Final video duration: 18.222331s
- Boundary evidence:
  - 2 selected native transcript windows
  - 2 selected elastic split windows
- Rejection reasons observed: `duplicate_source_window`, `overlap`,
  `selection_limit`
- Duplicate source-window rejections: 1
- Overlap rejections: 3
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 37 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`

### Source Video Plus Script

Run directory:

```text
data/processed/runs/product_acceptance_video_script_phase14_4b
```

Workflow:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

Result:

- Candidate windows: 18
- Selected candidates: 4
- Clips: 4
- Clip durations: 4.9225s, 4.98s, 5.346667s, 4.785s
- Final video duration: 20.082292s
- Script highlights aligned: 4
- Script highlights skipped: 0
- Boundary evidence:
  - 1 selected native transcript window
  - 3 selected elastic split windows
- Rejection reasons observed: `duplicate_source_window`, `overlap`,
  `selection_limit`
- Duplicate source-window rejections: 4
- Overlap rejections: 2
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 38 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`

## Boundary Evidence Interpretation

`package_report.md` now distinguishes:

- `native_transcript_window`: the selected transcript window was already in the
  short promo range, so no split or trim was needed.
- `elastic_duration_split`: a longer source window was split into balanced
  short candidates.
- `elastic_duration_trim`: a slightly overlong source window was trimmed to the
  target-length core. This was covered by tests but did not appear in the two
  acceptance selections.

This removes the earlier ambiguity where native short windows appeared as
`Boundary: unknown`.

## Acceptance Judgment

Phase 14.4B passes local product acceptance for both prepared material types.

The current product path can produce local finished packages with:

- no remote service dependency,
- 4 selected short clips,
- final duration around 20 seconds,
- quality and review gates passing,
- selected-clip boundary evidence visible in `package_report.md`.

Remaining product risk is editorial quality, not execution closure. The
candidate and scoring layer is still deterministic and text-first. The next
quality slice should add local media boundary evidence such as silence,
loudness, scene boundaries, or keyframe/contact-sheet review.
