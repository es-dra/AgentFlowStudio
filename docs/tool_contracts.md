# Tool Contracts

Phase 7.5B adds an agent-readable static catalog for NarratoCut's current
capabilities. The catalog is descriptive only: no runtime registry, no skill
runtime, and no autonomous agent control are added.

Phase 9 extends the same static catalog with real-video workflow nodes that now
exist in code. These entries remain descriptive contracts; they do not add an
agent runtime or automatic tool execution.

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
or an API key. In this phase, all cataloged tools are local and key-free.

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

### `inspect_run`

Inspects a workflow run directory and writes `quality_report.json`.

- Category: harness inspection
- Main entry points: `ncut inspect-run`, `narratocut.harness.inspect_run`
- Inputs: `run_dir`
- Outputs: `quality_report.json`
- Requires: no FFmpeg, no network, no model provider, no API key
- Main checks: `run_manifest_file_exists`, `trace_file_exists`, `mock_clips_count_matches_manifest`
