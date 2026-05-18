# Tool Contracts

Phase 7.5B adds an agent-readable static catalog for NarratoCut's current
capabilities. The catalog is descriptive only: no runtime registry, no skill
runtime, and no autonomous agent control are added.

Phase 9 extends the same static catalog with real-video workflow nodes that now
exist in code. These entries remain descriptive contracts; they do not add an
agent runtime or automatic tool execution.

Phase 11.1 extends the catalog with the narrow video-to-transcript workflow
nodes. These entries cover local video loading, audio artifact creation,
fixture-backed mock ASR, and `transcript.json` writing. They do not add visual
highlight detection, real ASR providers, or new autonomous tool execution.

Phase 11.3/11.4 extends the same contracts with real FFmpeg audio extraction
metadata and an optional OpenAI-compatible ASR adapter. The default workflows
still use mock ASR fixtures unless explicitly changed.

Phase 13.2 extends the catalog with a basic subtitle export node that turns an
existing timestamped `Transcript` into `subtitles.srt` and
`subtitle_manifest.json`. It does not burn subtitles into video or call FFmpeg.

Phase 13.3 extends the catalog with a narrow subtitle burn-in node that consumes
an existing final video and an existing `subtitles.srt`, then writes
`final_video_with_subtitles.mp4` plus `subtitle_burn_manifest.json`. It does
not generate subtitles, regenerate clip assembly, add BGM, create covers, or add
transitions.

Phase 13.4 extends the catalog with a narrow cover export node that consumes an
existing final video, extracts one frame with FFmpeg, and writes `cover.jpg`
plus `cover_manifest.json`. It does not create cover templates, inspect video
frames for the best moment, add BGM, add transitions, or change final assembly.

Catalog file:

```text
configs/tool_catalog.yaml
```

The catalog describes existing tools by name, entry point, input artifacts,
output artifacts, dependencies, failure modes, quality checks, and agent usage
constraints.

## Boundary

The Phase 7.5B catalog may describe tools that are already present in code or
CLI form. It must not promise future systems as if they exist.

Allowed:

- local mock workflow tools
- existing CLI commands
- existing Python helper functions
- the FFmpeg command builder contract that does not execute FFmpeg
- the standalone minimal real slicing PoC, marked as external-process execution
- harness inspection
- Phase 9 real-video workflow nodes that already exist in code
- Phase 11.1 video-to-transcript workflow nodes that already exist in code
- optional Phase 11.4 ASR provider adapters, marked as network/API-key gated
- Phase 12.2 simple assembly nodes that consume existing real clips
- Phase 13.2 subtitle export nodes that write text subtitle artifacts
- Phase 13.3 subtitle burn-in nodes that consume existing final video and SRT artifacts
- Phase 13.4 cover export nodes that consume an existing final video

Not allowed:

- runtime skill registry
- `ncut list-skills`
- autonomous agent execution
- Web/API, database, queue, or hosted runtime

## Required Contract Fields

Each tool in `configs/tool_catalog.yaml` includes:

- `name`
- `description`
- `category`
- `entrypoints`
- `input_artifacts`
- `output_artifacts`
- `requires`
- `failure_modes`
- `quality_checks`
- `agent_usage`

`requires` states whether a tool needs FFmpeg, network access, a model provider,
or an API key. Optional remote ASR adapters must be marked as network,
model-provider, and API-key gated.

`agent_usage` states whether a future agent may safely call the tool, whether
human review is required, whether it mutates workflow definitions, and whether it
executes an external process.

Tools that execute local FFmpeg are explicitly marked as not safe for automatic
agent execution and requiring human review.

## Cataloged Tools

### `analyze_hooks`

Analyzes a UTF-8 text file and writes hook candidates to `hooks.json`.

- Category: ROI analysis
- Main entry points: `ncut analyze-hooks`, workflow node `analyze_hooks`
- Inputs: `text_file`
- Outputs: `hooks.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `hooks_file_exists`, `hooks_non_empty`

### `generate_scripts`

Generates mock short-video scripts from hook candidates.

- Category: script generation
- Main entry points: `ncut generate-scripts`, workflow node `generate_scripts`
- Inputs: `hooks.json`
- Outputs: `scripts.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `scripts_file_exists`, `scripts_non_empty`

### `generate_clip_plans`

Generates deterministic clip planning contracts from scripts.

- Category: clip planning
- Main entry points: `ncut generate-clip-plans`, workflow node `generate_clip_plans`
- Inputs: `scripts.json`
- Outputs: `clip_plans.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `clip_plans_file_exists`, `clip_plans_non_empty`

### `mock_slice`

Generates mock clip text files and a slice manifest from clip plans.

- Category: mock slicing
- Main entry points: `ncut mock-slice`, workflow node `mock_slice`
- Inputs: `clip_plans.json`
- Outputs: `slice_manifest.json`, `clips/`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `slice_manifest_exists`, `clips_dir_exists`, `mock_clips_count_matches_manifest`

### `build_ffmpeg_command_contract`

Builds a minimal FFmpeg slicing command list without executing FFmpeg.

- Category: real slicing contract
- Main entry point: `narratocut.slicing_sop.build_ffmpeg_slice_command`
- Inputs: `input_video_path`, `start_sec`, `duration_sec`, `output_video_path`
- Outputs: `ffmpeg_command`
- Requires: no installed FFmpeg because this tool only builds the command
- Main check: `ffmpeg_command_has_expected_args`

### `slice_real`

Executes minimal local FFmpeg slicing from clip plans.

- Category: real slicing PoC
- Main entry points: `ncut slice-real`, `narratocut.slicing_sop.slice_clip_plans_real`
- Inputs: `input_video_path`, `clip_plans.json`
- Outputs: `real_slice_manifest.json`, `clips/*.mp4`
- Requires: installed FFmpeg; no network, no model provider, no API key
- Main checks: `real_slice_manifest_exists`, `real_clips_written`
- Agent usage: not safe for automatic execution, requires human review, executes an external process

### `probe_video_metadata`

Reads local video metadata through FFprobe and writes `video_metadata.json`.

- Category: real video metadata
- Main entry points: workflow node `probe_video_metadata`,
  `narratocut.slicing_sop.probe_video_metadata`
- Inputs: `input_video_path`, `ffprobe_executable`
- Outputs: `video_metadata.json`
- Requires: installed FFprobe; no network, no model provider, no API key
- Main checks: `video_metadata_exists`, `video_metadata_status`

### `validate_clip_plan`

Validates one `ClipPlan` against `ROISettings`, video metadata, and local
FFmpeg availability.

- Category: real video validation
- Main entry points: workflow node `validate_clip_plan`,
  `narratocut.slicing_sop.validate_clip_plan`
- Inputs: `clip_plan.json`, `roi_config.json`, `video_metadata.json`
- Outputs: `clip_plan_validation.json`
- Requires: no network, no model provider, no API key
- Main checks: segment time range, video duration, ROI advisory constraints,
  output filename safety, FFmpeg availability

### `real_slice_video`

Executes the real-video workflow slicing node after validation succeeds.

- Category: real video workflow node
- Main entry points: workflow node `real_slice_video`,
  `narratocut.slicing_sop.slice_clip_plans_real`
- Inputs: `input_video_path`, `clip_plan.json`, `clip_plan_validation.json`
- Outputs: `real_slice_manifest.json`, `clips/*.mp4`
- Requires: installed FFmpeg; no network, no model provider, no API key
- Main checks: `real_slice_manifest_exists`, `real_slice_manifest_status`,
  `real_clips_written`
- Agent usage: not safe for automatic execution, requires human review,
  executes an external process

### `load_real_slice_manifest`

Loads a `real_slice_manifest.json` from a prior slicing run.

- Category: video assembly input
- Main entry point: workflow node `load_real_slice_manifest`
- Inputs: `real_slice_manifest.json`
- Outputs: `real_slice_manifest.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `real_slice_manifest_exists`

### `generate_assembly_plan`

Generates a simple ordered assembly plan from successful real clip records.

- Category: video assembly planning
- Main entry points: workflow node `generate_assembly_plan`,
  `narratocut.assembly_sop.build_assembly_plan`
- Inputs: `real_slice_manifest.json`
- Outputs: `assembly_plan.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `assembly_plan_exists`

### `concat_clips`

Concatenates ordered clip files into `final_video.mp4` with FFmpeg.

- Category: video assembly execution
- Main entry points: workflow node `concat_clips`,
  `narratocut.assembly_sop.concat_clips`
- Inputs: `assembly_plan.json`, `clips/*.mp4`
- Outputs: `concat_list.txt`, `final_video.mp4`,
  `final_video_manifest.json`
- Requires: installed FFmpeg; no network, no model provider, no API key
- Main checks: `final_video_manifest_exists`,
  `final_video_manifest_status`, `final_video_file_exists`
- Agent usage: not safe for automatic execution, requires human review,
  executes an external process

### `probe_final_video`

Probes the assembled final video and enriches `final_video_manifest.json`.

- Category: video assembly metadata
- Main entry points: workflow node `probe_final_video`,
  `narratocut.slicing_sop.probe_video_metadata`
- Inputs: `final_video.mp4`, `final_video_manifest.json`
- Outputs: `final_video_manifest.json`
- Requires: installed FFprobe; no network, no model provider, no API key
- Main checks: `final_video_duration_tolerance`

### `load_video`

Loads and validates a local video path for the video-to-transcript workflow.

- Category: video transcription input
- Main entry point: workflow node `load_video`
- Inputs: `input_video_path`
- Outputs: workflow state `video_path`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main check: `input_video_file_exists`

### `extract_audio`

Extracts or mocks a local audio artifact from a video for ASR.

- Category: video transcription audio
- Main entry points: workflow node `extract_audio`,
  `narratocut.audio_sop.extract_audio_from_video`
- Inputs: `input_video_path`
- Outputs: `audio_manifest.json`, `audio/audio.wav`
- Requires: installed FFmpeg for real extraction mode. The Phase 11.1 examples
  still use `audio_extraction_mode: mock`, which does not require installed
  FFmpeg.
- Main checks: `audio_manifest_exists`, `audio_artifact_exists`,
  `audio_manifest_status`

### `transcribe_audio_mock`

Converts an audio artifact into a timestamped `Transcript` using a local
fixture-backed mock ASR provider.

- Category: video transcription ASR
- Main entry points: workflow node `transcribe_audio_mock`,
  `narratocut.asr_sop.MockASRProvider`
- Inputs: `audio_manifest.json`, `asr_fixture.json`
- Outputs: workflow state `transcript`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `transcript_segments_non_empty`, `transcript_timestamps_valid`

### `transcribe_audio_openai_compatible`

Converts an audio artifact into a timestamped `Transcript` using an explicitly
enabled OpenAI-compatible ASR provider.

- Category: video transcription ASR
- Main entry points: workflow node `transcribe_audio_openai_compatible`,
  `narratocut.asr_sop.OpenAICompatibleASRProvider`
- Inputs: `audio_manifest.json`, `audio/audio.wav`
- Outputs: workflow state `transcript`
- Requires: network, model provider, and API key. Calls are blocked unless
  `NARRATOCUT_ALLOW_REMOTE_ASR=true` is set.
- Main checks: `transcript_segments_non_empty`, `transcript_timestamps_valid`

### `write_transcript`

Writes the current timestamped `Transcript` state to `transcript.json`.

- Category: video transcription output
- Main entry point: workflow node `write_transcript`
- Inputs: workflow state `transcript`
- Outputs: `transcript.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `transcript_file_exists`, `transcript_schema_valid`

### `write_subtitles`

Exports the current timestamped `Transcript` state to `subtitles.srt` and
`subtitle_manifest.json`.

- Category: subtitle export
- Main entry points: workflow node `write_subtitles`,
  `narratocut.subtitle_sop.build_subtitle_export`
- Inputs: workflow state `transcript`
- Outputs: `subtitles.srt`, `subtitle_manifest.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `subtitle_manifest_exists`, `subtitle_manifest_status`,
  `subtitle_file_exists`, `subtitle_cue_count_matches_manifest`
- Boundary: this node only writes subtitle text artifacts. It does not burn
  subtitles into video, re-encode media, add BGM, or create a final video.

### `burn_subtitles`

Burns an existing `subtitles.srt` file into an existing final video with
FFmpeg.

- Category: subtitle burn execution
- Main entry points: workflow node `burn_subtitles`,
  `narratocut.subtitle_burn_sop.burn_subtitles_into_video`
- Inputs: `final_video.mp4`, `subtitles.srt`
- Outputs: `final_video_with_subtitles.mp4`,
  `subtitle_burn_manifest.json`
- Requires: installed FFmpeg; no network, no model provider, no API key
- Main checks: `subtitle_burn_manifest_exists`,
  `subtitle_burn_manifest_status`, `subtitle_burn_output_file_exists`,
  `subtitle_burn_ffmpeg_returncode`
- Agent usage: not safe for automatic execution, requires human review,
  executes an external process
- Boundary: this node consumes existing artifacts only. It does not generate
  subtitles, regenerate final assembly, add BGM, add transitions, create covers,
  call remote providers, or provide a Web UI.

### `probe_subtitle_burn`

Probes the subtitle-burned output video and enriches
`subtitle_burn_manifest.json`.

- Category: subtitle burn metadata
- Main entry points: workflow node `probe_subtitle_burn`,
  `narratocut.slicing_sop.probe_video_metadata`
- Inputs: `final_video_with_subtitles.mp4`, `subtitle_burn_manifest.json`
- Outputs: `subtitle_burn_manifest.json`
- Requires: installed FFprobe; no network, no model provider, no API key
- Main checks: `subtitle_burn_video_stream_present`,
  `subtitle_burn_output_file_size_positive`

### `export_cover`

Exports a single `cover.jpg` image from an existing final video with FFmpeg.

- Category: cover export execution
- Main entry points: workflow node `export_cover`,
  `narratocut.cover_sop.export_cover_from_video`
- Inputs: `final_video.mp4`
- Outputs: `cover.jpg`, `cover_manifest.json`
- Requires: installed FFmpeg; no network, no model provider, no API key
- Main checks: `cover_manifest_exists`, `cover_manifest_status`,
  `cover_image_file_exists`, `cover_image_file_size_positive`,
  `cover_ffmpeg_returncode`
- Agent usage: not safe for automatic execution, requires human review,
  executes an external process
- Boundary: this node consumes an existing final video only. It does not select
  an optimal highlight frame, generate templates, add text overlays, add BGM,
  add transitions, call remote providers, or provide a Web UI.

### `inspect_run`

Inspects a workflow run directory and writes `quality_report.json`.

- Category: harness inspection
- Main entry points: `ncut inspect-run`, `narratocut.harness.inspect_run`
- Inputs: `run_dir`
- Outputs: `quality_report.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `run_manifest_file_exists`, `trace_file_exists`, `mock_clips_count_matches_manifest`
