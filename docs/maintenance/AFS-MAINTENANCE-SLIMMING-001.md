# AFS Maintenance Slimming 001

Status: in progress on `codex/afs-maintenance-slimming-001`.

## Goal

Make the current AgentFlow Studio mainline easier to maintain after the
Production Memory Asset Loop merge, without changing the validated deterministic
loop behavior.

## Scope

This maintenance pass covers five consolidation nodes:

```text
1. Documentation/status slimming
2. CLI product surface layering
3. Web artifact registry consolidation
4. Production Memory asset facade
5. Ignored runtime cleanup manifest and safe local cleanup
```

## Non-Goals

- No remote provider calls.
- No Company KB writes.
- No Loulan-specific adapter or inspector.
- No deletion of preserved evidence handoffs.
- No directory restructuring of `agentflow/memory`.
- No hosted Web product or workflow execution UI.
- No claim of human acceptance, business validation, durable Memory OS, or
  provider success.

## Implementation Notes

- `DEVLOG.md` and `TASK_TRACKER.md` are short active ledgers again.
- Long pre-slimming history is preserved in `docs/archive/`.
- `docs/handoff/INDEX.md` routes current work away from old node sprawl.
- CLI support/internal commands remain callable, but default help should show a
  thinner product surface.
- Web artifact metadata should move toward one registry-driven source of truth.
- Production Memory asset callers should get a facade module before any future
  filesystem-level refactor.

## Verification Plan

```powershell
python -m pytest tests/test_cli_command_registry_boundaries.py -q
python -m pytest tests/test_web_static_artifact_registry.py -q
python -m pytest tests/test_production_memory_asset_loop_facade.py -q
python -m pytest tests/test_web_static_artifact_boundaries.py tests/test_web_static_production_memory_asset_cockpit.py -q
python -m apps.cli.main --help
python -m pytest
git diff --check
```

## Boundary Evidence

This pass is maintenance only. Passing machine tests are structure/runtime
verification, not human acceptance or business validation.
