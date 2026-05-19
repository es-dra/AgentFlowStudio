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

### `clip_plan_to_real_clips.yaml`

Phase 12.1 primary execution workflow:

1. `load_video`
2. `load_clip_plan`
3. `probe_video_metadata`
4. `validate_clip_plan`
5. `real_slice_video`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/clip_plan_to_real_clips.yaml --input examples/demo_slicing/clip_plan_to_real_clips_input.example.json --output data/reports/phase_12_1_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/clip_plan_to_real_clips.yaml --input examples/demo_slicing/clip_plan_to_real_clips_input.example.json --output data/processed/runs/demo_clip_plan_to_real_clips
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_clip_plan_to_real_clips
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_clip_plan_to_real_clips
```

The example expects a local ignored video at
`data/raw/demo_slicing/input.mp4`; the repository does not include real media.
The workflow writes `clip_plan.json`, `video_metadata.json`,
`clip_plan_validation.json`, `real_slice_manifest.json`, real `.mp4` clips
under `clips/`, and run contract artifacts.

This workflow is the Phase 12.1 execution boundary: it runs an existing
`clip_plan.json` against a source video. It does not run ASR, detect
highlights, generate a new clip plan, concatenate clips, add subtitles, add
BGM, create covers, call remote providers, or export `final_video.mp4`.

### `video_to_real_clips.yaml`

Phase 12.1B composition smoke workflow:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_mock`
4. `write_transcript`
5. `load_roi_config`
6. `detect_highlights`
7. `rank_highlights_by_roi`
8. `generate_clip_plan_from_highlights`
9. `write_highlight_plan`
10. `write_clip_plan`
11. `probe_video_metadata`
12. `validate_clip_plan`
13. `real_slice_video`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/video_to_real_clips.yaml --input examples/demo_asr/video_to_real_clips_input.example.json --output data/reports/video_to_real_clips_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_real_clips.yaml --input examples/demo_asr/video_to_real_clips_input.example.json --output data/processed/runs/demo_video_to_real_clips
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_to_real_clips
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_to_real_clips
```

This workflow composes the Phase 11 mock-ASR planning chain with the Phase
12.1 ClipPlan execution workflow. It writes `audio_manifest.json`,
`transcript.json`, `highlight_plan.json`, `clip_plan.json`,
`video_metadata.json`, `clip_plan_validation.json`,
`real_slice_manifest.json`, and real `.mp4` clips under `clips/`.

It is intentionally a composition smoke path. It does not use real ASR, inspect
video frames, concatenate clips, add subtitles, add BGM, create covers, call
remote providers, or export `final_video.mp4`.

### `clips_to_final_video.yaml`

Phase 12.2 simple assembly workflow:

1. `load_real_slice_manifest`
2. `generate_assembly_plan`
3. `concat_clips`
4. `probe_final_video`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/clips_to_final_video.yaml --input examples/demo_assembly/clips_to_final_video_input.example.json --output data/reports/clips_to_final_video_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/clips_to_final_video.yaml --input examples/demo_assembly/clips_to_final_video_input.example.json --output data/processed/runs/demo_clips_to_final_video
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_clips_to_final_video
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_clips_to_final_video
```

This workflow consumes an existing `real_slice_manifest.json` and its `clips/`
directory from a prior real slicing run. It writes `assembly_plan.json`,
`concat_list.txt`, `final_video_manifest.json`, and `final_video.mp4`.
For inspect/review, `final_video_manifest.json` is the source of truth for the
generated video path.

It is intentionally a simple FFmpeg concat path. It does not run ASR, detect
highlights, slice source videos, burn subtitles, add BGM, add transitions,
create covers, call remote providers, or provide a Web UI.

### `transcript_to_subtitles.yaml`

Phase 13.2 basic subtitle export workflow:

1. `load_transcript`
2. `write_subtitles`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/transcript_to_subtitles.yaml --input examples/demo_subtitles/transcript_to_subtitles_input.example.json --output data/reports/transcript_to_subtitles_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/transcript_to_subtitles.yaml --input examples/demo_subtitles/transcript_to_subtitles_input.example.json --output data/processed/runs/demo_transcript_to_subtitles
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_transcript_to_subtitles
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_transcript_to_subtitles
```

This workflow consumes an existing timestamped `transcript.json` and writes
`subtitles.srt` plus `subtitle_manifest.json`. `inspect-run` and `review-run`
check subtitle file presence, manifest status, cue count alignment, cue time
ranges, monotonic ordering, and non-empty cue text.

It intentionally exports subtitle text only. It does not burn subtitles into
video, run FFmpeg, re-encode media, add BGM, add transitions, create covers,
call remote providers, or export a new final video.

### `final_video_with_subtitles.yaml`

Phase 13.3 subtitle burn-in workflow:

1. `burn_subtitles`
2. `probe_subtitle_burn`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/final_video_with_subtitles.yaml --input examples/demo_subtitles/final_video_with_subtitles_input.example.json --output data/reports/final_video_with_subtitles_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_with_subtitles.yaml --input examples/demo_subtitles/final_video_with_subtitles_input.example.json --output data/processed/runs/demo_final_video_with_subtitles
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_final_video_with_subtitles
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_final_video_with_subtitles
```

This workflow consumes an existing `final_video.mp4` and an existing
`subtitles.srt`, then writes `final_video_with_subtitles.mp4` plus
`subtitle_burn_manifest.json`. `inspect-run` and `review-run` check manifest
status, FFmpeg return code, output video existence, non-empty output file size,
video stream presence when FFprobe is available, and known FFmpeg warning
classification.

The example references a generated ignored final video under `data/processed/`;
the repository does not include real media. It intentionally does not generate
subtitles, regenerate final assembly, slice videos, add BGM, add transitions,
create covers, call remote providers, inspect video frames, or provide a Web
UI.

### `final_video_to_cover.yaml`

Phase 13.4 cover export workflow:

1. `export_cover`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/final_video_to_cover.yaml --input examples/demo_cover/final_video_to_cover_input.example.json --output data/reports/final_video_to_cover_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_to_cover.yaml --input examples/demo_cover/final_video_to_cover_input.example.json --output data/processed/runs/demo_final_video_to_cover
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_final_video_to_cover
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_final_video_to_cover
```

This workflow consumes an existing `final_video.mp4`, extracts one frame with
FFmpeg, and writes `cover.jpg` plus `cover_manifest.json`. `inspect-run` and
`review-run` check manifest status, FFmpeg command/return code, cover file
presence, non-empty cover file size, and safe relative output paths.

The example references a generated ignored final video under `data/processed/`;
the repository does not include real media. It intentionally does not select an
optimal highlight frame, generate cover templates, add title overlays, add BGM,
add transitions, regenerate final assembly, call remote providers, inspect video
frames for quality, or provide a Web UI.

### `final_video_with_bgm.yaml`

Phase 13.5 local BGM mix workflow:

1. `mix_bgm`
2. `probe_bgm_mix`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/final_video_with_bgm.yaml --input examples/demo_bgm/final_video_with_bgm_input.example.json --output data/reports/final_video_with_bgm_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_with_bgm.yaml --input examples/demo_bgm/final_video_with_bgm_input.example.json --output data/processed/runs/demo_final_video_with_bgm
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_final_video_with_bgm
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_final_video_with_bgm
```

This workflow consumes an existing `final_video.mp4` and a local BGM audio file,
then writes `final_video_with_bgm.mp4` plus `audio_mix_manifest.json`.
`inspect-run` and `review-run` check manifest status, FFmpeg command/return
code, safe relative output path, output video presence, non-empty output size,
video stream presence when FFprobe is available, known FFmpeg warnings, and
duration drift.

`bgm_volume` and `original_audio_volume` are bounded to `0..1`. The default
`mix_strategy` is `mix_with_original`; use `bgm_only` only when the input final
video has no original audio stream.

The example references generated or local ignored media under `data/processed/`
and `data/raw/`; the repository does not include real video or music assets. It
intentionally does not select music, manage licensing, detect beats, add fades,
add transitions, regenerate final assembly, call remote providers, or provide a
Web UI.

### `final_video_package.yaml`

Phase 13.7 finished package manifest workflow:

1. `write_finished_package`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/final_video_package.yaml --input examples/demo_package/final_video_package_input.example.json --output data/reports/final_video_package_workflow_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/final_video_package.yaml --input examples/demo_package/final_video_package_input.example.json --output data/processed/runs/demo_final_video_package
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_final_video_package
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_final_video_package
```

This workflow consumes paths to existing final video artifacts and writes
`finished_package_manifest.json`. The final video is required; subtitle-burned
video, BGM-mixed video, cover image, and review report paths are optional.
`inspect-run` and `review-run` check package manifest status and declared asset
existence.

The example references generated ignored artifacts under `data/processed/`; the
repository does not include real media. This workflow indexes artifacts only. It
does not copy files, upload files, regenerate videos, burn subtitles, mix BGM,
export covers, call remote providers, or provide a Web UI.

### `video_to_finished_package_real_asr.yaml`

Phase 14.1 ASR-first product Golden Path for the source-video-only case:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_openai_compatible`
4. `write_transcript`
5. `load_roi_config`
6. `detect_highlights`
7. `rank_highlights_by_roi`
8. `generate_clip_plan_from_highlights`
9. `write_highlight_plan`
10. `write_clip_plan`
11. `probe_video_metadata`
12. `validate_clip_plan`
13. `real_slice_video`
14. `generate_assembly_plan`
15. `concat_clips`
16. `probe_final_video`
17. `write_clip_timeline_subtitles`
18. `mix_bgm`
19. `probe_bgm_mix`
20. `write_finished_package`

Example:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
$env:NARRATOCUT_OPENAI_API_KEY="<your-local-key>"
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_finished_package_real_asr.yaml --input examples/demo_asr/video_to_finished_package_real_asr_input.example.json --output data/processed/runs/demo_video_to_finished_package_real_asr
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_to_finished_package_real_asr
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_to_finished_package_real_asr
```

This workflow uses ASR transcript text as the highlight signal. It does not
inspect video frames or run multimodal highlight detection. The BGM path must be
local, ignored media, and `bgm_metadata_path` should point to local metadata
with `quality_verified: true` when the music has actually been reviewed.

### `video_to_finished_package_local_asr.yaml`

Local-ASR variant of the Phase 14.1 source-video-only Golden Path. It has the
same product chain as `video_to_finished_package_real_asr.yaml`, but step 3 is
`transcribe_audio_faster_whisper` instead of a remote OpenAI-compatible ASR
call.

Example:

```powershell
.venv\Scripts\python.exe -m pip install faster-whisper
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_finished_package_local_asr.yaml --input examples/demo_asr/video_to_finished_package_local_asr_input.example.json --output data/processed/runs/demo_video_to_finished_package_local_asr
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_to_finished_package_local_asr
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_to_finished_package_local_asr
```

The committed example uses `asr_model: small`, `asr_device: cpu`, and
`asr_compute_type: int8` for better Chinese transcript quality on roughly
one-minute local smokes without requiring a strong GPU. Use `tiny` for a faster
engineering-only smoke, but expect weaker highlight quality. The first run may
download model files into the configured local cache.

### `video_script_to_finished_package_real_asr.yaml`

Phase 14.1 ASR-first product Golden Path for the source-video-plus-script case.
It first detects script highlights, then aligns those script highlights to ASR
transcript segments and writes `script_highlight_alignment.json` before slicing
and packaging.

Example:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
$env:NARRATOCUT_OPENAI_API_KEY="<your-local-key>"
.venv\Scripts\ncut run-workflow --workflow workflows/video_script_to_finished_package_real_asr.yaml --input examples/demo_asr/video_script_to_finished_package_real_asr_input.example.json --output data/processed/runs/demo_video_script_to_finished_package_real_asr
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_script_to_finished_package_real_asr
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_script_to_finished_package_real_asr
```

Low-confidence script-to-transcript alignments are skipped and reported in the
alignment manifest. This workflow does not do visual semantic search; the ASR
transcript is the source of video timestamps.

### `video_script_to_finished_package_local_asr.yaml`

Local-ASR variant of the Phase 14.1 source-video-plus-script Golden Path. It
uses `transcribe_audio_faster_whisper`, then aligns script highlights to local
ASR transcript segments before slicing and packaging.

Example:

```powershell
.venv\Scripts\python.exe -m pip install faster-whisper
.venv\Scripts\ncut run-workflow --workflow workflows/video_script_to_finished_package_local_asr.yaml --input examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json --output data/processed/runs/demo_video_script_to_finished_package_local_asr
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_script_to_finished_package_local_asr
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_script_to_finished_package_local_asr
```

For local small-model Chinese ASR, the example uses a lower
`alignment_min_confidence` because short ASR segments and imperfect transcript
text make exact lexical overlap sparse. The aligner still records confidence,
matched segment ids, and skipped highlights in `script_highlight_alignment.json`.

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

### `transcript_to_candidate_windows.yaml`

Phase 14.2A transcript candidate-window workflow:

1. `load_transcript`
2. `generate_candidate_windows`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/transcript_to_candidate_windows.yaml --input examples/demo_highlight/transcript_candidate_windows_input.example.json --output data/reports/transcript_candidate_windows_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/transcript_to_candidate_windows.yaml --input examples/demo_highlight/transcript_candidate_windows_input.example.json --output data/processed/runs/demo_transcript_candidate_windows
```

This workflow writes `candidate_windows.json` from adjacent transcript segment
windows. It is the Phase 14.2A selection-quality input artifact: later scoring
can evaluate many candidate windows instead of selecting highlights directly
from raw transcript segments. The manifest records the transcript
`content_channel` when available, so the same candidate layer can later consume
ASR transcripts, OCR subtitle transcripts, or fused transcripts. It does not
score candidates, write `highlight_plan.json`, write `clip_plan.json`, run
FFmpeg, call an LLM, inspect video frames, or export a final video.

### `video_subtitle_ocr_to_highlight_plan.yaml`

Phase 14.2B/C OCR-subtitle timeline and candidate scoring workflow:

1. `load_video`
2. `build_ocr_transcript`
3. `write_ocr_transcript`
4. `generate_candidate_windows`
5. `score_candidate_windows`
6. `write_highlight_score_report`
7. `write_highlight_plan`

Example:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/video_subtitle_ocr_to_highlight_plan.yaml --input examples/demo_ocr/video_subtitle_ocr_to_highlight_plan_input.example.json --output data/reports/video_subtitle_ocr_to_highlight_plan.json
.venv\Scripts\ncut run-workflow --workflow workflows/video_subtitle_ocr_to_highlight_plan.yaml --input examples/demo_ocr/video_subtitle_ocr_to_highlight_plan_input.example.json --output data/processed/runs/demo_video_subtitle_ocr_to_highlight_plan
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_subtitle_ocr_to_highlight_plan
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_subtitle_ocr_to_highlight_plan
```

The committed example expects a local ignored video at
`data/raw/demo_ocr/source.mp4` and consumes the committed frame-level OCR
fixture at `examples/demo_ocr/ocr_frames_fixture.json`. The workflow writes
`ocr_transcript.json`, `ocr_transcript_manifest.json`,
`candidate_windows.json`, `highlight_score_report.json`, and
`highlight_plan.json`.

This is an offline product skeleton for OCR evidence and explainable highlight
selection. It does not extract frames, run a real OCR engine, call remote
providers, slice media, generate `clip_plan.json`, add subtitles/BGM/covers, or
provide a Web UI. A future local OCR provider can feed the same frame-result
contract.

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

Use `audio_extraction_mode: ffmpeg` only when local FFmpeg is available and a
real audio artifact is needed. Remote ASR providers are not used by this
workflow unless a future workflow explicitly selects one.

### `video_to_highlight_clip_plan.yaml`

Phase 11.2 mock-ASR video-to-clip-plan workflow:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_mock`
4. `write_transcript`
5. `load_roi_config`
6. `detect_highlights`
7. `rank_highlights_by_roi`
8. `generate_clip_plan_from_highlights`
9. `write_highlight_plan`
10. `write_clip_plan`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_highlight_clip_plan.yaml --input examples/demo_asr/video_to_highlight_clip_plan_input.example.json --output data/processed/runs/demo_video_to_highlight_clip_plan
```

This workflow composes Phase 11.1 transcript generation with the Phase 10
highlight pipeline. It writes `transcript.json`, `highlight_plan.json`, and
`clip_plan.json`. It does not use real ASR, inspect video frames, run FFmpeg
slicing, stitch clips, add subtitles, add BGM, or export a final video.

### `video_to_transcript_real_asr.yaml`

Phase 11.5 explicit remote-ASR video-to-transcript workflow:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_openai_compatible`
4. `write_transcript`

Example:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
$env:NARRATOCUT_OPENAI_API_KEY="<your-local-key>"
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_transcript_real_asr.yaml --input examples/demo_asr/video_to_transcript_real_asr_input.example.json --output data/processed/runs/demo_video_to_transcript_real_asr
```

This workflow is intentionally separate from the mock ASR workflows. It may
call a remote ASR provider only when `NARRATOCUT_ALLOW_REMOTE_ASR=true` is set
and an API key is available through the configured environment variable. It
writes `audio_manifest.json`, `audio/audio.wav`, and `transcript.json`. It does
not detect highlights, generate `clip_plan.json`, run FFmpeg slicing, stitch
clips, add subtitles, add BGM, or export a final video.

### `video_to_highlight_clip_plan_real_asr.yaml`

Phase 11.6 explicit real-ASR video-to-highlight-clip-plan workflow:

1. `load_video`
2. `extract_audio`
3. `transcribe_audio_openai_compatible`
4. `write_transcript`
5. `load_roi_config`
6. `detect_highlights`
7. `rank_highlights_by_roi`
8. `generate_clip_plan_from_highlights`
9. `write_highlight_plan`
10. `write_clip_plan`

Example:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
$env:NARRATOCUT_OPENAI_API_KEY="<your-local-key>"
.venv\Scripts\ncut run-workflow --workflow workflows/video_to_highlight_clip_plan_real_asr.yaml --input examples/demo_asr/video_to_highlight_clip_plan_real_asr_input.example.json --output data/processed/runs/demo_video_to_highlight_clip_plan_real_asr
```

This workflow composes explicit remote ASR with the Phase 10 highlight
pipeline. It writes `transcript.json`, `highlight_plan.json`, and
`clip_plan.json`. It does not inspect video frames, run FFmpeg slicing, stitch
clips, add subtitles, add BGM, or export a final video.

## Phase 11 artifact inspection

Phase 11 video workflows can be inspected and reviewed with the same commands:

```powershell
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_video_to_transcript
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_video_to_transcript
```

For video transcript profiles, inspection covers `audio_manifest.json`,
`audio/audio.wav`, `transcript.json`, `manifest.json`, `run_manifest.json`, and
`trace.json`. For video-to-highlight profiles, it also covers
`highlight_plan.json` and `clip_plan.json`.

The review layer checks transcript timestamps and provider metadata, audio
manifest execution status, highlight/clip source segment references, and
obvious secret leakage in explicit real-ASR runs. It does not call ASR, execute
FFmpeg slicing, or generate clips.
