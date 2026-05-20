# AgentFlow Studio Architecture

AgentFlow Studio is an agent-native content production and distribution
workflow platform.

This repository still keeps the `NarratoCut` name. In this repository,
AgentFlow Studio is represented only by MVP module contracts and local-first
workflow artifacts. This document records the platform direction; it does not
define a hosted runtime, database, Web UI, or Agent runtime.

## Product Principle

AgentFlow Studio follows this operating logic:

```text
Agent executes tasks. The product preserves reusable assets.
The user decides. The system records, summarizes, and reuses the decision.
```

The platform moat is not model access. The durable asset is the structured
history of what agents did, what artifacts were produced, what users accepted
or rejected, and which execution strategy worked for which scenario.

## Current Modules

### NarratoStudio

NarratoStudio is the production-side MVP module.

Current role:

- turns a creative brief into a structured production handoff
- emits machine-readable production artifacts
- emits a human-readable production report
- emits candidate memory and local execution trace artifacts

Current recommended workflow:

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

### NarratoCut

NarratoCut is the distribution-side MVP module.

Current role:

- consumes existing videos, transcripts, scripts, clip plans, and package inputs
- produces highlight clips, finished package indexes, reports, and review
  artifacts
- preserves local-first delivery and acceptance evidence

Current product surface:

```text
video / transcript / clip_plan
-> highlight_plan
-> clip_plan.json
-> real clips
-> final_video.mp4
-> subtitles / cover / bgm
-> finished_package_manifest.json
-> package_report.md
-> inspect/review
```

## Platform Contract Layer

The current mainline should treat these as contract surfaces:

- project manifest: project-level index and intent
- artifact map: cross-module artifact registry
- feedback event: raw user or external feedback
- feedback signal: derived interpretation for one run
- memory candidate: proposed reusable knowledge
- promotion decision: explicit acceptance, rejection, merge, or expiration of a
  memory candidate
- skill contract: agent-readable task capability description

These contracts are intentionally local-first and file-based in this phase.

## Non-Goals

Phase 15.2 does not implement:

- AgentFlow Router runtime
- AgentFlow Memory runtime
- skill runtime or tool permission engine
- cross-module execution
- database storage
- hosted API
- Web UI
- remote LLM, I2V, or T2V execution
- repository or CLI renaming

## Next Development Order

Recommended mainline order:

1. Stabilize platform contract docs and minimal examples.
2. Strengthen NarratoStudio review gates around JSON artifact references.
3. Deepen feedback, memory candidate, and cost-quality trace contracts.
4. Only then extract broader AgentFlow Skills, Router, and Memory runtime
   designs.
