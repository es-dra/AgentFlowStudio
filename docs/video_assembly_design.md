# Video Assembly Design

Phase 12 turns clipped segments into a final short-video file. It should remain
small at P0 and avoid becoming a general video editor.

## Goal

Use clips created by the real slicing workflow to produce:

```text
final_video.mp4
final_video_manifest.json
```

Phase 12 solves "make these clips into one deliverable video". It does not solve
"which moments should be clipped"; that belongs to Phase 10 and Phase 11.

## P0 Scope

P0 should include:

- `assembly_plan.json`
- ordered clip sequence
- concat clips with FFmpeg
- `final_video.mp4`
- `final_video_manifest.json`
- final-video quality checks
- inspect/review support for final-video artifacts

P0 quality checks:

- final video exists
- file size is greater than 0
- FFprobe can read the file when available
- final duration approximately matches the sum of clip durations
- expected resolution and codec are recorded when available

## P1 Scope

P1 may add:

- subtitle burn-in
- user-provided BGM
- BGM volume control
- basic audio mixing
- optional title card

P1 should not include:

- automatic music recommendation
- beat matching
- lyric recognition
- complex subtitle template libraries
- transition packs
- platform publishing

## Proposed Artifacts

`assembly_plan.json` should describe intent:

- `project_id`
- `source_run_id`
- `clips`
- `order`
- `target_duration_sec`
- `output_name`
- `assembly_options`

`final_video_manifest.json` should describe execution:

- `status`
- `final_video`
- `input_clips`
- `duration_sec`
- `width`
- `height`
- `codec`
- `errors`
- `warnings`

## Workflow Direction

Target P0 workflow:

```text
load_slice_manifest
  -> load_clip_outputs
  -> generate_assembly_plan
  -> concat_clips
  -> probe_final_video
  -> inspect-run
  -> review-run
```

The implementation should reuse FFmpeg path resolution and probe utilities from
Phase 9.

## Failure Policy

Assembly failures should still leave reviewable artifacts.

Examples:

- missing clip file -> failed `final_video_manifest.json`
- FFmpeg unavailable -> failed `final_video_manifest.json` with actionable error
- concat failure -> failed manifest with FFmpeg stderr summary
- duration mismatch -> inspect warning or failure depending on tolerance

## Acceptance Criteria

Phase 12 P0 is complete when:

- multiple input clips can be concatenated into `final_video.mp4`
- final-video manifest is written for success and failure paths
- inspect/review can report final-video status
- tests do not require installed FFmpeg; subprocess calls are mocked
- real local FFmpeg validation can be run with ignored local media
