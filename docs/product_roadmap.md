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

Purpose:

- keep the `v0.1.0` CLI/Agent MVP stable
- prepare a viewer-only Web UI branch around existing run/package artifacts
- define AgentFlow Studio and NarratoStudio artifact boundaries before runtime
  work
- improve selection quality only through measurable artifact evidence
- validate NarratoStudio as a local-first structured production handoff
  generator before adding runtime or Web assumptions

Default boundary:

- do not change core workflow behavior until a specific branch goal requires it
- do not treat test runs or internal validation samples as formal deliverables
- do not add Web/API/database/platform runtime assumptions to the released CLI
  path

## Phase 15.1: NarratoStudio Mainline MVP

Status: complete.

Purpose:

- add `NarratoStudio` as a sibling module for production-side MVP validation
- keep `NarratoCut` as the distribution-side module
- prove the first production workflow through structured artifacts, not a chat
  transcript

First workflow:

```text
creative_brief.json
-> story_bible.json
-> episode_outline.json
-> scene_plan.json
-> shot_plan.json
-> prompt_pack.json
-> production_handoff.json
-> production_report.md
```

Boundary:

- local deterministic generation only
- no remote LLM call
- no Agent runtime
- no database
- no Web UI implementation
- no migration from reference UI projects

## Phase 15.2: AgentFlow Mainline Contracts

Status: in progress.

Purpose:

- define the top-level AgentFlow Studio contract layer before runtime work
- fix the boundary between NarratoStudio production-side artifacts and
  NarratoCut distribution-side artifacts
- document feedback, memory candidate, artifact map, and skill contract shapes
  without implementing Router, Memory runtime, or cross-module execution

Expected documents:

- `docs/agentflow_studio_architecture.md`
- `docs/module_boundary.md`
- `docs/agentflow_artifact_map.md`
- `docs/agentflow_memory_contract.md`
- `docs/agentflow_skill_contract.md`

Expected examples:

- `examples/agentflow/project_manifest.example.json`
- `examples/agentflow/artifact_map.example.json`
- `examples/agentflow/feedback_event.example.jsonl`

Boundary:

- documentation and minimal examples only
- no workflow changes
- no CLI changes
- no package rename
- no tag changes
- no AgentFlow Router runtime
- no AgentFlow Memory runtime
- no skill runtime
- no Web UI
