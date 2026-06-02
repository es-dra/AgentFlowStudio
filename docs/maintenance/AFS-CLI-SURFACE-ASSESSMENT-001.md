# AFS CLI Surface Assessment 001

Status: maintenance assessment for `AFS-MAINTENANCE-SLIMMING-001`.

## Finding

The default CLI help currently exposes many node-level
`production-memory-loop-*` commands. This is useful for engineering debugging
but too broad for the product command surface.

## Target Layers

```text
public product commands
support/operator commands
legacy hidden commands
```

## Public Product Commands

These commands should stay visible in default help because they describe stable
user-facing local workflows or product-level deterministic entrypoints:

- `slice-real`
- `ffmpeg-check`
- `inspect-run`
- `review-run`
- `package-report`
- `delivery-readiness`
- `memory-video-pipeline-*`
- `memory-evidence-reuse-review`
- `production-memory-loop-validate`
- `production-memory-loop-run-no-provider`
- `production-memory-loop-run-operator-no-provider`
- `production-memory-loop-asset-profile-readiness`
- `production-memory-loop-run-asset-test-package`
- `production-memory-loop-record-asset-feedback`
- `production-memory-loop-draft-asset-profile-update-candidate`
- `production-memory-loop-review-asset-profile-update-candidate`
- `production-memory-loop-asset-profile-context-projection`
- `production-memory-loop-review-asset-consistency`
- `web-bridge`

## Hidden Support Commands

Detailed operator-loop, acceptance-feedback, session report, next-pass, and
Company KB candidate commands should remain callable for runbooks and tests but
stay hidden from default help. They are node-level support tools, not the
primary product entrypoint.

Direct provider smoke and numbered demo commands remain hidden legacy/support
entries under `apps/cli/support_command_registry.py`.

## Boundary

Hiding a command does not remove it. It only reduces default help noise. Tests
should still be able to call hidden commands by exact name when regression
coverage requires them.
