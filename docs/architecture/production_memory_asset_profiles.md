# Production Memory Asset Profiles

Status: implementation slice for
`AFS-PRODUCTION-MEMORY-ASSET-PROFILE-READINESS-001`.

## Positioning

This slice turns the existing Production Memory operator loop into a tester
package for character and scene continuity review.

It does not claim that visual consistency is solved. It organizes explicit
project materials, operator-loop evidence, memory candidates, and promotion
decisions into reviewable asset profiles that can be loaded into a next local
test pass.

Product layer:

```text
memory-driven AI content production workbench
```

Technical layer:

```text
Production Memory Architecture
```

Long-term vision:

```text
Memory OS
```

## Artifact Types

- `agentflow_production_memory_asset_profile_seed`: sanitized local seed for
  tester-supplied project materials, character references, and profile intent.
- `agentflow_production_memory_asset_profile`: unified profile artifact with
  `profile_kind: character | scene`.
- `agentflow_production_memory_asset_profile_readiness`: machine readiness for
  tester review.
- `agentflow_production_memory_asset_test_package`: tester-facing package that
  links profiles, readiness, rubric, feedback template, and optional provider
  validation records.

## Profile Contract

Profiles are scoped project assets, not Company memory. Required profile
surfaces include:

- `profile_scope`
- `profile_version`
- `supersedes_profile_id`
- `allowed_variations`
- `negative_constraints`
- `evidence_refs`
- `promotion_decision_refs`
- `context_eligibility`
- `blockers`
- `writes_long_term_memory: false`
- `writes_company_kb: false`

The unified profile model avoids a parallel character-only or scene-only
runtime. Character and scene behavior differ by `profile_kind`, not by separate
systems.

## Readiness Rules

- Feedback is not memory.
- A memory candidate is not promoted memory.
- A profile may use a memory candidate as evidence only when the candidate has
  an explicit promotion decision ref.
- Rejected, pending, blocked, expired, or missing refs block readiness.
- `promoted` in this package means usable for the next project context only.
  It does not write durable memory or Company KB.
- Local project materials and character-reference paths are runtime inputs and
  are not persisted in package artifacts.

## Provider Boundary

The deterministic package is the core milestone. Optional provider validation
is a separate smoke lane:

```text
deterministic package passes -> provider gates checked -> provider smoke may run
```

Image smoke requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`. Video smoke requires
`NARRATOCUT_ALLOW_REMOTE_VIDEO=true`. Provider config must come from a local
ignored config path or `NARRATOCUT_PROVIDER_CONFIG`.

MiniMax I2I and Kling I2V reuse existing gated smoke adapters. GPT Image2 is
recorded as a blocker until a verified adapter exists in this repository.
