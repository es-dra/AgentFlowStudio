# AFS-PRODUCTION-MEMORY-ASSET-PROFILE-READINESS-001

Status: implementation handoff.

## Scope

This slice adds a non-Web tester package for the Production Memory asset
profile loop:

```text
final project materials
  -> production-memory operator loop
  -> character/scene asset profiles
  -> readiness package
  -> tester rubric and feedback template
  -> optional gated image/video provider validation
```

Loulan remains a real production pressure sample, not the product center. The
committed seed is sanitized and generic. Real script, storyboard, character
image, generated media, provider config, and provider secrets must stay local
and ignored.

## Worktree

Use:

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-production-memory-loop-001
```

Do not test this slice from:

```text
D:\Projects\AgentFlowStudio
```

That root is a different checkout and can point to an older branch.

## Added Product Surface

CLI commands:

```text
production-memory-loop-asset-profile-readiness
production-memory-loop-run-asset-test-package
```

Committed example:

```text
examples/agentflow/production_memory_asset_profile_seed.example.json
```

Core output files:

```text
asset_profiles.json
asset_profile_readiness.json
asset_profile_readiness.md
asset_test_package.json
asset_test_package.md
asset_consistency_rubric.md
tester_feedback_template.md
provider_validation_plan.json
provider_validation_blockers.json
```

## Claim Boundaries

- Not human acceptance.
- Not business validation.
- Not durable memory.
- Not Company KB promotion.
- Not Memory OS completion.
- Not provider success unless `provider_validation_result.json` says
  `status: succeeded`.

## Provider Policy

The deterministic package is the core milestone. Provider validation is
optional and gated:

- image: `AFS_ALLOW_REMOTE_IMAGE=true`
- video: `AFS_ALLOW_REMOTE_VIDEO=true`
- config: `--provider-config` or `AFS_PROVIDER_CONFIG`

MiniMax I2I and Kling I2V reuse existing smoke adapters. GPT Image2 is recorded
as a blocker until a verified adapter exists.

## Verification Results

Commands run:

```powershell
python -m pytest tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_production_memory_asset_profile_readiness.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
python -m apps.cli.main production-memory-loop-run-asset-test-package --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json --output data/processed/runs/production_memory_loop/asset_test_package
python -m pytest
git diff --check
```

Results:

- Focused asset profile tests: `7 passed`.
- Focused asset/contract/CLI registry suite: `33 passed`.
- CLI help exposed both new commands.
- CLI no-provider smoke wrote a ready asset test package.
- Full suite on Python 3.13.5: `924 passed`.
- `git diff --check`: exit 0 with CRLF warnings only.
- Python 3.12.13 from the Codex runtime exists but lacks `pytest`; it was not
  used for the final verification run.

Optional provider validation was attempted after deterministic checks and wrote
blockers for:

- `image_gate_unset`
- `video_gate_unset`
- `provider_config_missing`
- `character_reference_image_missing`

No provider success is claimed.

## Next Work

The next product slice should be Web adaptation for the asset package
readiness/cockpit. It should remain read-only first and should not add
directory scanning, browser persistence, provider execution from Web, or a
Loulan-specific inspector.
