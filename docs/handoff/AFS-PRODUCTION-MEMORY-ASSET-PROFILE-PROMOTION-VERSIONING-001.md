# AFS-PRODUCTION-MEMORY-ASSET-PROFILE-PROMOTION-VERSIONING-001

Status: implementation handoff for Node 3 of the non-Web Production Memory
asset loop.

## Scope

This slice reviews one
`agentflow_production_memory_asset_profile_update_candidate` and records an
explicit local project profile decision:

```text
asset profile update candidate
  -> asset profile promotion decision
  -> optional asset profile version
```

It does not add Web adaptation, provider execution, Company KB writes, durable
memory writes, human acceptance, or business validation.

## Added Artifacts

- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`

## Added CLI

```powershell
python -m apps.cli.main production-memory-loop-review-asset-profile-update-candidate --help
```

Inputs:

- `--asset-profiles`
- `--asset-profile-update-candidate`
- `--decision promoted|merged|rejected|expired|blocked`
- `--rationale`
- `--reviewer-role`
- `--decided-at`
- `--output`

Outputs:

- `asset_profile_promotion_decision.json`
- `asset_profile_promotion_decision.md`
- `asset_profile_version.json` and `.md` only when the decision applies a
  version.

## Contract Rules

- Source update candidate must be `candidate_only` before `promoted` or
  `merged` can apply a version.
- `rejected`, `expired`, or `blocked` decisions record review state but do not
  create a version.
- Supported patch operation is whitelisted `add_unique`.
- Unsupported patch operation or path fails before versioning.
- The source profile and update candidate are not mutated.
- Generated profile versions keep:
  - `writes_long_term_memory: false`
  - `writes_company_kb: false`
  - `profile_status: promoted`
  - `supersedes_profile_id`
  - source evidence refs
  - explicit local profile decision refs
- This is local project profile versioning only; it is not durable Memory OS
  storage and not Company KB promotion.

## Verification

Verification run for this branch:

```powershell
python -m pytest tests/test_production_memory_asset_profile_promotion_versioning.py -q
python -m pytest tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main production-memory-loop-review-asset-profile-update-candidate --help
python -m py_compile agentflow\memory\production_asset_profile_promotion.py agentflow\memory\production_asset_profile_promotion_contract.py agentflow\memory\production_asset_profile_promotion_render.py agentflow\memory\production_asset_profile_promotion_utils.py apps\cli\production_memory_asset_profile_promotion_command.py apps\cli\command_registry.py
python -m pytest
git diff --check
```

Results:

- Focused profile promotion/versioning tests: `11 passed`.
- Adjacent asset promotion/update/feedback/readiness suite: `38 passed`.
- Focused contract examples and CLI registry suite: `26 passed`.
- CLI help shows `--decision` as required.
- CLI no-provider smoke wrote ignored promotion decision and profile version
  artifacts.
- Changed Python files compiled.
- Full suite on Python 3.13.5: `955 passed`.
- `git diff --check`: exit 0 with LF-to-CRLF warnings only.
- Security audit: `PASS`; no blocking secret/private-path/media leak found in
  this slice.
- Spec review: prior blockers fixed; stale version outputs are removed when a
  later non-version decision writes to the same output directory.

## Next Node

Next deterministic node:

```text
Node 4 Asset Profile Context Projection
```

Web cockpit remains deferred until profile feedback, update candidate,
promotion/versioning, and context projection are deterministic.
