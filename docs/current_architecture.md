# Current Architecture

This document summarizes the NarratoCut architecture for the `v0.1.0` delivery
closeout. NarratoCut is the distribution-side short video highlight workflow
module of AgentFlow Studio. It is a reference for productization work, Golden
Sample runs, and future UI/API or agent integration.

## Current Position

NarratoCut is a CLI-first technical MVP for short-video distribution workflows.
It is designed around readable artifacts, deterministic workflow execution,
package reports, and post-run inspection/review.

NarratoStudio is now added as a sibling MVP module inside this repository for
production-side validation. It is a local-first structured production handoff
generator, not a replacement or rename of NarratoCut.

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

## Architecture Principles

- Schema-first: Pydantic schemas define contracts for major artifacts.
- Workflow-driven: YAML workflows define execution order.
- Artifact-readable: each major step writes JSON or media outputs.
- Inspectable/reviewable: `inspect-run` writes quality reports; `review-run`
  writes agent-readable review reports.
- Mock-first by default: remote providers are opt-in.
- CLI stays thin: business logic lives in `narratocut/*`, `workflow_engine`, or
  `harness`.

## Main Layers

```text
apps/cli
  -> thin Typer command layer

workflow_engine
  -> workflow loading, context, node registry, runner, draft planner

schemas
  -> data contracts for clips, transcripts, highlights, video metadata,
     subtitles, packages, validation, and workflow runs

*_sop modules
  -> domain logic for slicing, assembly, subtitles, covers, BGM, ASR,
     highlights, packages, and audio extraction

harness
  -> run manifests, trace, inspect-run quality checks, review-run reports

narratostudio
  -> production-side contracts and deterministic handoff SOP logic

workflows
  -> YAML workflow definitions

examples
  -> committed input fixtures and local-media path examples

data
  -> ignored local media, runs, reports, and generated artifacts
```

## Workflow Families

Planning workflows:

- `script_to_highlight_plan.yaml`
- `transcript_to_highlight_clip_plan.yaml`
- `video_to_transcript.yaml`
- `video_to_transcript_real_asr.yaml`
- `video_to_highlight_clip_plan.yaml`
- `video_to_highlight_clip_plan_real_asr.yaml`

Execution workflows:

- `clip_plan_to_real_clips.yaml`
- `video_to_real_clips.yaml`
- `clips_to_final_video.yaml`

Final artifact workflows:

- `transcript_to_subtitles.yaml`
- `final_video_with_subtitles.yaml`
- `final_video_to_cover.yaml`
- `final_video_with_bgm.yaml`
- `final_video_package.yaml`

Production-side MVP workflow:

- `narratostudio_brief_to_production_handoff.yaml`

## Important Artifacts

Run-level artifacts:

- `manifest.json`
- `run_manifest.json`
- `trace.json`
- `quality_report.json`
- `review_report.json`
- `delivery_readiness.json`
- `delivery_readiness.md`

`run_manifest.json` keeps a backward-compatible `artifacts` map and an expanded
`artifact_index` for agents and future Web UI code. `review_report.json`
includes `quality_level` and `delivery_status` so callers do not need to infer
handoff state only from raw check counts.

Planning artifacts:

- `transcript.json`
- `highlight_plan.json`
- `clip_plan.json`

Execution artifacts:

- `video_metadata.json`
- `clip_plan_validation.json`
- `real_slice_manifest.json`
- `clips/`
- `assembly_plan.json`
- `concat_list.txt`
- `final_video_manifest.json`
- `final_video.mp4`

Enhancement/package artifacts:

- `subtitle_manifest.json`
- `subtitles.srt`
- `subtitle_burn_manifest.json`
- `final_video_with_subtitles.mp4`
- `cover_manifest.json`
- `cover.jpg`
- `audio_mix_manifest.json`
- `final_video_with_bgm.mp4`
- `finished_package_manifest.json`

NarratoStudio production handoff artifacts:

- `creative_brief.json`
- `story_bible.json`
- `episode_outline.json`
- `scene_plan.json`
- `shot_plan.json`
- `prompt_pack.json`
- `production_handoff.json`
- `production_report.md`
- `memory_candidates.json`
- `cost_quality_trace.json`
- `feedback_signal_log.json`
- `execution_trace.json`

## Quality Profiles

Quality profiles route `inspect-run` and `review-run` to the right checks.
Important profiles include:

- `real_clips`
- `video_real_clips`
- `final_video`
- `subtitle_export`
- `subtitle_burn`
- `cover_export`
- `bgm_mix`
- `finished_package`
- `narratostudio_production_handoff`
- video transcript and highlight profiles

## Current Boundaries

The system does not yet provide:

- physical package directory or zip export
- Web UI
- hosted NarratoStudio runtime or Web UI
- AgentFlow Router runtime
- AgentFlow Memory runtime
- automatic music selection
- publishing/upload
- transition templates
- automatic visual highlight detection from video frames
- default remote ASR or LLM calls

## Productization Risks

- `README.md` and roadmap must stay aligned with the implemented workflow
  surface.
- `workflow_engine/nodes.py` is a registration hotspot and should not absorb
  more business logic.
- More workflows increase discoverability burden; a documented Golden Path and
  one-command orchestration are needed before Web UI work.
- `finished_package_manifest.json` is currently an index, not a physical
  deliverable package.
