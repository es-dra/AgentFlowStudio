# Handoff Index

Status: current handoff directory index for AgentFlow Studio.

This directory now keeps only handoff files that still support the current
local-internal-test product spine. Old node-by-node, demo, competition, and
Web bridge handoffs were deleted instead of migrated.

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

## Runtime Service / Frontend Handoff

- `AFS-WEB-LIBTV-SHELL-RESET-003.md`
- `AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001.md`
- `AFS-WEB-RC-DRAFT-PR-001.md`
- `AFS-WEB-PROVIDER-SMOKE-READINESS-001.md`
- `AFS-WEB-CANVAS-EXPERIENCE-002.md`
- `AFS-WEB-CANVAS-EXPERIENCE-002-BROWSER-QA.md`
- `AFS-WEB-REFOUNDATION-VERTICAL-001.md`
- `AFS-LIBTV-NODE-PROMPT-OPTIMIZER-INTEGRATION-001.md`
- `AFS-PROMPT-MEMORY-LOOP-MVP-001.md`
- `AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md`
- `AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006.md`
- `AFS-WEB-LIBTV-CANVAS-USABILITY-006P.md`
- `AFS-WEB-LIBTV-CANVAS-INTERACTION-SAFETY-006Q.md`
- `AFS-WEB-LIBTV-VIDEO-MOTION-CONTROLS-006R.md`
- `AFS-WEB-FOUNDATION-001.md`
- `AFS-WEB-WORKFLOW-CONTROLS-001.md`
- `AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`
- `AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md`

## Local Internal Test Handoff

- `AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`

## Current Maintenance Evidence

- `../maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`
- `../maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md`
- `../maintenance/AFS-ACTUAL-CLEANUP-002.zh-CN.md`

## Deleted Surfaces

Deleted from current handoff surface:

- old numbered memory/demo handoffs;
- old competition demo run/talk docs;
- old Company KB feedback handoffs;
- old generic Production Memory operator node handoffs;
- old Web bridge and Web operator handoffs.

## Routing Rule

- Product/tester handoff: start with the asset loop current evidence.
- Frontend integration: start with the landing prep plan, then Runtime Service / frontend contract handoffs.
- New Web work: start from the read-only asset cockpit handoff and current Web tests.
- Provider work: start from provider-gated docs and never infer authorization from deterministic test success.
