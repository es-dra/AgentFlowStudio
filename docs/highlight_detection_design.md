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
- `type`
- `title`
- `source_text`
- `reason`
- `score`
- `suggested_duration`
- `start_sec`
- `end_sec`
- `roi_tags`
- `risk_flags`

Recommended `HighlightPlan` fields:

- `project_id`
- `source_type`
- `content_goal`
- `target_platform`
- `highlights`
- `created_at`

`start_sec` and `end_sec` are optional for `script_only` and required before
generating an executable `ClipPlan`.

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

## Acceptance Criteria

Phase 10 is complete when:

- `script_only` inputs produce valid `highlight_plan.json`
- `timestamped_transcript` inputs produce valid `highlight_plan.json` and
  `clip_plan.json`
- generated clip plans can pass Phase 9 validation when their timestamps are
  within video duration
- ROI settings influence ranking metadata or ordering
- tests cover both input modes and provider failure handling
