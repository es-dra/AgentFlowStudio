# Product Roadmap

This roadmap records the mainline direction after Phase 13. NarratoCut is now a
CLI-first technical MVP: it can produce real local video artifacts through
workflow contracts, but it is not yet a consumer-facing product.

## Product Positioning

NarratoCut is an artifact-driven short-video workflow system for existing
videos, transcripts, scripts, and clip plans.

Current product path:

```text
video / transcript / clip_plan
  -> highlight_plan
  -> clip_plan.json
  -> real clips
  -> final_video.mp4
  -> subtitles.srt
  -> final_video_with_subtitles.mp4
  -> cover.jpg
  -> final_video_with_bgm.mp4
  -> finished_package_manifest.json
  -> inspect/review
```

The current product is useful for technical users who can run CLI workflows and
inspect artifacts. It is not yet a one-click editor, Web UI, desktop product, or
hosted SaaS service.

## Completed Mainline Phases

### Phase 9: Real Video Slicing Foundation

Status: complete.

Purpose:

- execute a provided `ClipPlan` against a local video
- validate the plan against video metadata and ROI settings
- produce real `.mp4` clips
- keep run artifacts inspectable and reviewable

Not included:

- automatic highlight detection
- ASR
- final-video assembly
- subtitles, BGM, cover, Web UI, or agent runtime

### Phase 10: Script / Timestamped Transcript Highlight Detection

Status: complete.

Purpose:

- detect deterministic highlight candidates from script or timestamped
  transcript inputs
- rank highlights with ROI settings
- generate executable `clip_plan.json` only when timestamps exist

Modes:

- `script_only`: writes `highlight_plan.json`; no `clip_plan.json`
- `timestamped_transcript`: writes `highlight_plan.json` and `clip_plan.json`

### Phase 11: Video ASR + Timestamped Highlights

Status: complete.

Purpose:

- turn local videos into timestamped transcripts
- compose transcripts with the Phase 10 highlight pipeline
- support explicit real-ASR workflows without default remote calls
- harden video artifact inspect/review checks

Important boundary:

- real ASR is opt-in only via explicit workflow and
  `NARRATOCUT_ALLOW_REMOTE_ASR=true`
- no video-frame highlight detection
- no slicing or assembly in Phase 11 workflows

### Phase 12: Real Clip Execution and Final Video Assembly

Status: complete.

Purpose:

- bridge generated or existing `clip_plan.json` into real clips
- compose mock-ASR planning with real slicing for smoke coverage
- assemble real clips into `final_video.mp4`

Completed capabilities:

- `clip_plan_to_real_clips.yaml`
- `video_to_real_clips.yaml`
- `clips_to_final_video.yaml`
- `real_slice_manifest.json`
- `assembly_plan.json`
- `concat_list.txt`
- `final_video_manifest.json`
- `final_video.mp4`
- inspect/review support for real clips and final video outputs

### Phase 13: Final Video Enhancement and Packaging

Status: complete.

Purpose:

- harden final video quality checks
- add narrow, composable product artifacts around an existing final video
- keep every enhancement inspectable and reviewable

Completed increments:

- Phase 13.1: final video quality hardening
- Phase 13.2: subtitle export to `subtitles.srt`
- Phase 13.3: subtitle burn-in to `final_video_with_subtitles.mp4`
- Phase 13.4: cover export to `cover.jpg`
- Phase 13.5: local BGM mix to `final_video_with_bgm.mp4`
- Phase 13.6: BGM mix hardening, volume bounds, and `bgm_only`
- Phase 13.7: finished package manifest indexing

Phase 13 output surface:

```text
final_video.mp4
subtitles.srt
final_video_with_subtitles.mp4
cover.jpg
final_video_with_bgm.mp4
finished_package_manifest.json
quality_report.json
review_report.json
```

Not included:

- one-command end-to-end product workflow
- physical package directory or zip export
- automatic music selection
- advanced subtitle templates
- transitions
- publishing/upload
- Web UI

## Next Direction: Phase 14 Productization

Phase 14 should not start as "Web UI first." The backend product path needs a
stable Golden Path and one-command orchestration before a UI can be useful.

Recommended sequence:

### Phase 14.0: Documentation and Golden Path

Goals:

- align README and roadmap with current capabilities
- document current architecture
- document the Phase 13 complete Golden Path
- run a local product smoke with ignored media artifacts

### Phase 14.1: One-command Finished Package Workflow

Recommended workflow:

```text
workflows/final_video_to_finished_package.yaml
```

Initial scope:

```text
final_video.mp4
+ optional transcript/subtitles
+ optional BGM
  -> subtitles.srt, if transcript is provided
  -> final_video_with_subtitles.mp4, if subtitles are provided/enabled
  -> cover.jpg
  -> final_video_with_bgm.mp4, if BGM is provided
  -> finished_package_manifest.json
```

This should compose Phase 13 capabilities only. It should not regenerate
highlights, clip plans, real clips, or final assembly.

### Phase 14.2: Physical Package Export and Report

Goals:

- create a package directory with copied final artifacts
- write `package_report.md`
- optionally write a zip archive later

Candidate output:

```text
package/
  final_video.mp4
  final_video_with_subtitles.mp4
  final_video_with_bgm.mp4
  cover.jpg
  subtitles.srt
  finished_package_manifest.json
  package_report.md
  review_report.json
```

### Phase 14.3: Web UI v0

Goal:

- expose the stable Golden Path through a local product console

The UI should call stable workflow/API surfaces instead of hard-coding demo
paths.

### Phase 14.4: Agent Workflow Tools

Goal:

- expose safe workflow actions as controlled agent tools
- keep approval, risk checks, and audit trails explicit

The project should not bind to one agent framework too early.
