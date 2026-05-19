# Phase 14.6 Delivery Readiness Acceptance

Date: 2026-05-20

## Scope

This acceptance pass re-runs the two local product paths after Phase 14.5
selection diagnostics and Phase 14.6 delivery-readiness reporting.

It verifies:

- The video-only path still produces a finished package.
- The video-plus-script path still produces a finished package.
- Each run writes `selection_diagnostics.json`.
- `inspect-run`, `review-run`, and refreshed `package_report.md` are present.
- `delivery-readiness` can summarize both formal runs into release-facing
  JSON and Markdown reports.

This pass validates local execution, artifact completeness, and delivery
readiness reporting. It does not claim deterministic viral selection is
editorially final.

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
data/processed/runs/product_acceptance_video_only_phase14_6
```

Workflow:

```text
workflows/video_to_finished_package_local_asr.yaml
```

Result:

- Candidate windows: 16
- Selected candidates: 4
- Clips: 4
- Clip durations: 4.20s, 4.60s, 4.79s, 4.56s
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
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 39 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`
- Selection diagnostics: `warning`

Selection diagnostics warnings:

- `near_miss_rejected`
- `too_many_selection_limit_rejections`
- `duplicate_source_window_pressure`
- `few_strong_hooks`

### Source Video Plus Script

Run directory:

```text
data/processed/runs/product_acceptance_video_script_phase14_6
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
- Clip source ranges:
  - 3.27s - 8.1925s
  - 21.92s - 26.90s
  - 27.06s - 32.406667s
  - 32.77s - 37.555s
- Final video duration: 20.082292s
- Script highlights aligned: 4
- Script highlights skipped: 0
- Selected boundary strategies:
  - 1 native transcript window
  - 3 elastic split windows
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 40 passed / 0 failed / 0 warnings
- Refreshed report: `package_report.md`
- Selection diagnostics: `warning`

Selection diagnostics warnings:

- `near_miss_rejected`
- `too_many_selection_limit_rejections`
- `duplicate_source_window_pressure`
- `few_strong_hooks`

## Delivery Readiness

Report directory:

```text
data/reports/acceptance/phase14_6_delivery_readiness
```

Command:

```powershell
.venv\Scripts\python.exe -m apps.cli.main delivery-readiness `
  --run-dir data\processed\runs\product_acceptance_video_only_phase14_6 `
  --run-dir data\processed\runs\product_acceptance_video_script_phase14_6 `
  --output data\reports\acceptance\phase14_6_delivery_readiness
```

Result:

- `delivery_readiness.json`: written
- `delivery_readiness.md`: written
- Overall status: `warning`
- Runs: 0 passed / 2 warning / 0 failed
- Failures: none

The readiness result is `warning` rather than `pass` because both selection
diagnostic reports correctly identify weak hook evidence and candidate
competition pressure. The delivery gate therefore confirms execution readiness
while preserving the current selection-quality risk.

## Acceptance Judgment

Phase 14.6 passes execution and artifact-completeness acceptance for both
prepared material types.

The current local-first product path can now produce:

- real finished packages,
- 4 short selected clips,
- final videos around 20 seconds,
- local ASR transcript artifacts,
- candidate windows,
- highlight score reports,
- selection diagnostics,
- package reports,
- quality and review reports,
- a final delivery readiness report.

The current state is suitable for an internal product handoff or CLI/agent
acceptance checkpoint with an explicit warning label.

It should not be presented as fully mature viral-selection quality. The main
remaining issue is selection depth: selected clips are passing mostly on
duration fit, while hook/conflict/payoff evidence remains weak. The next quality
phase should focus on stronger candidate scoring, OCR/visual evidence fusion,
and better differentiation among near-miss candidates.

## Selection-Quality Rerun

After the first Phase 14.6 run, the scoring layer was hardened to recognize
Chinese short-drama and short-promo signals instead of relying mostly on English
keywords and duration fit.

Changes verified in this rerun:

- Chinese hook/conflict/payoff cues now contribute to the deterministic score.
- A lightweight specificity signal helps concrete story beats outrank generic
  duration-fit candidates.
- Repeated subwindows from the same source window receive a small later-window
  penalty, while the final `highlight_plan.json` remains ordered by source
  timeline for natural assembly.
- Selection diagnostics still report near misses, but only raise readiness
  warnings for actionable pressure rather than expected overlap or duplicate
  pruning.

### Rerun Directories

```text
data/processed/runs/product_acceptance_video_only_phase14_6_selection_quality
data/processed/runs/product_acceptance_video_script_phase14_6_selection_quality
```

Delivery readiness report:

```text
data/reports/acceptance/phase14_6_selection_quality
```

### Rerun Results

Video-only result:

- Candidate windows: 16
- Selected candidates: 4
- Clip durations: 4.20s, 4.60s, 4.79s, 5.14s
- Final video duration: 18.788998s
- Selected reasons now include `strong_hook`, `conflict`,
  `payoff_or_reversal`, `specificity`, and `duration_fit`.
- `selection_diagnostics.json`: 0 warnings
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 39 passed / 0 failed / 0 warnings

Video+script result:

- Candidate windows: 18
- Selected candidates: 4
- Clip durations: 4.9225s, 4.98s, 4.785s, 5.683333s
- Final video duration: 20.419887s
- Selected reasons now include `strong_hook`, `conflict`,
  `payoff_or_reversal`, `specificity`, and `duration_fit`.
- `selection_diagnostics.json`: 0 warnings
- `inspect-run`: pass, 8 passed / 0 failed / 0 warnings
- `review-run`: passed, 40 passed / 0 failed / 0 warnings

Delivery readiness rerun result:

- Overall status: `pass`
- Runs: 2 passed / 0 warning / 0 failed
- Failures: none

This rerun closes the immediate visible selection-quality warnings from the
first Phase 14.6 pass. It still does not claim mature viral judgment; the
selection layer remains deterministic and text-first. The next quality work
should focus on OCR/visual/audio evidence fusion and stronger editorial
boundary selection.
