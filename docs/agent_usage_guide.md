# Agent Usage Guide

This guide is the operational path for using AgentFlow Studio as the distribution
module of AgentFlow Studio.

AgentFlow Studio `v0.1.0` is local-first. Do not call remote LLMs or remote ASR
unless the user explicitly enables the relevant environment flags.

## 1. Choose A Skill

Start from [`../skills`](../skills/README.md), not from the full workflow list.

- Use `skills/short_highlight_package.skill.yaml` when the user has only a
  source video.
- Use `skills/video_script_highlight_package.skill.yaml` when the user has a
  source video plus script.

The skill file tells you the primary workflow, required inputs, output
artifacts, quality gates, and failure recovery notes.

## 2. Run The Workflow

Video-only local path:

```powershell
.venv\Scripts\afs run-workflow `
  --workflow workflows/video_to_finished_package_local_asr.yaml `
  --input data/processed/product_acceptance_phase14_1/video_only_local_asr_input.json `
  --output data/processed/runs/acceptance/video_only_v0_1_0
```

Video plus script local path:

```powershell
.venv\Scripts\afs run-workflow `
  --workflow workflows/video_script_to_finished_package_local_asr.yaml `
  --input data/processed/product_acceptance_phase14_1/video_script_local_asr_input.json `
  --output data/processed/runs/acceptance/video_script_v0_1_0
```

The input bundle paths above are local acceptance examples. They reference
ignored media and local model cache paths that are not committed to git.

## 3. Inspect, Review, And Refresh The Report

After each run:

```powershell
.venv\Scripts\afs inspect-run --run-dir <run_dir>
.venv\Scripts\afs review-run --run-dir <run_dir>
.venv\Scripts\afs package-report --run-dir <run_dir>
```

Then compare one or more refreshed product runs:

```powershell
.venv\Scripts\afs delivery-readiness `
  --run-dir <video_only_run_dir> `
  --run-dir <video_script_run_dir> `
  --output data/reports/acceptance/v0_1_0_delivery_readiness
```

## 4. Read The Result

Use this order:

1. `run_manifest.json`: artifact index and run metadata.
2. `finished_package_manifest.json`: final package asset index.
3. `package_report.md`: selected clips, reasons, quality gates.
4. `review_report.json`: `quality_level`, `delivery_status`, checks, and
   recommendations.
5. `delivery_readiness.json`: final handoff gate across product runs.

`run_manifest.json` keeps the backward-compatible `artifacts` map and the
expanded `artifact_index` entries. `artifact_index` records path, required
state, and whether the artifact existed when the run manifest was written.

## 5. Failure Handling

| Symptom | Likely cause | Action |
| --- | --- | --- |
| FFmpeg command fails | FFmpeg or FFprobe missing | Run `afs ffmpeg-check --json`, then install FFmpeg or set `NCUT_FFMPEG_PATH` / `NCUT_FFPROBE_PATH`. |
| Local ASR fails | faster-whisper missing or model cache unavailable | Install `faster-whisper`, verify `configs/models.yaml`, or use the prepared local model cache. |
| ASR text quality is weak | Small local model or poor audio | Retry with a better local model, add script input, or treat the result as `needs_review`. |
| No candidates selected | Transcript too sparse or duration gates too strict | Review `candidate_windows.json` and loosen candidate settings in the input bundle. |
| Highlight quality is weak | Text-first deterministic scoring hit its limit | Read `highlight_score_report.json` and `selection_diagnostics.json`; consider OCR/script evidence or manual review. |
| Package asset missing | Upstream media step failed or path was wrong | Read `finished_package_manifest.json`, then inspect the referenced upstream manifest. |
| Delivery readiness warning | Execution passed but quality evidence is risky | Read `delivery_readiness.md` and decide whether to accept, rerun, or manually review clips. |

## 6. Boundaries

This guide does not describe a Web UI, Memory runtime, Router runtime, hosted
API, automatic publishing, or mature viral-selection model. Those are later
AgentFlow Studio layers.
