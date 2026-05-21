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

Status: complete.

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

## Phase 15.3: NarratoStudio Review Hardening

Status: complete.

Purpose:

- strengthen `narratostudio_production_handoff` inspect/review checks after the
  first NarratoStudio MVP merge
- keep strong consistency checks on JSON artifacts, not on the Markdown report
- make broken outline/scene/shot/prompt/handoff references visible before later
  AgentFlow runtime or UI work consumes the artifacts

Planned checks:

- outline beats referenced by scenes and covered by at least one scene
- scenes referenced by shots and covered by at least one shot
- shots referenced by prompts and covered by at least one prompt
- `production_handoff.json` core artifact IDs match upstream artifacts
- `production_handoff.json` artifact reference map includes required core
  artifact paths
- `production_report.md` has only light identity checks as a human review view

Boundary:

- no workflow generation logic changes
- no CLI changes
- no package rename
- no Router, Memory, or skill runtime
- no Web UI
- no remote model calls

## Phase 15.4: AgentFlow Memory Signal Contracts

Status: complete.

Purpose:

- deepen the feedback, memory candidate, promotion decision, and cost-quality
  signal contracts before any Memory runtime work
- prevent Agents from treating derived feedback signals or candidate memories as
  durable project memory
- keep memory evolution reviewable through explicit evidence and promotion
  decisions

Expected examples:

- `examples/agentflow/memory_candidate.example.json`
- `examples/agentflow/memory_promotion_decision.example.json`

Boundary:

- contract docs and examples only
- no workflow changes
- no CLI changes
- no database or vector store
- no automatic long-term memory writes
- no Router, Memory, or skill runtime

## Phase 15.5: AgentFlow Skill / Router Contract Layer

Status: complete.

Purpose:

- define the minimum contract layer for skill invocation, skill result, and
  Router decision artifacts
- make skill selection reviewable before implementing any Router runtime
- keep skill execution boundaries explicit through quality gates and forbidden
  side effects

Expected documents:

- `docs/agentflow_skill_contract.md`
- `docs/agentflow_router_contract.md`

Expected examples:

- `examples/agentflow/skill_invocation.example.json`
- `examples/agentflow/skill_result.example.json`
- `examples/agentflow/router_decision.example.json`

Boundary:

- contract docs and examples only
- no workflow changes
- no CLI changes
- no Python runtime changes
- no Pydantic schema package
- no Router runtime
- no skill runtime
- no permission system
- no cross-module execution
- no Web UI

## Phase 15.6: AgentFlow Contract Registry / Validation Layer

Status: complete.

Purpose:

- add a lightweight discovery registry for current AgentFlow contract examples
- make artifact types, example paths, docs, and validation rules explicit
- help future Agents find the right contract before any runtime work exists

Expected documents:

- `docs/agentflow_contract_registry.md`

Expected examples:

- `examples/agentflow/contract_registry.example.json`

Boundary:

- contract docs, examples, and tests only
- no workflow changes
- no CLI changes
- no Python runtime changes
- no Pydantic schema package
- no registry service
- no Router runtime
- no skill runtime
- no Memory runtime
- no database or cross-module execution

## Phase 15.7: AgentFlow Contract Audit Gate

Status: complete.

Purpose:

- add a static audit report example for committed AgentFlow contracts
- prevent registry, example, doc, and boundary drift before runtime work
- keep Router, Memory, Skill, and cost-quality semantics reviewable

Output:

- `docs/agentflow_contract_validation.md`
- `examples/agentflow/contract_audit_report.example.json`

Boundary:

- static docs, examples, and tests only; no workflow, CLI, Python runtime,
  runtime validator, registry service, Router runtime, skill runtime, Memory
  runtime, database, or cross-module execution

## Phase 15.8: AgentFlow PR Review Checklist

Status: in progress.

Purpose: add `docs/agentflow_pr_review_checklist.md` so contract PRs keep
schema, artifact, semantic boundary, and verification checks consistent.

Boundary: docs/tests only; no workflow, CLI, Python runtime, CI config, runtime
validator, registry service, Router/skill/Memory runtime, database, Web UI, or
cross-module execution.
