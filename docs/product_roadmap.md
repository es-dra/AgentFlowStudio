# Product Roadmap

This roadmap records the mainline direction after the v0.1.0 delivery closeout.
NarratoCut is now the distribution-side short video highlight workflow module
of AgentFlow Studio: it can produce local finished-package artifacts through
workflow contracts, but it is not yet a consumer-facing product or Web UI.

## Product Positioning

NarratoCut is an artifact-driven short-video distribution workflow system for
existing videos, transcripts, scripts, and clip plans.

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

- physical package directory or zip export
- automatic music selection
- advanced subtitle templates
- transitions
- publishing/upload
- Web UI

## Next Direction After v0.1.0

NarratoCut v0.1.0 should be treated as the stable distribution-side MVP before
opening broader AgentFlow Studio work.

The detailed post-release plan is in
[`post_v0_1_0_plan.md`](post_v0_1_0_plan.md).

Recommended sequence:

1. Keep NarratoCut stable and fix contract or delivery-readiness regressions.
2. Build a separate NarratoCut Web UI branch as a package/run/report viewer.
3. On the mainline, expand AgentFlow Studio architecture and start
   NarratoStudio production-side artifact contracts.
4. Merge the viewer branch only after it reads stable run/package artifacts
   instead of hard-coding demo paths.

## Phase 15: Post-v0.1.0 Productization

Status: in progress.

Phase 15 keeps the `v0.1.0` CLI/Agent MVP stable while the mainline defines the
AgentFlow Studio contract layer and validates NarratoStudio as the
production-side sibling module.

Detailed Phase 15 history now lives in
[`agentflow_phase15_roadmap.md`](agentflow_phase15_roadmap.md).

Current Phase 15 rules:

- keep core workflow behavior stable unless a narrow branch requires it
- treat test runs and internal validation samples as evidence, not deliverables
- do not add Web/API/database/platform runtime assumptions to the released CLI
  path
- keep AgentFlow work contract-first until runtime phases are explicitly opened

Current checkpoint:

- contract-layer review gates are in place
- runtime readiness gates are documented
- Router dry-run decision validation is in place
- skill invocation/result replay validation is in place
- intermediate asset architecture is defined for reusable Agent execution
  assets before runtime behavior changes
- the architecture refactor plan is defined before moving contracts into a
  platform package
- the next mainline slice should introduce only a minimal `agentflow/` package
  skeleton before moving behavior
