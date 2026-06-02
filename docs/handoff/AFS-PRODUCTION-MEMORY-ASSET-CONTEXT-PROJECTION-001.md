# AFS-PRODUCTION-MEMORY-ASSET-CONTEXT-PROJECTION-001

Status: implementation handoff for Node 4 of the non-Web Production Memory
asset loop.

## Scope

This slice projects explicit local asset profile versions into the next
no-provider context payload:

```text
asset profile version
  -> asset profile context projection
  -> included_refs / blocked_refs
  -> context_payload.asset_profile_refs
```

It does not add Web adaptation, provider execution, Company KB writes, durable
memory writes, human acceptance, or business validation.

## Added Artifact

- `agentflow_production_memory_asset_profile_context_projection`

## Added CLI

```powershell
python -m apps.cli.main production-memory-loop-asset-profile-context-projection --help
```

Inputs:

- `--asset-profile-version` one or more
  `agentflow_production_memory_asset_profile_version` JSON files.
- `--generated-at`
- `--output`

Outputs:

- `asset_profile_context_projection.json`
- `asset_profile_context_projection.md`

## Contract Rules

- Only `agentflow_production_memory_asset_profile_version` artifacts can be
  included in the next context projection.
- Promotion decisions are not inclusion authority by themselves.
- A version is included only when:
  - `profile_version_applied: true`
  - `usable_for_next_context: true`
  - `version_change_summary` is present
  - embedded profile exists and has `profile_status: promoted`
  - embedded profile has `context_eligibility: included`
  - embedded profile has no blockers
  - embedded profile keeps `writes_long_term_memory: false`
  - embedded profile keeps `writes_company_kb: false`
  - source decision id is present in the embedded profile decision refs
- Superseded source profile refs and stale superseded profile versions are
  represented in `blocked_refs`.
- The projection lists both `included_refs` and `blocked_refs`.
- The projection is no-provider only and does not write durable memory or
  Company KB.

## Verification

Verification to run for this branch:

```powershell
python -m pytest tests/test_production_memory_asset_profile_context_projection.py -q
python -m pytest tests/test_production_memory_asset_profile_context_projection.py tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
python -m apps.cli.main production-memory-loop-asset-profile-context-projection --help
python -m py_compile agentflow\memory\production_asset_profile_context_projection.py apps\cli\production_memory_asset_profile_context_projection_command.py apps\cli\command_registry.py
python -m pytest
git diff --check
```

## Next Node

Next deterministic node:

```text
Node 5 Cross-Scene Consistency Review
```

Node 5 should consume next-pass results plus asset profile context projection
artifacts to judge whether character and scene anchors were kept, partially
kept, not kept, or cannot be judged. Web cockpit remains deferred until the
feedback/version/projection loop is deterministic.
