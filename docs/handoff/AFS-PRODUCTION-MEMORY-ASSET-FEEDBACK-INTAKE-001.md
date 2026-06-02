# AFS-PRODUCTION-MEMORY-ASSET-FEEDBACK-INTAKE-001

Status: implementation handoff.

## Scope

This slice adds the first post-test-package intake node:

```text
tester feedback fixture
  + asset_profiles.json
  + asset_profile_readiness.json
  -> agentflow_production_memory_asset_feedback_event
```

It records tester feedback as structured, auditable evidence. It does not turn
feedback into memory, a memory candidate, a promotion decision, a profile
version, or Company KB material.

## Worktree

Use the superpowers worktree named:

```text
afs-production-memory-asset-feedback-intake-001
```

Do not test this slice from the legacy root checkout. That checkout can point
to an older Loulan evidence branch.

## Added Product Surface

CLI command:

```text
production-memory-loop-record-asset-feedback
```

Committed sanitized fixture:

```text
examples/agentflow/production_memory_asset_feedback.example.json
```

Runtime outputs:

```text
asset_feedback_event.json
asset_feedback_event.md
```

## Contract Boundaries

- `feedback_is_memory: false`
- `creates_memory_candidate: false`
- `creates_promotion_decision: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- `provider_calls_started: false`

The event may record feedback against a blocked or retired profile, but it does
not make that profile eligible for next context.

## Input Boundary

Supported input types:

```text
json_fixture
markdown_derived_fixture
```

This slice does not parse free-form Markdown. A Markdown feedback form must be
converted into a sanitized JSON fixture before this command records it.

The intake blocks private paths, local media references, media bytes, signed
URLs, provider result URLs, provider secrets, and committed Loulan-specific
materials.

## Verification Results

Commands run before handoff:

```powershell
python -m pytest tests/test_production_memory_asset_feedback_intake.py -q
python -m pytest tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
python -m apps.cli.main production-memory-loop-record-asset-feedback --help
python -m py_compile agentflow\memory\production_asset_feedback.py apps\cli\production_memory_asset_feedback_command.py apps\cli\command_registry.py
python -m apps.cli.main production-memory-loop-run-asset-test-package --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json --output data/processed/runs/production_memory_loop/asset_feedback_intake_smoke/package
python -m apps.cli.main production-memory-loop-record-asset-feedback --asset-profiles data/processed/runs/production_memory_loop/asset_feedback_intake_smoke/package/asset_profiles.json --asset-profile-readiness data/processed/runs/production_memory_loop/asset_feedback_intake_smoke/package/asset_profile_readiness.json --feedback-json examples/agentflow/production_memory_asset_feedback.example.json --output data/processed/runs/production_memory_loop/asset_feedback_intake_smoke/feedback
python -m pytest
git diff --check
```

Results:

- Focused asset feedback intake tests: `10 passed`.
- Focused asset feedback/profile readiness suite: `17 passed`.
- Focused contract examples and CLI registry suite: `26 passed`.
- CLI help exposes `production-memory-loop-record-asset-feedback`.
- CLI smoke wrote ignored asset feedback event outputs.
- Full suite on Python 3.13.5: `934 passed`.
- `git diff --check`: exit 0 with LF-to-CRLF warnings only.
- Security audit initially blocked on new absolute local paths in this handoff;
  those were removed before final verification. Remaining sensitive-keyword
  matches are rule text or deliberate redaction-test literals.

## Next Work

After this PR is reviewed or merged, the next deterministic node should be:

```text
Node 2 Asset Profile Update Candidate
```

Do not start Web cockpit adaptation until the feedback, update-candidate,
profile promotion/versioning, and context projection loop is deterministic.
