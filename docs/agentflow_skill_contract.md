# AgentFlow Skill Contract

AgentFlow Skills describe tasks that an agent can plan, execute, inspect, and
review through artifacts.

Phase 15.2 only defines the contract shape. It does not implement a skill
runtime, permission engine, marketplace, or Router.

## Skill Contract Purpose

A skill contract should answer:

- When should an agent use this skill?
- What artifacts does it require?
- What artifacts does it emit?
- Which workflow or command is the recommended execution path?
- Which quality gates must run after execution?
- Which side effects are forbidden?

## Minimal Fields

- `id`: stable skill id.
- `name`: human-readable name.
- `schema_version`: contract version.
- `module`: owning module.
- `status`: draft, mvp, stable, or deprecated.
- `description`: concise task description.
- `primary_workflow`: optional workflow path.
- `input_artifacts`: required and optional inputs.
- `output_artifacts`: expected outputs.
- `quality_gates`: inspect/review commands or profiles.
- `allowed_side_effects`: local file writes, media reads, network calls, etc.
- `forbidden_side_effects`: remote calls, memory writes, publishing, etc.
- `when_to_use`: agent routing hints.
- `when_not_to_use`: boundaries and non-goals.
- `failure_recovery`: common recovery guidance.

## Current Skill Surfaces

Current repository skill files remain under [`../skills`](../skills/README.md).

Important current skills:

- `video_highlight_package.skill.yaml`
- `video_script_highlight_package.skill.yaml`
- `narratostudio_production_handoff.skill.yaml`

These are agent-readable contracts, not a full skill runtime.

## Boundaries

Skills should not:

- silently call remote providers
- write long-term memory without a promotion decision
- publish content
- commit generated media
- treat derived feedback as raw feedback
- bypass `inspect-run` or `review-run` when quality gates are defined

AgentFlow Router may later select a skill, but Router runtime design is outside
Phase 15.2.
