# Highlight Detection Design

Phase 10 introduces text-based highlight detection. It moves NarratoCut from
"execute a provided ClipPlan" toward "help decide what should be clipped".

## Goal

Detect short-video candidates from scripts or transcripts and write structured
artifacts that can be reviewed, ranked, and, when timestamps are available,
converted into `ClipPlan`.

Target highlight types:

- `hook`
- `conflict`
- `reversal`
- `climax`
- `quote`
- `summary`
- `call_to_action`

## Input Modes

### `script_only`

Input:

- normal script text, narration draft, article section, or speech outline
- no reliable timestamps

Output:

- `highlight_plan.json`

No executable `clip_plan.json` is produced in this mode. The system can explain
what looks valuable, but it cannot map that text to video time ranges without a
timeline.

### `timestamped_transcript`

Input:

- transcript segments with `start_sec`, `end_sec`, and `text`

Output:

- `highlight_plan.json`
- `clip_plan.json`

The generated `clip_plan.json` can be validated and executed by the Phase 9 real
video slicing workflow.

## Artifact Shape

The first version should introduce a highlight schema under
`narratocut/schemas/` and keep it small.

Recommended `HighlightSegment` fields:

- `highlight_id`
- `source_type`
- `highlight_type`
- `title`
- `text`
- `reason`
- `score`
- `confidence`
- `suggested_duration`
- `start_time`
- `end_time`
- `roi_tags`
- `source_segment_ids`
- `metadata`

Recommended `HighlightPlan` fields:

- `plan_id`
- `input_mode`
- `source_id`
- `roi_profile`
- `highlights`
- `summary`
- `warnings`
- `metadata`
- `created_at`

`start_time` and `end_time` are optional at the `HighlightSegment` level, but
the `HighlightPlan` input mode decides whether they may appear.

The Phase 10.1 schema uses `start_time` and `end_time` for transcript-aligned
time ranges. `script_only` highlight plans must not include these fields;
`timestamped_transcript` highlight plans require them for every highlight.

## Input Examples

Phase 10.2 adds example contracts under `examples/demo_highlight/`:

- `script.txt`
- `transcript.json`
- `roi_config.json`
- `script_input.example.json`
- `transcript_input.example.json`

The script-only input produces only `highlight_plan.json`. The timestamped
transcript input can produce both `highlight_plan.json` and `clip_plan.json`.

## Workflow Direction

Phase 10 adds text-first workflows:

```text
load_roi_config
  -> load_script / load_transcript
  -> detect_highlights
  -> rank_highlights_by_roi
  -> generate_clip_plan, only when timestamps exist
```

If timestamps exist and a source video is provided, the generated clip plan can
continue into:

```text
validate_clip_plan
  -> real_slice_video
  -> inspect-run
  -> review-run
```

## Provider Boundary

The implementation should keep provider behavior behind the existing model
gateway shape.

Required:

- deterministic mock provider output for tests
- schema validation for generated highlight plans
- no remote LLM calls unless `NARRATOCUT_ALLOW_REMOTE_LLM=true`

Not required in Phase 10:

- ASR
- OCR
- direct video understanding
- final-video assembly
- BGM, subtitles, or Web UI

## Phase 10.3 Deterministic Baseline

Phase 10.3 adds `narratocut.highlight_sop` as an offline baseline detector.
This module is intentionally not a fake-data generator and not an LLM wrapper.
It is a deterministic rule-based detector used to make Phase 10 testable before
provider-backed detection is introduced.

Public API:

- `DeterministicHighlightDetector.detect_script(...)`
- `DeterministicHighlightDetector.detect_transcript(...)`
- `detect_highlights_from_script(...)`
- `detect_highlights_from_transcript(...)`

The baseline detects a small set of candidate types:

- `hook`
- `conflict`
- `insight`
- `cta`
- `other`, as a fallback candidate

For `script_only`, generated highlights are untimed. For
`timestamped_transcript`, generated highlights preserve source segment IDs and
the exact `start_time` / `end_time` values from the transcript. Phase 10.3 still
does not perform ROI ranking or generate executable `ClipPlan` artifacts.

## Phase 10.4 ROI-aware Ranking

Phase 10.4 adds transparent local ranking rules that reorder a `HighlightPlan`
with optional `ROISettings`.

Public API:

- `ROIHighlightRanker.rank(...)`
- `rank_highlights_by_roi(...)`

The ranker returns a new `HighlightPlan` instead of mutating the detector output.
This lets later workflows keep both raw and ranked plans, for example:

```text
highlight_plan.raw.json
highlight_plan.ranked.json
```

The detector score remains in `highlight.score`. The ROI-aware score is stored
under:

```text
highlight.metadata.ranking_factors.final_score
```

Ranking factors include:

- `base_score`
- `confidence`
- `content_goal`
- `target_platform`
- `priority`
- `content_goal_boost`
- `target_platform_boost`
- `priority_boost`
- `final_score`
- `matched_rules`

The current formula is intentionally simple and explainable:

```text
final_score =
  base_score * 0.70
  + confidence * 0.15
  + content_goal_boost
  + target_platform_boost
  + priority_boost
```

`final_score` is clamped to `0.0-1.0`. This is a ranking heuristic, not a
prediction of views, virality, conversion, or revenue.

The ranker may add user-facing tags such as `goal:*`, `platform:*`, and
`priority:*`, while preserving detector-provided `roi_tags`.

## Phase 10.5 Highlight-to-ClipPlan Generation

Phase 10.5 converts a ranked `timestamped_transcript` `HighlightPlan` into one
executable `ClipPlan`.

Public API:

- `HighlightClipPlanGenerator.generate(...)`
- `generate_clip_plan_from_highlights(...)`

Input requirements:

- `HighlightPlan.input_mode` must be `timestamped_transcript`
- each highlight must already contain `start_time` and `end_time`
- `source_video` must be provided by the caller

The generator intentionally rejects `script_only` plans. Plain scripts can
produce a `HighlightPlan`, but they cannot produce a trustworthy executable
`ClipPlan` without a timeline.

The generated `ClipPlan` preserves the incoming highlight order. This means the
usual Phase 10 path is:

```text
transcript
  -> detect_highlights
  -> rank_highlights_by_roi
  -> generate_clip_plan_from_highlights
```

Each highlight becomes one `ClipSegment`. Segment metadata preserves:

- `highlight_id`
- `highlight_type`
- `highlight_score`
- `highlight_confidence`
- `roi_tags`
- `source_segment_ids`
- `ranking_factors`, when available

This increment still does not run FFmpeg, validate against a real video, add
workflow nodes, add CLI commands, generate ASR, stitch clips, burn subtitles, or
mix BGM. Those remain later phases or later Phase 10 workflow integration.

## Phase 10.6 Workflow Integration

Phase 10.6 exposes the Phase 10 pipeline through `run-workflow` without adding
new product CLI commands.

Workflows:

- `workflows/script_to_highlight_plan.yaml`
- `workflows/transcript_to_highlight_clip_plan.yaml`

Script workflow:

```text
load_roi_config
  -> load_script
  -> detect_highlights
  -> rank_highlights_by_roi
  -> write_highlight_plan
```

Output:

- `highlight_plan.json`

It does not write `clip_plan.json`.

Timestamped transcript workflow:

```text
load_roi_config
  -> load_transcript
  -> detect_highlights
  -> rank_highlights_by_roi
  -> generate_clip_plan_from_highlights
  -> write_highlight_plan
  -> write_clip_plan
```

Outputs:

- `highlight_plan.json`
- `clip_plan.json`

The workflow run manifest records Phase 10-specific modes:

- `workflow_mode: highlight_detection` for script-only runs
- `workflow_mode: highlight_to_clip_plan` for timestamped transcript runs

Phase 10.6 still does not generate ASR, inspect raw video for highlights, run
FFmpeg, assemble clips, burn subtitles, mix BGM, or export a final video.

## Acceptance Criteria

Phase 10 is complete when:

- `script_only` inputs produce valid `highlight_plan.json`
- `timestamped_transcript` inputs produce valid `highlight_plan.json` and
  `clip_plan.json`
- generated clip plans can pass Phase 9 validation when their timestamps are
  within video duration
- ROI settings influence ranking metadata or ordering
- tests cover both input modes, workflow execution, and generated artifact
  schema validation
