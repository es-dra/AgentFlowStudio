# AgentFlow Phase 15 Roadmap

This document preserves the detailed Phase 15 history after the v0.1.0
NarratoCut delivery closeout.

The short product roadmap stays in [`product_roadmap.md`](product_roadmap.md).
This file is the detailed AgentFlow Studio mainline record for contract-first
work after the NarratoCut local-first CLI/Agent MVP.

## Scope

Phase 15 is contract-first and artifact-first.

It does not implement AgentFlow runtime, hosted services, or cross-module
execution. Phase 15 has:

- no Router runtime
- no skill runtime
- no Memory runtime
- no Web UI
- no hosted API, database, remote provider behavior, repository rename, or CLI rename

## Phase 15 Summary

| Phase | Status | Focus |
| --- | --- | --- |
| Phase 15.1 | complete | NarratoStudio mainline MVP |
| Phase 15.2 | complete | AgentFlow mainline contracts |
| Phase 15.3 | complete | NarratoStudio review hardening |
| Phase 15.4 | complete | Memory signal contracts |
| Phase 15.5 | complete | Skill and Router contracts |
| Phase 15.6 | complete | Contract registry |
| Phase 15.7 | complete | Contract audit gate |
| Phase 15.8 | complete | Contract PR review checklist |
| Phase 15.9 | complete | Roadmap document split |
| Phase 15.10 | complete | Runtime readiness spike |
| Phase 15.11 | complete | Router dry-run decision validator |
| Phase 15.12 | complete | Skill Invocation / Result Replay Validator |
| Phase 15.13 | complete | Intermediate Asset & Memory Architecture Plan |
| Phase 15.14 | complete | Architecture Refactor Plan |

## Phase 15.1: NarratoStudio Mainline MVP

Status: complete.

Purpose: add `NarratoStudio` as a sibling production-side MVP module while
keeping `NarratoCut` as the distribution-side module.

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

Boundary: local deterministic generation only; no remote LLM, Agent runtime,
database, Web UI implementation, or migration from reference UI projects.

## Phase 15.2: AgentFlow Mainline Contracts

Status: complete.

Purpose:

- define the top-level AgentFlow Studio contract layer before runtime work
- fix the boundary between NarratoStudio production-side artifacts and
  NarratoCut distribution-side artifacts
- document feedback, memory candidate, artifact map, and skill contract shapes

Outputs:

- `docs/agentflow_studio_architecture.md`
- `docs/module_boundary.md`
- `docs/agentflow_artifact_map.md`
- `docs/agentflow_memory_contract.md`
- `docs/agentflow_skill_contract.md`
- `examples/agentflow/project_manifest.example.json`
- `examples/agentflow/artifact_map.example.json`
- `examples/agentflow/feedback_event.example.jsonl`

Boundary:

- documentation and minimal examples only
- no workflow changes
- no CLI changes
- no package rename or tag changes
- no AgentFlow Router runtime
- no AgentFlow Memory runtime
- no skill runtime
- no Web UI

## Phase 15.3: NarratoStudio Review Hardening

Status: complete.

Purpose:

- strengthen `narratostudio_production_handoff` inspect/review checks
- keep strong consistency checks on JSON artifacts, not Markdown reports
- make broken outline, scene, shot, prompt, and handoff references visible

Checks:

- outline beats referenced by scenes and covered by at least one scene
- scenes referenced by shots and covered by at least one shot
- shots referenced by prompts and covered by at least one prompt
- `production_handoff.json` core artifact IDs match upstream artifacts
- `production_handoff.json` artifact refs include required core paths
- `production_report.md` receives only light identity checks

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

- deepen feedback, memory candidate, promotion decision, and cost-quality signal
  contracts before Memory runtime work
- prevent Agents from treating derived feedback signals or candidate memories as
  durable project memory
- keep memory evolution reviewable through evidence and promotion decisions

Outputs:

- `docs/agentflow_memory_contract.md`
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
- make skill selection reviewable before implementing Router runtime
- keep skill execution boundaries explicit through quality gates and forbidden
  side effects

Outputs:

- `docs/agentflow_skill_contract.md`
- `docs/agentflow_router_contract.md`
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
- help future Agents find the right contract before runtime work exists

Outputs:

- `docs/agentflow_contract_registry.md`
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

Outputs:

- `docs/agentflow_contract_validation.md`
- `examples/agentflow/contract_audit_report.example.json`

Boundary:

- static docs, examples, and tests only
- no workflow changes
- no CLI changes
- no Python runtime changes
- no runtime validator
- no registry service
- no Router runtime
- no skill runtime
- no Memory runtime
- no database or cross-module execution

## Phase 15.8: AgentFlow PR Review Checklist

Status: complete.

Purpose:

- add a human review checklist for AgentFlow contract PRs
- keep schema, artifact, semantic boundary, and verification checks consistent
- avoid treating docs or tests as runtime validation

Outputs:

- `docs/agentflow_pr_review_checklist.md`
- `tests/test_agentflow_pr_review_checklist.py`

Boundary:

- docs and tests only
- no workflow changes
- no CLI changes
- no Python runtime changes
- no CI config changes
- no runtime validator
- no registry service
- no Router runtime
- no skill runtime
- no Memory runtime
- no database
- no Web UI
- no cross-module execution

## Phase 15.9: AgentFlow Roadmap Document Split

Status: complete.

Purpose:

- keep the main product roadmap short enough to review
- preserve the Phase 15 contract-layer history in this dedicated document
- make docs navigation point reviewers to the right level of detail

Boundary:

- docs and tests only
- no workflow changes
- no CLI changes
- no runtime validator
- no Router runtime
- no skill runtime
- no Memory runtime
- no Web UI

## Phase 15.10: AgentFlow Runtime Readiness Spike

Status: complete.

Purpose: define when AgentFlow runtime work is allowed to start through
contract, artifact, review, feedback/memory, cost-quality, and operations
gates.

Output: `docs/agentflow_runtime_readiness.md`
Boundary: docs/tests only; no workflow, CLI, runtime validator, Router runtime,
skill runtime, Memory runtime, or Web UI.

## Phase 15.11: AgentFlow Router Dry-run Decision Validator

Status: complete.

Purpose: add the first narrow runtime-readiness validation surface for existing
Router decision artifacts.

Output:

- `narratocut.harness.agentflow_router.validate_router_decision_dry_run`
- `agentflow_router_dry_run_validation` result shape
- focused regression tests for decision-only Router validation

Boundary:

- validates an existing `agentflow_router_decision`
- does not select skills from live requests
- does not execute skills
- does not execute workflows
- does not write runtime state, long-term memory, database rows, or generated
  run artifacts
- does not add CLI commands, hosted APIs, Web UI, or remote provider behavior

## Phase 15.12: AgentFlow Skill Invocation / Result Replay Validator

Status: complete.

Purpose: add a narrow replay validation surface for existing skill invocation
and skill result artifacts.

Output:

- `narratocut.harness.agentflow_skill.validate_skill_invocation_result_replay`
- `agentflow_skill_replay_validation` result shape
- focused regression tests for skill invocation/result alignment

Boundary:

- validates existing `agentflow_skill_invocation` and `agentflow_skill_result`
  artifacts
- does not invoke skills
- does not execute workflows
- does not call local or remote providers
- does not write runtime state, long-term memory, database rows, or generated
  run artifacts
- does not add CLI commands, hosted APIs, Web UI, or cross-module execution

## Phase 15.13: AgentFlow Intermediate Asset & Memory Architecture Plan

Status: complete.

Purpose: define how Agent execution artifacts become reviewable intermediate
assets and, after explicit promotion, reusable asset profiles.

Output:

- `docs/agentflow_intermediate_asset_architecture.md`
- `agentflow_intermediate_asset` example
- `agentflow_reusable_asset_profile` example
- `agentflow_asset_reuse_decision` example
- registry and static audit coverage for the new contract surfaces

Boundary:

- docs, examples, and tests only
- does not implement Memory runtime
- does not implement Router runtime
- does not implement skill runtime
- does not implement database, vector store, cache service, or file repository
- does not change CLI or workflow execution
- does not call local or remote providers

## Phase 15.14: AgentFlow Architecture Refactor Plan

Status: complete.

Purpose: define the architecture refactor sequence before moving contracts or
validators into a platform package.

Output:

- `docs/agentflow_architecture_refactor_plan.md`

Recommended target:

- add a future top-level `agentflow/` package for the platform contract layer
- keep `narratostudio/` responsible for production-side handoff domain logic
- keep `narratocut/` responsible for distribution-side media workflows,
  package review, and the current CLI path
- preserve compatibility imports before moving validators out of
  `narratocut.harness`

Boundary:

- docs and tests only
- does not create the `agentflow/` package
- does not move Python modules
- does not change workflow execution
- does not rename repository or CLI
- does not add Router runtime
- does not add skill runtime
- does not add Memory runtime
- does not merge or modify the Web UI branch
