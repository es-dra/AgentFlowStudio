# AFS-PRODUCTION-MEMORY-ASSET-COCKPIT-WEB-001

Status: implementation handoff for Node 6 of the Production Memory asset loop.

## Scope

This slice adds a generic read-only Web Workbench cockpit for selected asset
loop artifacts:

```text
asset readiness / feedback / candidate / promotion / version / projection / review JSON
  -> selected-file Web workspace
  -> read-only asset cockpit
```

It does not add provider execution, workflow execution from Web, folder scans,
browser persistence, Company KB writes, durable memory writes, human
acceptance, business validation, or project-specific inspectors.

## Added Web Surface

The Web Workbench now recognizes and displays these asset artifacts:

- `agentflow_production_memory_asset_profile_seed`
- `agentflow_production_memory_asset_profile`
- `agentflow_production_memory_asset_profile_readiness`
- `agentflow_production_memory_asset_test_package`
- `agentflow_production_memory_asset_provider_validation_plan`
- `agentflow_production_memory_asset_provider_validation_blockers`
- `agentflow_production_memory_asset_provider_validation_result`
- `agentflow_production_memory_asset_feedback_event`
- `agentflow_production_memory_asset_profile_update_candidate`
- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`
- `agentflow_production_memory_asset_profile_context_projection`
- `agentflow_production_memory_asset_consistency_review`

## Implementation Notes

- `apps/web/artifact-contracts.js` registers asset artifact aliases and source
  roles.
- `apps/web/artifact-workspace.js` exposes normalized asset artifact slots.
- `apps/web/memory-workbench-inspector.js` and
  `apps/web/memory-workbench-production-inspector-facts.js` show structured
  facts for the asset loop.
- `apps/web/memory-workbench-production-assets.js` builds the generic asset
  cockpit view.
- `apps/web/memory-workbench-production-assets-shared.js` keeps shared view
  helpers separate so the main builder stays focused.
- `apps/web/memory-workbench-controller.js` inserts the asset cockpit after the
  existing production-memory view chain, so selected asset artifacts can
  override the default fixture view.

## Contract Rules

- Selected local JSON is the only input.
- The cockpit does not auto-open referenced paths.
- The cockpit does not create or mutate artifacts.
- Asset feedback remains evidence only.
- Update candidates remain candidate only.
- Promotion decisions and profile versions keep their existing Node 3
  semantics.
- Context projection remains the Node 4 inclusion authority.
- Consistency review remains the Node 5 evidence artifact and does not create
  feedback or promotion decisions.
- All displayed boundaries retain `writes_long_term_memory: false`,
  `writes_company_kb: false`, and no-provider controls when present.

## Verification

Verification to run for this branch:

```powershell
python -m pytest tests/test_web_static_production_memory_asset_cockpit.py -q
python -m pytest tests/test_web_static_production_memory_asset_cockpit.py tests/test_production_memory_asset_profile_context_projection.py tests/test_production_memory_asset_consistency_review.py tests/test_web_static_artifact_boundaries.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
node --check apps\web\memory-workbench-production-assets.js
node --check apps\web\memory-workbench-production-assets-shared.js
python -m pytest
git diff --check
```

Browser-level smoke was attempted with local Edge headless. The `file://` path
and a short-lived local HTTP server did not produce a usable rendered memory
DOM capture, so browser smoke is a residual risk rather than passing evidence.

## Next Node

The deterministic asset loop now has:

```text
readiness -> feedback -> update candidate -> promotion/version
  -> context projection -> consistency review -> Web read-only cockpit
```

Next work should be driven by tester feedback. Likely follow-ups are:

- harden tester feedback fixtures from real test runs;
- add a lighter product-facing test package summary if testers report the CLI
  bundle is too technical;
- start Web interaction design only after the static cockpit proves readable.
