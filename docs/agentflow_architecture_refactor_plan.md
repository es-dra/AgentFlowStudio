# AgentFlow Architecture Refactor Plan

Phase 15.14 defines the next architecture refactor before any package moves.

This is a planning artifact only. It does not move Python modules, does not
change workflow execution, does not add Router runtime, does not add skill
runtime, does not add Memory runtime, and does not rename the CLI.

Planning boundary:

- Phase 15.14 does not move Python modules.
- Phase 15.14 does not change workflow execution.
- Phase 15.14 does not add Router runtime.
- Phase 15.14 does not add skill runtime.
- Phase 15.14 does not add Memory runtime.
- Phase 15.14 does not rename the CLI.

## Purpose

AgentFlow Studio now has three concerns in one repository:

- `narratocut/`: distribution-side media packaging, highlight selection,
  local slicing, final video assembly, reports, and review.
- `narratostudio/`: production-side structured handoff generation and
  production artifact contracts.
- AgentFlow platform contracts: project manifests, artifact maps, memory
  signals, intermediate assets, router decisions, skill invocation/result
  records, static contract audit, and replay validators.

The repository container is now `AgentFlowStudio`. The refactor should make the
platform contract layer explicit without breaking the current NarratoCut
CLI/Agent MVP, package imports, workflow files, or artifact contracts.

## Target Package Boundary

Recommended target:

```text
agentflow/
  contracts/      platform contract constants, example loaders, validation helpers
  harness/        platform-level artifact validators and audit helpers
  memory/         memory signal and asset contract helpers, not durable runtime
  router/         decision-only validation helpers, not Router runtime
  skills/         skill invocation/result replay helpers, not skill runtime

narratostudio/
  contracts/      production-side artifact schemas
  sop/            deterministic production handoff logic
  nodes/          workflow node adapters for production handoff workflow

narratocut/
  harness/        distribution artifact inspection and review
  workflow_engine/
  schemas/
  *_sop modules
```

`agentflow/` owns the platform contract layer. `narratostudio/` and
`narratocut/` keep module-owned domain logic. The platform package may validate
or index artifacts, but it must not become a hidden orchestrator.

## Ownership Rules

Platform-owned:

- `agentflow_project_manifest`
- `agentflow_artifact_map`
- `agentflow_contract_registry`
- `agentflow_contract_audit_report`
- `agentflow_feedback_event`
- `agentflow_memory_candidate`
- `agentflow_memory_promotion_decision`
- `agentflow_intermediate_asset`
- `agentflow_reusable_asset_profile`
- `agentflow_asset_reuse_decision`
- `agentflow_router_decision`
- `agentflow_skill_invocation`
- `agentflow_skill_result`
- `agentflow_router_dry_run_validation`
- `agentflow_skill_replay_validation`

NarratoStudio-owned:

- `creative_brief.json`
- `story_bible.json`
- `episode_outline.json`
- `scene_plan.json`
- `shot_plan.json`
- `prompt_pack.json`
- `production_handoff.json`
- `production_report.md`
- production handoff deterministic SOP logic
- `narratostudio_production_handoff` quality profile

NarratoCut-owned:

- highlight, clip, transcript, slicing, assembly, subtitle, cover, BGM, and
  package schemas
- distribution workflow execution nodes
- `inspect-run`, `review-run`, delivery-readiness, and finished package review
- current CLI entrypoints

## Migration Order

Step 1: introduce platform package skeleton.

- Add `agentflow/__init__.py` and small package namespaces only.
- Do not move behavior in the same PR.
- Add import smoke tests that prove the package is present.

Step 2: move pure contract utilities.

- Move only constant lists, artifact type helpers, and example loading helpers.
- Keep old imports as compatibility import wrappers.
- Do not move workflow nodes, SOP logic, or media-specific checks.

Step 3: split AgentFlow harness validators.

- Move Router dry-run and skill replay validators from
  `narratocut.harness.*` into `agentflow.harness.*`.
- Keep `narratocut.harness.agentflow_router` and
  `narratocut.harness.agentflow_skill` as compatibility import wrappers.
- No validator should execute workflows, select skills, invoke providers, or
  write durable state.

Step 4: expose compatibility imports.

- Keep compatibility import paths for at least one deprecation window.
- Emit no runtime warnings in tests unless there is a documented migration
  policy.
- Update docs to point new code at `agentflow.*`.

Step 5: update docs and examples.

- Update contract docs, roadmap, and examples after import compatibility is in
  place.
- Keep examples file-based and local-first.
- Do not change artifact names unless a separate contract migration document
  exists.

## Compatibility Strategy

Compatibility import paths are required for the first migration stage. Current
tests and user workflows may import AgentFlow validators through
`narratocut.harness.*`; those paths should keep working while new docs point to
`agentflow.harness.*`.

The deprecation window should last until:

- all tests import the new platform path directly
- docs no longer recommend the old platform-in-NarratoCut path
- Web UI branch has rebased and verified it does not depend on old locations
- at least one full verification run passes after the import move

Only after that window should wrappers be removed.

## Regression Matrix

| Surface | Required verification |
| --- | --- |
| Contract example tests | `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py` |
| Contract audit gate | `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_audit.py` |
| Router dry-run validator | `.venv\Scripts\python.exe -m pytest tests/test_agentflow_router_dry_run_validator.py` |
| Skill replay validator | `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_replay_validator.py` |
| NarratoStudio workflow smoke | run the local `narratostudio_brief_to_production_handoff` workflow, then inspect/review |
| NarratoCut delivery readiness | rerun the current video-only and video+script golden paths when distribution code moves |
| CLI help/version | `.venv\Scripts\python.exe -m apps.cli.main --help` and `.venv\Scripts\python.exe -m apps.cli.main version` |
| Full Python suite | `.venv\Scripts\python.exe -m pytest` |
| Import and bytecode check | `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests` |

For docs-only planning changes, the targeted document tests are enough before
full verification. For any import move, run the complete matrix.

## Non-Goals

Phase 15.14 does not:

- create `agentflow/` files
- move existing Python modules
- change workflow execution
- rename Python packages, workflows, artifacts, or the CLI
- rename the CLI or add `agentflow run-workflow`
- change artifact names or schema versions
- add Router runtime
- add skill runtime
- add Memory runtime
- add a database, vector store, cache service, hosted API, or Web UI
- call local or remote providers
- merge or modify the Web UI branch

## First Implementation Slice After This Plan

The first implementation slice after this plan is now:

```text
codex/agentflow-package-skeleton
```

Scope:

- add an empty `agentflow/` package with narrow documentation
- add import smoke tests
- do not move validators yet
- do not change CLI, workflows, or artifact contracts

Completion rule: this slice is complete when `agentflow` imports cleanly, the
reserved namespaces import cleanly, and existing
`narratocut.harness.agentflow_*` validator imports still work.

The second implementation branch can move pure constants or validators only if
the compatibility import strategy is already tested.
