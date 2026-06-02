# Handoff Index

Status: handoff directory index for current AgentFlow Studio maintenance.

The `docs/handoff/` directory preserves node-by-node implementation evidence.
Do not treat every file here as current product direction. Use this index to
route new work.

## Current Mainline Evidence

- `AFS-PRODUCTION-MEMORY-ASSET-PROFILE-READINESS-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-FEEDBACK-INTAKE-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-PROFILE-UPDATE-CANDIDATE-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-PROFILE-PROMOTION-VERSIONING-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-CONTEXT-PROJECTION-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-CONSISTENCY-REVIEW-001.md`
- `AFS-PRODUCTION-MEMORY-ASSET-COCKPIT-WEB-001.md`

These files describe the deterministic local Production Memory Asset Loop:

```text
asset profile package
-> tester feedback event
-> update candidate
-> promotion decision
-> profile version
-> context projection
-> consistency review
-> read-only Web cockpit
```

## Current Maintenance Evidence

- `../maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md`
- `../maintenance/AFS-MAINTENANCE-SLIMMING-001.md`
- `../maintenance/AFS-CLI-SURFACE-ASSESSMENT-001.md`
- `../maintenance/AFS-IGNORED-RUNTIME-CLEANUP-MANIFEST-001.md`

## Preserved Evidence, Not Current Product Line

- `AFS-MEMORY-ADVANTAGE-DEMO-012.md`
- `AFS-MEMORY-ADVANTAGE-DEMO-013.md`
- `AFS-MEMORY-ADVANTAGE-DEMO-014.md`
- `AFS-MEMORY-ADVANTAGE-DEMO-015.md`
- `AFS-MEMORY-ADVANTAGE-RECORDING-016.md`

These files are historical provider/demo evidence. Do not add new numbered demo
modules unless the tracker is explicitly changed.

## Older Production Memory Node Evidence

Production Memory operator, next-pass, action-result, and acceptance-feedback
handoffs remain useful for debugging and regression history. They are no longer
the preferred entrypoint for product-level tester handoff; prefer the asset-loop
documents listed under current mainline evidence.

## Routing Rule

- Product/tester handoff: start with the asset loop current evidence.
- Engineering debugging: use the specific node handoff that matches the failing
  artifact or CLI command.
- New Web work: start from the read-only cockpit handoff and current Web tests.
- Provider work: start from provider-gated docs and never infer authorization
  from deterministic test success.
