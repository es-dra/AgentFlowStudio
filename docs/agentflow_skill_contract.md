# AgentFlow Skill Contract

AgentFlow Skills describe tasks that an agent can plan, execute, inspect, and
review through artifacts.

Phase 15.5 strengthens the contract shape for planned skill calls and skill
results. It does not implement a skill runtime, permission engine, marketplace,
or Router execution runtime.

Phase 15.12 adds local replay validation for a committed or provided skill
invocation/result pair. This still does not implement a skill runtime: it
validates that a result matches the planned invocation and quality-gate
expectations, but it does not invoke a skill, execute a workflow, call a
provider, or write runtime state.

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

## Skill Invocation Artifact

`agentflow_skill_invocation` records that an Agent plans to call a skill. It is
an auditable plan, not proof that execution already happened.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_skill_invocation`.
- `invocation_id`: stable id for the planned call.
- `project_id`: project or workspace id.
- `skill_id`: selected skill contract id.
- `requested_by`: agent, human, or external system.
- `execution_status`: `planned` for the current contract example.
- `input_artifacts`: artifact paths or ids the skill will consume.
- `expected_output_artifacts`: expected result artifacts.
- `quality_gates`: gates that must run after execution.
- `allowed_side_effects`: permitted side effects for this call.
- `forbidden_side_effects`: side effects the skill must not perform.

See
[`../examples/agentflow/skill_invocation.example.json`](../examples/agentflow/skill_invocation.example.json).

## Skill Result Artifact

`agentflow_skill_result` records the outcome summary after a skill run. It
should point to artifacts and review evidence instead of duplicating the full
run output.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_skill_result`.
- `result_id`: stable result id.
- `invocation_id`: matching skill invocation id.
- `project_id`: project or workspace id.
- `skill_id`: executed skill contract id.
- `execution_status`: `succeeded`, `failed`, or `blocked`.
- `output_artifacts`: artifacts emitted by the skill.
- `quality_gate_status`: status for required gates, such as `inspect_run` and
  `review_run`.
- `review_artifacts`: quality or review reports that support the result.
- `writes_long_term_memory`: whether execution wrote durable memory. Current
  examples keep this `false`.

See
[`../examples/agentflow/skill_result.example.json`](../examples/agentflow/skill_result.example.json).

## Quality Gates

Skill execution should leave enough evidence for later review. A result may be
blocked or failed even if some artifacts exist.

Current gate status values:

- `passed`
- `failed`
- `not_run`

Markdown reports can support human review, but strong contract checks should
remain on machine-readable artifacts and review reports.

## Replay Validation Artifact

`agentflow_skill_replay_validation` records the local validation result for a
skill invocation/result pair. It is a harness validation surface, not skill
runtime output.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_skill_replay_validation`.
- `validation_scope`: `skill_invocation_result_replay`.
- `runtime_status`: `not_implemented`.
- `does_not_execute`: must be `true`.
- `invocation_id`: validated invocation id.
- `result_id`: validated result id.
- `skill_id`: skill id from the planned invocation.
- `overall_status`: `passed` or `failed`.
- `checks`: per-check validation results.

The current replay validator checks schema version, artifact type, invocation
id, project id, skill id, planned invocation status, result status, expected
output coverage, quality gate status coverage, passing required gates, review
artifact declaration, `writes_long_term_memory: false`, and private path or
secret fragments.

The implementation entry point for new code is
`agentflow.harness.agentflow_skill.validate_skill_invocation_result_replay`.
`agentflow_studio.harness.agentflow_skill` remains a compatibility import wrapper for
the first migration window.

## Current Skill Surfaces

Current repository skill files remain under [`../skills`](../skills/README.md).

Important current skills:

- `short_highlight_package.skill.yaml`
- `video_script_highlight_package.skill.yaml`
- `agentflow_production_handoff.skill.yaml`

These are agent-readable contracts, not a full skill runtime.

## Forbidden Side Effects

Forbidden side effects must be explicit in skill contracts and invocations.
Typical forbidden side effects include:

- remote model calls without explicit opt-in
- publishing or uploading content
- writing long-term memory without a promotion decision
- committing generated media or local run artifacts
- changing Router, Memory, CLI, or workflow behavior as a hidden side effect

## Boundaries

Skills should not:

- silently call remote providers
- write long-term memory without a promotion decision
- publish content
- commit generated media
- treat derived feedback as raw feedback
- bypass `inspect-run` or `review-run` when quality gates are defined

AgentFlow Router may later select a skill, but a Router decision is still a
separate decision artifact. It does not execute the skill by itself.
