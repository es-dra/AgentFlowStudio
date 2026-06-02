# AFS CLI Help Cleanup 001

Date: 2026-06-03

Status: verified locally, integration pending

## Scope

This maintenance pass removes the terminal-display risk where Typer/Rich help
output could crop long option names, artifact kinds, or default output paths
with a Unicode ellipsis. On some Windows output paths this displayed as mojibake
in tester-facing CLI help.

## Changes

- Shortened public help text for long Production Memory artifact references.
- Hid long default runtime output paths in public help while keeping command
  defaults unchanged.
- Added short public options for tester-facing commands:
  - `asset-profile-update-review --candidate`
  - `asset-consistency-review --projection`
  - `asset-consistency-review --review-json`
- Kept legacy hidden command names and long internal options callable for
  runbook compatibility.
- Added a CLI boundary test that scans visible product command help for
  truncation/replacement glyphs.

## Boundary

- No provider calls.
- No Company KB writes.
- No test-baseline branch changes until this fix is merged and verified on
  `master`.

## Verification

Completed before merge:

```powershell
python -m pytest tests/test_cli_command_registry_boundaries.py tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_consistency_review.py -q
# 25 passed

python -m pytest
# 981 passed

git diff --check
# passed; only Windows LF-to-CRLF warnings were printed
```
