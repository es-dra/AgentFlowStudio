# Module Boundary

This document defines the current module responsibilities inside the
`AgentFlowStudio` repository after the container rename.

The repository container is now `AgentFlowStudio`. The Python package names,
CLI commands, workflow files, and module artifact contracts are intentionally
unchanged in this phase. AgentFlow Studio and AgentFlow Production remain sibling MVP
modules used to validate AgentFlow Studio's distribution-side and
production-side contract surfaces, while `agentflow/` owns platform contract
helpers as they migrate out of module-specific locations.

## AgentFlow

Owns:

- platform contract constants and example loaders
- shared platform harness helpers as they are migrated
- Router, Memory, and Skill contract boundaries before runtime implementation
- compatibility guidance for module-owned imports during migration

Consumes:

- committed AgentFlow contract examples
- module-produced artifacts when a platform-level validator explicitly targets
  them

Emits:

- static contract helper outputs and validation result shapes only

Out of scope:

- workflow orchestration
- media execution
- production handoff generation
- long-term memory writes
- Router runtime, Memory runtime, or skill runtime
- hosted API, database, provider calls, or Web UI

## AgentFlow Production

Owns:

- production-side structured handoff contracts
- deterministic creative-brief to handoff SOP logic
- production handoff report rendering
- AgentFlow Production workflow node implementations
- AgentFlow Production quality profile checks

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

## AgentFlow Studio

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

AgentFlow Production does not directly call AgentFlow Studio workflows.

AgentFlow Studio does not directly interpret story or prompt artifacts as final media.
If a future workflow connects the modules, it should pass through explicit
handoff artifacts and concrete media or plan inputs.

Recommended future bridge:

```text
AgentFlow Production production_handoff.json
-> production execution or asset generation layer
-> source video / clips / final media
-> AgentFlow Studio distribution package workflow
```

The bridge is not implemented in Phase 15.2.
