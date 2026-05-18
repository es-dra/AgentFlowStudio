# Workflows

This directory contains YAML workflow definitions for NarratoCut.

## Available workflows

### `mock_roi_to_script.yaml`

Phase 3 demo workflow:

1. `analyze_hooks`
2. `generate_scripts`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_roi_to_script.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_workflow
```

Generated files are written to the output directory. Runs under `data/processed/` are ignored by git.

`run-workflow` also writes run contract artifacts:

- `manifest.json`
- `run_manifest.json`
- `trace.json`
- `quality_report.json`

### `mock_text_to_slices.yaml`

Phase 6 full mock workflow:

1. `analyze_hooks`
2. `generate_scripts`
3. `generate_clip_plans`
4. `mock_slice`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
```

This workflow writes `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, `.txt` mock clips under `clips/`, and run contract artifacts.

Draft a static workflow plan without executing the workflow:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/reports/workflow_plan.json
```

Inspect the run:

```powershell
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
```

Generate an agent-readable review report:

```powershell
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```

### `real_video_roi_to_clips.yaml`

Phase 9 real-video workflow:

1. `load_roi_config`
2. `load_clip_plan`
3. `probe_video_metadata`
4. `validate_clip_plan`
5. `real_slice_video`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/real_video_roi_to_clips.yaml --input examples/demo_real_video/input.example.json --output data/processed/runs/demo_real_video
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_real_video
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_real_video
```

This workflow requires a local video at `data/raw/demo_real_video/input.mp4`
and local FFmpeg/FFprobe for a successful real slicing run. Missing tools still
produce structured failure artifacts.

### `script_to_highlight_plan.yaml`

Phase 10 script highlight workflow:

1. `load_roi_config`
2. `load_script`
3. `detect_highlights`
4. `rank_highlights_by_roi`
5. `write_highlight_plan`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/script_to_highlight_plan.yaml --input examples/demo_highlight/script_input.example.json --output data/processed/runs/demo_highlight_script
```

This workflow writes a ranked `highlight_plan.json`. It intentionally does not
write `clip_plan.json` because script-only input has no reliable timeline.

### `transcript_to_highlight_clip_plan.yaml`

Phase 10 timestamped transcript workflow:

1. `load_roi_config`
2. `load_transcript`
3. `detect_highlights`
4. `rank_highlights_by_roi`
5. `generate_clip_plan_from_highlights`
6. `write_highlight_plan`
7. `write_clip_plan`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/transcript_to_highlight_clip_plan.yaml --input examples/demo_highlight/transcript_input.example.json --output data/processed/runs/demo_highlight_transcript
```

This workflow writes a ranked `highlight_plan.json` and an executable
`clip_plan.json`. It does not run FFmpeg, stitch clips, add subtitles, add BGM,
or export a final video.

### `video_to_transcript.yaml`

Phase 11.1 video-to-transcript workflow:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_mock`
4. `write_transcript`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_transcript.yaml --input examples/demo_asr/video_to_transcript_input.example.json --output data/processed/runs/demo_video_to_transcript
```

The example uses `audio_extraction_mode: mock` and a fixture-backed mock ASR
provider, so it writes `audio_manifest.json`, `audio/audio.wav`, and
`transcript.json` without requiring real ASR. It does not detect highlights,
generate `clip_plan.json`, run FFmpeg slicing, or inspect video frames.
