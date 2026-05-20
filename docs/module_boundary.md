# Module Boundary

This document defines the current module responsibilities inside the
`NarratoCut` repository after the NarratoStudio MVP merge.

The repository name is unchanged. NarratoCut and NarratoStudio are sibling MVP
modules used to validate AgentFlow Studio's distribution-side and
production-side contract surfaces.

## NarratoStudio

Owns:

- production-side structured handoff contracts
- deterministic creative-brief to handoff SOP logic
- production handoff report rendering
- NarratoStudio workflow node implementations
- NarratoStudio quality profile checks

Consumes:

- `creative_brief.json`
- optional future `feedback.jsonl` inputs for derived feedback signals

Emits:

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
- standard run artifacts such as `manifest.json`, `run_manifest.json`, and
  `trace.json`

Out of scope:

- finished video generation
- visual asset generation
- distribution packaging
- posting or publishing
- long-term memory writes
- Agent runtime
- Web UI

## NarratoCut

Owns:

- distribution-side highlight selection and clip planning
- real local slicing and final video assembly workflows
- subtitles, cover, BGM, and finished package indexing
- package reports and delivery readiness
- run inspection and review surfaces for distribution artifacts

Consumes:

- source video files
- transcripts
- scripts
- `clip_plan.json`
- existing final videos or local media artifacts
- future production outputs after they are converted into concrete media inputs

Emits:

- `highlight_plan.json`
- `clip_plan.json`
- `real_slice_manifest.json`
- `final_video_manifest.json`
- `finished_package_manifest.json`
- `package_report.md`
- `quality_report.json`
- `review_report.json`
- `delivery_readiness.json`
- `delivery_readiness.md`

Out of scope:

- production-side story bible or scene planning
- long-form creative development
- AgentFlow Router runtime
- AgentFlow Memory runtime
- hosted user accounts or publishing integrations

## Cross-Module Boundary

NarratoStudio does not directly call NarratoCut workflows.

NarratoCut does not directly interpret story or prompt artifacts as final media.
If a future workflow connects the modules, it should pass through explicit
handoff artifacts and concrete media or plan inputs.

Recommended future bridge:

```text
NarratoStudio production_handoff.json
-> production execution or asset generation layer
-> source video / clips / final media
-> NarratoCut distribution package workflow
```

The bridge is not implemented in Phase 15.2.
