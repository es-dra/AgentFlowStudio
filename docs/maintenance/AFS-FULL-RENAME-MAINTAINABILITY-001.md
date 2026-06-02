# AFS Full Rename Maintainability 001

Date: 2026-06-03

Status: verified locally, PR pending

## Scope

This maintenance pass performs the full public rename requested for AgentFlow
Studio:

- Package metadata is renamed from the legacy distribution to
  `agentflow-studio`.
- The public console command is `afs`.
- The legacy console script is removed.
- The Python package is `agentflow_studio`.
- The production handoff package is nested under
  `agentflow_studio.production`.
- Public environment gates use the `AFS_*` prefix.
- Product-facing docs and test names use AgentFlow Studio / AgentFlow
  Production language.

## CLI Surface

The public Production Memory commands now use short AFS names:

```text
memory-loop-validate
memory-loop-run-no-provider
asset-profile-readiness
asset-test-package-run
asset-feedback-record
asset-profile-update-draft
asset-profile-update-review
asset-context-project
asset-consistency-review
```

The old `production-memory-loop-*` command names remain callable as hidden
aliases for internal runbooks and regression tests. They do not appear in the
default `afs --help` product surface.

## Boundaries

- No provider calls were made.
- No Company KB files were written.
- No runtime media, model cache, local private path, signed URL, provider
  secret, or generated artifact was intentionally added.
- This pass changes naming and entrypoints. It does not claim human acceptance,
  business validation, provider success, durable memory promotion, or Memory OS
  completion.

## Verification

Completed:

```powershell
python -m pytest tests/test_cli_command_registry_boundaries.py tests/test_agentflow_package_skeleton.py -q
python -m pytest tests/test_contract_examples.py -q
python -m pytest tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_context_projection.py tests/test_production_memory_asset_consistency_review.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_web_static_artifact_registry.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_production_bridge.py -q
python -m pytest tests/test_agentflow_production_workflow.py tests/test_alpha_smoke_cli.py -q
python -m compileall apps agentflow agentflow_studio tests
python -m pytest
git diff --check
```

Editable install note:

- `pip install -e .[dev]` with the system Python 3.13 failed because the
  project intentionally declares `requires-python = ">=3.11,<3.13"`.
- Editable install and `afs` command smoke were verified with the bundled
  Python 3.12 runtime.

Final regression result:

```powershell
python -m pytest
# 980 passed

git diff --check
# passed
```
