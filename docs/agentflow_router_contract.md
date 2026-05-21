# AgentFlow Router Contract

AgentFlow Router is the future platform layer that decides which skill is most
appropriate for a task.

Phase 15.5 defines only the decision artifact. It does not implement a Router
runtime, skill runtime, permission engine, workflow execution, database, or
cross-module task execution.

Phase 15.11 adds local dry-run validation for committed or provided Router
decision artifacts. This still does not implement Router runtime: it validates
that a decision is well formed and decision-only, but it does not select a skill
from a live request, execute a skill, call a workflow, or write runtime state.

## Router Purpose

A Router decision should answer:

- What did the user or Agent ask for?
- Which skill was selected?
- Why was it selected?
- Which candidate skills were rejected?
- Why were they rejected?
- Has anything been executed?

For Phase 15.5, the answer to the last question must be no. Router output is a
decision record only.

## Router Decision Artifact

`agentflow_router_decision` records skill selection reasoning. It must not claim
that a skill has already run.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_router_decision`.
- `decision_id`: stable decision id.
- `project_id`: project or workspace id.
- `request_summary`: concise task summary.
- `selected_skill_id`: chosen skill contract id.
- `selection_reason`: why this skill fits the request.
- `rejected_candidate_skills`: candidate skills that were considered but not
  selected, each with `skill_id` and `reason`.
- `execution_status`: `decision_only`.
- `executes_skill`: must be `false`.

See
[`../examples/agentflow/router_decision.example.json`](../examples/agentflow/router_decision.example.json).

## Review Rules

Router decisions are reviewable artifacts. Review should check:

- the selected skill exists as a known skill contract
- the selection reason matches the request
- rejected candidates include clear reasons
- the decision does not claim execution
- no private path, secret, generated media, or local run artifact is embedded
  in the example contract

## Dry-run Validation Artifact

`agentflow_router_dry_run_validation` records the local validation result for a
Router decision artifact. It is a harness validation surface, not Router
runtime output.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_router_dry_run_validation`.
- `validation_scope`: `router_decision_dry_run`.
- `runtime_status`: `not_implemented`.
- `does_not_execute`: must be `true`.
- `decision_id`: validated decision id.
- `selected_skill_id`: selected skill id from the decision artifact.
- `overall_status`: `passed` or `failed`.
- `checks`: per-check validation results.

The current dry-run validator checks schema version, artifact type, selected
skill presence, known skill ids, request summary, selection reason, rejected
candidate reasons, selected skill exclusion from rejected candidates,
decision-only execution status, `executes_skill: false`, and private path or
secret fragments.

## Boundaries

Router must not:

- execute a workflow
- call a model or provider
- write long-term memory
- mutate project artifacts
- publish content
- bypass skill quality gates

Skill execution, permissions, retries, approvals, and cross-module orchestration
remain future runtime work.
