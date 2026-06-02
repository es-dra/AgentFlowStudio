# AFS Asset Profile Test Package

Status: tester handoff instructions for
`AFS-PRODUCTION-MEMORY-ASSET-PROFILE-READINESS-001`.

## Worktree Warning

Use this worktree for testing:

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-production-memory-loop-001
```

Do not use the older root checkout for this slice:

```text
D:\Projects\AgentFlowStudio
```

That checkout may point at a different branch and can confuse verification.

## Deterministic Package Command

Run the no-provider package from the committed sanitized example:

```powershell
python -m apps.cli.main production-memory-loop-run-asset-test-package `
  --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json `
  --output data/processed/runs/production_memory_loop/asset_test_package
```

Expected output files:

- `operator_loop/production_memory_operator_loop_run.json`
- `asset_profiles.json`
- `asset_profile_readiness.json`
- `asset_profile_readiness.md`
- `asset_test_package.json`
- `asset_test_package.md`
- `asset_consistency_rubric.md`
- `tester_feedback_template.md`
- `provider_validation_plan.json`
- `provider_validation_blockers.json`

The deterministic command must not call remote providers, write Company KB, or
write durable memory.

## Tester Materials

When final project materials are available, pass them as local ignored runtime
inputs:

```powershell
python -m apps.cli.main production-memory-loop-run-asset-test-package `
  --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json `
  --project-materials <local-final-script-or-folder> `
  --character-reference-image <local-character-reference-image> `
  --output data/processed/runs/production_memory_loop/asset_test_package
```

The package records whether local inputs were supplied, but it does not persist
their absolute paths, bytes, or file names in committed artifacts.

## Optional Provider Validation

Provider validation is not part of the core milestone. Run it only after the
deterministic package and tests pass.

Required local setup:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
$env:AFS_ALLOW_REMOTE_VIDEO="true"
$env:AFS_PROVIDER_CONFIG="<local ignored provider config>"
```

Then run:

```powershell
python -m apps.cli.main production-memory-loop-run-asset-test-package `
  --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json `
  --character-reference-image <local-character-reference-image> `
  --provider-config <local ignored provider config> `
  --run-provider-validation `
  --output data/processed/runs/production_memory_loop/asset_test_package
```

If the gate, config, adapter, or local input is unavailable, the command writes
`provider_validation_blockers.json`. That does not fail the core milestone.

## Review Instructions

Testers should review:

- What the character profile says is confirmed.
- What the scene profile says is confirmed.
- Which refs entered next context.
- Which refs were blocked and why.
- Which allowed variations are acceptable.
- Which negative constraints were violated.
- Whether the result is kept, partially kept, not kept, or cannot be judged.

Use:

```text
asset_consistency_rubric.md
tester_feedback_template.md
```

Do not treat machine readiness as human acceptance, provider success, business
validation, or durable Memory OS completion.
