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
transcript input can later produce both `highlight_plan.json` and `clip_plan.json`.

## Workflow Direction

Phase 10 should add a text-first workflow:

```text
load_roi_config
  -> load_script_or_transcript
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

## Acceptance Criteria

Phase 10 is complete when:

- `script_only` inputs produce valid `highlight_plan.json`
- `timestamped_transcript` inputs produce valid `highlight_plan.json` and
  `clip_plan.json`
- generated clip plans can pass Phase 9 validation when their timestamps are
  within video duration
- ROI settings influence ranking metadata or ordering
- tests cover both input modes and provider failure handling
