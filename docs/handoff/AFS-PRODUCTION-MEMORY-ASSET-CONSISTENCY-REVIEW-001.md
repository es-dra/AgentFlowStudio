# AFS-PRODUCTION-MEMORY-ASSET-CONSISTENCY-REVIEW-001

Status: implementation handoff for Node 5 of the non-Web Production Memory
asset loop.

## Scope

This slice records explicit cross-scene or cross-shot consistency observations
against projected profile context:

```text
asset profile context projection
  + sanitized consistency review fixture
  -> asset consistency review
```

It does not add Web adaptation, provider execution, free-form Markdown parsing,
Company KB writes, durable memory writes, automatic feedback events, automatic
profile updates, promotion decisions, human acceptance, or business
validation.

## Added Artifacts

- `agentflow_production_memory_asset_consistency_review_fixture`
- `agentflow_production_memory_asset_consistency_review`

## Added CLI

```powershell
python -m apps.cli.main production-memory-loop-review-asset-consistency --help
```

Inputs:

- `--asset-profile-context-projection`
- `--consistency-review-json`
- `--reviewed-at`
- `--output`

Outputs:

- `asset_consistency_review.json`
- `asset_consistency_review.md`

## Contract Rules

- Only profile refs from `asset_profile_context_projection.included_refs` can
  produce consistency findings.
- Unknown or blocked profile refs become `blocked_findings`.
- `cannot_judge` is neutral.
- Review dimensions, results, failure attributions, and suggested next states
  reuse the first asset-feedback taxonomy.
- The review fixture may be `json_fixture` or `markdown_derived_fixture`, but
  this node does not parse free-form Markdown.
- This review is evidence only:
  - `creates_asset_feedback_event: false`
  - `creates_profile_update_candidate: false`
  - `creates_promotion_decision: false`
  - `writes_long_term_memory: false`
  - `writes_company_kb: false`

## Verification

Verification to run for this branch:

```powershell
python -m pytest tests/test_production_memory_asset_consistency_review.py -q
python -m pytest tests/test_production_memory_asset_consistency_review.py tests/test_production_memory_asset_profile_context_projection.py tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
python -m apps.cli.main production-memory-loop-review-asset-consistency --help
python -m py_compile agentflow\memory\production_asset_consistency_review.py agentflow\memory\production_asset_consistency_review_render.py apps\cli\production_memory_asset_consistency_review_command.py apps\cli\command_registry.py
python -m pytest
git diff --check
```

## Next Node

Next deterministic node:

```text
Node 6 Web Read-Only Asset Cockpit
```

The Web cockpit should remain read-only. It can render profile readiness,
feedback intake, update candidates, promotion/versioning, context projection,
and consistency review artifacts, but it must not scan directories, persist
browser state, execute providers, or create Loulan-specific inspectors.
