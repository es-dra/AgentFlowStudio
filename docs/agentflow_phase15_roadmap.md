# AgentFlow Phase 15 Roadmap

This document preserves the detailed Phase 15 history after the v0.1.0
AgentFlow Studio delivery closeout.

The short product roadmap stays in [`product_roadmap.md`](product_roadmap.md).
This file is the detailed AgentFlow Studio mainline record for contract-first
work after the AgentFlow Studio local-first CLI/Agent MVP.

## Scope

Phase 15 is contract-first and artifact-first.

It does not implement AgentFlow runtime, hosted services, or cross-module
execution. Phase 15 has:

- no Router runtime
- no skill runtime
- no Memory runtime
- no Web UI
- no hosted API, database, remote provider behavior, Python package rename,
  workflow rename, or CLI rename

## Phase 15 Summary

| Phase | Status | Focus |
| --- | --- | --- |
| Phase 15.1 | complete | AgentFlow Production mainline MVP |
| Phase 15.2 | complete | AgentFlow mainline contracts |
| Phase 15.3 | complete | AgentFlow Production review hardening |
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
| Phase 15.15 | complete | AgentFlow Package Skeleton |
| Phase 15.16 | complete | AgentFlow Contract Example Helpers |
| Phase 15.17a | complete | AgentFlow repo rename docs alignment |
| Phase 15.17 | complete | AgentFlow validator constants |
| Phase 15.18 | complete | Router dry-run validator migration |
| Phase 15.19 | complete | Skill replay validator migration |
| Phase 15.20 | complete | Intermediate Asset / Memory Validator |
| Phase 15.21 | complete | AgentFlow Production asset feedback loop smoke |
| Phase 15.22 | complete | AgentFlow Production asset feedback source validator |
| Phase 15.23 | complete | AgentFlow Production asset feedback review surface |
| Phase 15.24 | complete | AgentFlow Production asset feedback review harness |
| Phase 15.25 | complete | AgentFlow Production asset feedback review gate |
| Phase 15.26 | complete | AgentFlow Production asset reuse dry-run planner |
| Phase 15.27 | complete | AgentFlow Production asset reuse review surface |
| Phase 15.28 | complete | AgentFlow Production asset reuse chain fixtures |
| Phase 15.29 | complete | AgentFlow Production asset reuse chain audit smoke |

## Phase 15.1: AgentFlow Production Mainline MVP

Status: complete.

Purpose: add `AgentFlow Production` as a sibling production-side MVP module while
keeping `AgentFlow Studio` as the distribution-side module.

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
- fix the boundary between AgentFlow Production production-side artifacts and
  AgentFlow Studio distribution-side artifacts
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

## Phase 15.3: AgentFlow Production Review Hardening

Status: complete.

Purpose:

- strengthen `agentflow_production_handoff` inspect/review checks
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

- `agentflow_studio.harness.agentflow_router.validate_router_decision_dry_run`
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

- `agentflow_studio.harness.agentflow_skill.validate_skill_invocation_result_replay`
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
- keep `agentflow_production/` responsible for production-side handoff domain logic
- keep `agentflow_studio/` responsible for distribution-side media workflows,
  package review, and the current CLI path
- preserve compatibility imports before moving validators out of
  `agentflow_studio.harness`

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

## Phase 15.15: AgentFlow Package Skeleton

Status: complete.

Purpose: introduce the top-level `agentflow/` namespace before moving platform
contract helpers or validators.

Output:

- `agentflow/__init__.py`
- reserved namespace packages under `agentflow/contracts`, `agentflow/harness`,
  `agentflow/memory`, `agentflow/router`, and `agentflow/skills`
- import smoke tests proving the package exists and old validator imports still
  work from `agentflow_studio.harness`

Boundary:

- does not move validators
- does not move contracts
- does not change workflow execution
- does not change CLI behavior
- does not add Router runtime
- does not add skill runtime
- does not add Memory runtime
- does not add database, provider, hosted API, or Web UI behavior

## Phase 15.16: AgentFlow Contract Example Helpers

Status: complete.

Purpose: move pure AgentFlow contract example constants and JSON/JSONL loading
helpers into the new platform package.

Output:

- `agentflow.contracts.examples`
- `AGENTFLOW_CONTRACT_SCHEMA_VERSION`
- committed AgentFlow example path and artifact type constants
- read-only JSON/JSONL example loaders
- contract example tests now reuse the platform helper constants

Boundary:

- does not move validators
- does not move runtime behavior
- does not change artifact contracts
- does not change workflow execution
- does not change CLI behavior
- does not add Router runtime
- does not add skill runtime
- does not add Memory runtime
- does not add database, provider, hosted API, or Web UI behavior

## Phase 15.17a: AgentFlow Repo Rename Docs Alignment

Status: complete.

Purpose: align documentation after the repository container was renamed to
`AgentFlowStudio`.

Expected output:

- README and docs describe `AgentFlowStudio` as the platform repository
- AgentFlow Studio remains documented as the distribution-side module
- AgentFlow Production remains documented as the production-side module
- `agentflow/` remains documented as the platform contract and harness
  migration layer
- DEVLOG records that package, CLI, workflow, artifact, and version names are
  intentionally unchanged

Boundary:

- docs only
- does not rename Python packages
- does not rename CLI commands
- does not rename workflows or artifact contracts
- does not change version or tags
- does not change workflow execution
- does not add Router runtime, skill runtime, Memory runtime, database,
  provider behavior, hosted API, or Web UI behavior

## Phase 15.17: AgentFlow Validator Constants

Status: complete.

Purpose: migrate platform-level shared validator constants into
`agentflow.harness` while keeping actual validator behavior and compatibility
imports stable.

Output:

- `agentflow/harness/constants.py`
- shared schema version, result status strings, and forbidden fragment lists
- focused tests proving existing router and skill validators still behave the
  same
- `agentflow_studio.harness.agentflow_router` and
  `agentflow_studio.harness.agentflow_skill` import the shared constants while
  keeping their public validator functions in place

Boundary:

- no validator behavior migration yet
- no workflow changes
- no CLI changes
- no runtime behavior
- no package, workflow, artifact, or schema version rename

## Phase 15.18: Router Dry-run Validator Migration

Status: complete.

Purpose: move the Router dry-run validator implementation into
`agentflow.harness` while keeping the legacy AgentFlow Studio import path as a
compatibility wrapper.

Output:

- `agentflow.harness.agentflow_router.validate_router_decision_dry_run`
- `agentflow_studio.harness.agentflow_router` compatibility wrapper
- focused tests proving new platform imports and old compatibility imports
  reference the same validator function
- existing Router dry-run validator behavior remains unchanged

Boundary:

- does not migrate Skill replay validation
- does not implement Router runtime
- does not select skills from live requests
- does not execute skills or workflows
- does not write runtime state, long-term memory, database rows, or generated
  run artifacts
- does not change CLI, workflow execution, artifact contracts, schema version,
  provider behavior, hosted API, or Web UI behavior

## Phase 15.19: Skill Replay Validator Migration

Status: complete.

Purpose: move the Skill invocation/result replay validator implementation into
`agentflow.harness` while keeping the legacy AgentFlow Studio import path as a
compatibility wrapper.

Output:

- `agentflow.harness.agentflow_skill.validate_skill_invocation_result_replay`
- `agentflow_studio.harness.agentflow_skill` compatibility wrapper
- focused tests proving new platform imports and old compatibility imports
  reference the same validator function
- existing Skill replay validator behavior remains unchanged

Boundary:

- does not implement skill runtime
- does not invoke skills
- does not execute workflows
- does not call local or remote providers
- does not write runtime state, long-term memory, database rows, or generated
  run artifacts
- does not change CLI, workflow execution, artifact contracts, schema version,
  provider behavior, hosted API, or Web UI behavior

## Phase 15.20: Intermediate Asset / Memory Validator

Status: complete.

Purpose: add a narrow validation surface for committed or provided
intermediate asset, reusable asset profile, asset reuse decision, memory
candidate, and memory promotion decision artifacts.

Output:

- `agentflow.memory.assets.validate_asset_memory_contract_set`
- `agentflow_asset_memory_validation` result shape
- focused tests for the current asset/memory examples and failure boundaries
- `agentflow.memory` package metadata updated to platform memory helper layer
  while keeping runtime status `not_implemented`

Boundary:

- validates existing in-memory artifact payloads only
- does not implement Memory runtime
- does not promote candidate memory
- does not write long-term memory
- does not create reusable asset profiles
- does not execute workflows, skills, Router decisions, providers, database
  writes, vector-store writes, or file repository writes
- does not change CLI, workflow execution, artifact contracts, schema version,
  hosted API, or Web UI behavior

## Phase 15.21: AgentFlow Production Asset Feedback Loop Smoke

Status: complete.

Purpose: prove that a current AgentFlow Production production handoff run can be
adapted into the AgentFlow asset/memory contract set and validated through the
platform memory helper layer.

Output:

- `agentflow.memory.agentflow_production_assets.build_agentflow_production_asset_memory_contract_set`
- focused smoke tests that run the local AgentFlow Production workflow in `tmp_path`,
  build the in-memory contract set from `production_handoff.json`,
  `memory_candidates.json`, `feedback_signal_log.json`, and
  `cost_quality_trace.json`, and validate it with
  `agentflow.memory.assets.validate_asset_memory_contract_set`

Boundary:

- validates a smoke contract loop only
- does not implement Memory runtime
- does not execute durable candidate promotion
- does not write long-term memory
- does not persist reusable asset profiles
- does not read from or write to `data/processed/runs/`
- does not change CLI or workflow execution
- does not execute skills, Router decisions, providers, database writes,
  vector-store writes, hosted APIs, or Web UI behavior

## Phase 15.22: AgentFlow Production Asset Feedback Source Validator

Status: complete.

Purpose: validate the AgentFlow Production source payloads used by the asset-feedback
smoke adapter before mapping them into AgentFlow asset/memory contracts.

Output:

- `agentflow.memory.agentflow_production_assets.validate_agentflow_production_asset_feedback_sources`
- focused tests that reject malformed candidate stores, primary feedback-store
  misuse, non-local cost traces, and incomplete production handoff artifact
  references

Boundary:

- validates existing in-memory AgentFlow Production source payloads only
- does not execute workflows
- does not build or persist reusable asset profiles
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact contracts, schema version,
  provider behavior, hosted API, database/vector-store writes, or Web UI
  behavior

## Phase 15.23: AgentFlow Production Asset Feedback Review Surface

Status: complete.

Purpose: compose the AgentFlow Production source-payload validator, asset/memory smoke
adapter, and AgentFlow asset/memory contract-set validator into one
Agent-readable in-memory review artifact.

Output:

- `agentflow.memory.agentflow_production_review.review_agentflow_production_asset_feedback_loop`
- `agentflow_production_asset_feedback_review` result shape
- focused tests that prove valid current AgentFlow Production workflow outputs pass
  the composed review and invalid source payloads stop before contract-set
  adaptation

Boundary:

- returns a review artifact only
- validates existing in-memory AgentFlow Production source payloads only
- does not execute workflows
- does not build or persist reusable asset profiles outside the returned
  in-memory contract-set review
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact contracts, schema version,
  provider behavior, hosted API, database/vector-store writes, or Web UI
  behavior

## Phase 15.24: AgentFlow Production Asset Feedback Review Harness

Status: complete.

Purpose: add a harness-level validator for the
`agentflow_production_asset_feedback_review` artifact so Agents can inspect
the composed review result without re-running workflows or rebuilding contract
sets.

Output:

- `agentflow.harness.agentflow_production_review.validate_agentflow_production_asset_feedback_review`
- `agentflow_production_asset_feedback_review_validation` result shape
- committed validation example and contract registry/audit coverage
- focused tests for valid review artifacts, runtime-claim rejection,
  source-failure step consistency, and private path/secret rejection

Boundary:

- validates an existing in-memory review artifact only
- does not call the AgentFlow Production workflow
- does not rebuild source validation, asset-memory contract sets, or reusable
  profiles
- does not implement Memory runtime
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior

## Phase 15.25: AgentFlow Production Asset Feedback Review Gate

Status: complete.

Purpose: convert an existing
`agentflow_production_asset_feedback_review_validation` artifact into a
decision-only gate result that tells a later Agent whether asset reuse planning
may proceed or source artifacts must be repaired first.

Output:

- `agentflow.harness.agentflow_production_review.gate_agentflow_production_asset_feedback_review`
- `agentflow_production_asset_feedback_review_gate` result shape
- committed gate example and contract registry/audit coverage
- focused tests for passed validation, failed validation blocking, and runtime
  or memory-write claim rejection

Boundary:

- gates an existing in-memory review validation artifact only
- does not call the AgentFlow Production workflow
- does not rebuild source validation, review artifacts, asset-memory contract
  sets, or reusable profiles
- does not implement Memory runtime
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior

## Phase 15.26: AgentFlow Production Asset Reuse Dry-run Planner

Status: complete.

Purpose: convert a passed
`agentflow_production_asset_feedback_review_gate` plus its existing review
artifact into a dry-run reuse plan that a later Agent can inspect before any
actual reuse attempt.

Output:

- `agentflow.memory.agentflow_production_reuse.plan_agentflow_production_asset_reuse_dry_run`
- `agentflow_production_asset_reuse_dry_run_plan` result shape
- committed dry-run plan example and contract registry/audit coverage
- focused tests for ready planning, blocked gate handling, and runtime or
  memory-write claim rejection

Boundary:

- plans from existing in-memory review and gate artifacts only
- does not execute asset reuse
- does not call the AgentFlow Production workflow
- does not rebuild source validation, review artifacts, asset-memory contract
  sets, reusable profiles, or promotion decisions
- does not implement Memory runtime
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior

## Phase 15.27: AgentFlow Production Asset Reuse Review Surface

Status: complete.

Purpose: review an existing AgentFlow Production asset-feedback/reuse chain after
dry-run planning so a later Agent can inspect whether reuse remains blocked,
failed, or ready for human review without executing the task.

Output:

- `agentflow.memory.agentflow_production_reuse_review.review_agentflow_production_asset_reuse_dry_run_chain`
- `agentflow_production_asset_reuse_review` result shape
- committed reuse-review example and contract registry/audit coverage
- focused tests for ready chains, blocked gates, mismatched chain ids, and
  runtime or long-term-memory-write claim rejection

Boundary:

- reviews existing in-memory review, validation, gate, and dry-run plan
  artifacts only
- does not execute asset reuse
- does not call the AgentFlow Production workflow
- does not rebuild source validation, review artifacts, asset-memory contract
  sets, reusable profiles, promotion decisions, gates, or dry-run plans
- does not implement Memory runtime
- does not execute durable candidate promotion
- does not write long-term memory
- does not read from or write to `data/processed/runs/`
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior

## Phase 15.28: AgentFlow Production Asset Reuse Chain Fixtures

Status: complete.

Purpose: provide one reusable pure in-memory fixture builder for the existing
AgentFlow Production asset-feedback/reuse chain so future tests can exercise the
review, validation, gate, dry-run plan, and final review surface together
without repeating setup code.

Output:

- `agentflow.memory.agentflow_production_reuse_chain.build_agentflow_production_asset_reuse_dry_run_chain`
- focused tests for ready chains, failed-review blocking, and no-execute /
  no-memory-write boundaries

Boundary:

- builds existing in-memory artifact payloads only
- does not define a new contract artifact type
- does not execute asset reuse
- does not call the AgentFlow Production workflow
- does not read from or write to run directories
- does not persist reusable profiles or write long-term memory
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior

## Phase 15.29: AgentFlow Production Asset Reuse Chain Audit Smoke

Status: complete.

Purpose: add a narrow smoke audit for the fixture-built AgentFlow Production
asset-feedback/reuse chain so future changes cannot quietly turn the fixture
path into runtime behavior or a new contract surface.

Output:

- `agentflow.memory.agentflow_production_reuse_audit.audit_agentflow_production_asset_reuse_chain_fixture`
- focused tests for ready chains, blocked chains, runtime-claim rejection, and
  unexpected contract-surface rejection

Boundary:

- audits existing fixture-built in-memory artifact payloads only
- does not register a new contract artifact type
- does not execute asset reuse
- does not call the AgentFlow Production workflow
- does not read from or write to run directories
- does not persist reusable profiles or write long-term memory
- does not change CLI, workflow execution, artifact schema version, provider
  behavior, hosted API, database/vector-store writes, or Web UI behavior
