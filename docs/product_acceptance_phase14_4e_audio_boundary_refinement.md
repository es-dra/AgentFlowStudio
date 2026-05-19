# Phase 14.4E Audio Boundary Refinement Acceptance

Date: 2026-05-20

## Scope

This acceptance pass re-runs the two local product paths after Phase 14.4D
audio-boundary cut-point refinement.

It verifies:

- The source-video-only path still produces a finished package.
- The source-video-plus-script path still produces a finished package.
- Selected clips stay in the short promo range.
- Audio boundary refinement can affect real selected clip timestamps when a
  nearby high-confidence boundary exists.
- `package_report.md` explains whether audio refinement was applied.
- `inspect-run` and `review-run` pass without warnings.

This pass validates local execution, boundary refinement, and report
readability. It does not claim deterministic viral selection is editorially
final.

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
data/processed/runs/product_acceptance_video_only_phase14_4e
```

Workflow:

```text
workflows/video_to_finished_package_local_asr.yaml
```

Result:

- Boundary signal manifest: `succeeded`
- Boundary points: 4
- Candidate windows: 16
- Selected candidates: 4
- Clips: 4
- Clip durations: 4.2s, 4.6s, 4.79s, 4.56s
- Clip source ranges:
  - 1.28s - 5.48s
  - 5.48s - 10.08s
  - 27.28s - 32.07s
  - 32.50s - 37.06s
- Final video duration: 18.189323s
- Selected boundary strategies:
  - 2 native transcript windows
  - 1 elastic split window
  - 1 audio-boundary-refined elastic split window
- Audio refinement applied:
  - `cand_008`: 32.47s - 37.06s -> 32.50s - 37.06s, start boundary only
- Rejection reasons observed:
  - `duplicate_source_window`: 1
  - `overlap`: 3
  - `selection_limit`: 8
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 38 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`

### Source Video Plus Script

Run directory:

```text
data/processed/runs/product_acceptance_video_script_phase14_4e
```

Workflow:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

Result:

- Boundary signal manifest: `succeeded`
- Boundary points: 20
- Candidate windows: 18
- Selected candidates: 4
- Clips: 4
- Clip durations: 4.9225s, 4.98s, 5.346667s, 4.785s
- Clip source ranges:
  - 3.27s - 8.1925s
  - 21.92s - 26.9s
  - 27.06s - 32.406667s
  - 32.77s - 37.555s
- Final video duration: 20.082292s
- Script highlights aligned: 4
- Script highlights skipped: 0
- Selected boundary strategies:
  - 1 native transcript window
  - 3 elastic split windows
- Audio refinement applied: none selected in this run
- Rejection reasons observed:
  - `duplicate_source_window`: 4
  - `overlap`: 2
  - `selection_limit`: 8
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 39 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`

## Report Readability Fix

This acceptance pass exposed a reporting problem: `package_report.md` displayed
the nearest audio boundary even when it was many seconds away from the selected
clip boundary. The JSON evidence was technically accurate because it included
`distance_sec`, but the Markdown report was too noisy for human acceptance.

The report now displays nearby audio boundary evidence only when the boundary is
within 1.0 second of the clip boundary. Otherwise it shows:

```text
Audio boundary: not nearby
```

This keeps the machine evidence intact while making the human report less
misleading.

## Acceptance Judgment

Phase 14.4E passes local product acceptance for both prepared material types.

The current product path can produce local finished packages with:

- no remote service dependency,
- 4 selected short clips,
- final duration around 20 seconds,
- audio boundary signals generated locally,
- safe audio-boundary refinement applied when a selected candidate has a nearby
  high-confidence boundary,
- `package_report.md` explaining boundary strategy and refinement status,
- quality and review gates passing without warnings.

Remaining product risk is still editorial selection quality. Audio boundary
refinement improves cut-point naturalness when usable local evidence exists, but
it does not replace stronger hook/conflict/payoff scoring, visual evidence, or
human editorial review.
