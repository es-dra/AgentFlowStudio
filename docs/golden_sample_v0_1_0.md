# Golden Sample v0.1.0

This page records the smallest acceptance path for NarratoCut `v0.1.0`.

The repository does not commit real media, generated clips, model cache, or
package outputs. The commands below expect local ignored inputs.

## Required Local Inputs

```text
data/raw/demo_real_video/input.mp4
data/raw/demo_zombie/input.mp4
data/raw/demo_zombie/script.txt
data/raw/demo_bgm/bgm.wav
data/models/faster-whisper/
```

Input bundles:

```text
data/processed/product_acceptance_phase14_1/video_only_local_asr_input.json
data/processed/product_acceptance_phase14_1/video_script_local_asr_input.json
```

## Video-Only Path

```powershell
.venv\Scripts\ncut run-workflow `
  --workflow workflows/video_to_finished_package_local_asr.yaml `
  --input data/processed/product_acceptance_phase14_1/video_only_local_asr_input.json `
  --output data/processed/runs/acceptance/v0_1_0_video_only

.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/acceptance/v0_1_0_video_only
.venv\Scripts\ncut review-run --run-dir data/processed/runs/acceptance/v0_1_0_video_only
.venv\Scripts\ncut package-report --run-dir data/processed/runs/acceptance/v0_1_0_video_only
```

## Video Plus Script Path

```powershell
.venv\Scripts\ncut run-workflow `
  --workflow workflows/video_script_to_finished_package_local_asr.yaml `
  --input data/processed/product_acceptance_phase14_1/video_script_local_asr_input.json `
  --output data/processed/runs/acceptance/v0_1_0_video_script

.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/acceptance/v0_1_0_video_script
.venv\Scripts\ncut review-run --run-dir data/processed/runs/acceptance/v0_1_0_video_script
.venv\Scripts\ncut package-report --run-dir data/processed/runs/acceptance/v0_1_0_video_script
```

## Delivery Readiness

```powershell
.venv\Scripts\ncut delivery-readiness `
  --run-dir data/processed/runs/acceptance/v0_1_0_video_only `
  --run-dir data/processed/runs/acceptance/v0_1_0_video_script `
  --output data/reports/acceptance/v0_1_0_delivery_readiness
```

## Expected Key Artifacts

Each run should contain:

```text
run_manifest.json
trace.json
transcript.json
boundary_signal_manifest.json
candidate_windows.json
highlight_score_report.json
selection_diagnostics.json
highlight_plan.json
clip_plan.json
real_slice_manifest.json
final_video_manifest.json
finished_package_manifest.json
package_report.md
quality_report.json
review_report.json
clips/
final_video.mp4
final_video_with_bgm.mp4
```

The delivery report directory should contain:

```text
delivery_readiness.json
delivery_readiness.md
```

## Acceptance Boundary

This sample verifies local execution, artifact completeness, reviewability, and
handoff readiness. It does not validate mature editorial judgment, platform
publishing performance, Web UI behavior, or multimodal visual understanding.
