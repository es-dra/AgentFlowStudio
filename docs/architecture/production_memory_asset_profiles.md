# Production Memory Asset Profiles

Status: implementation slice for
`AFS-PRODUCTION-MEMORY-ASSET-PROFILE-READINESS-001` through local profile
promotion/versioning.

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

## Asset Feedback Intake

`agentflow_production_memory_asset_feedback_event` records tester feedback
against one character or scene profile. It is an evidence-only intake artifact:

- It is not memory.
- It is not a memory candidate.
- It is not a promotion decision.
- It does not unlock next-context use for a blocked or retired profile.
- It records `json_fixture` or `markdown_derived_fixture` as the source input
  type, but it does not parse free-form Markdown in this slice.
- It rejects private paths, media bytes, signed URLs, provider secrets, and
  provider result URLs.

The first supported taxonomy is shared with the later cross-scene consistency
review node:

```text
review_dimension:
  character_identity
  wardrobe_or_body_anchor
  scene_spatial_anchor
  lighting_or_time_anchor
  negative_constraint_violations
  allowed_variation_fit
  overall_result

failure_attribution:
  prompt_issue
  context_issue
  profile_issue
  reference_asset_issue
  model_capability_issue
  style_drift
  character_inconsistency
  scene_inconsistency
  unknown
```

## Asset Profile Update Candidate

`agentflow_production_memory_asset_profile_update_candidate` turns one asset
feedback event into a structured candidate patch. It is the next deterministic
node after feedback intake:

```text
asset feedback event
  -> structured proposed_profile_patch.patch_ops
  -> explicit profile promotion/versioning decision in a later node
```

Rules:

- It is not a profile version.
- It is not a profile promotion decision.
- It does not apply the patch.
- It does not unlock next-context eligibility.
- It does not write durable memory or Company KB.
- `cannot_judge` creates a blocked no-patch candidate.
- `kept + no_change` records `no_update_recommended` with no patch.
- Negative feedback without structured patch operations records
  `blocked_missing_patch_ops`.
- Drift and violated-constraint feedback becomes structured `patch_ops`, not
  free-form profile mutation.

The first supported patch operation is:

```text
op: add_unique
path: /negative_constraints/- | /evidence_refs/-
value: sanitized scalar
rationale: bounded explanation
evidence_refs: [source feedback event id]
```

## Asset Profile Promotion And Versioning

`agentflow_production_memory_asset_profile_promotion_decision` records an
explicit operator decision for one
`agentflow_production_memory_asset_profile_update_candidate`.

`agentflow_production_memory_asset_profile_version` is written only when the
decision is `promoted` or `merged` and the source candidate is `candidate_only`.

Rules:

- The decision is local project profile versioning, not durable memory.
- It does not write Company KB.
- It does not claim human acceptance, business validation, provider success, or
  next-pass execution.
- `rejected`, `expired`, and `blocked` decisions record the review result but
  do not create a new profile version.
- `blocked_cannot_judge`, `blocked_missing_patch_ops`, and
  `no_update_recommended` candidates cannot be promoted into a version.
- Only whitelisted structured patch operations are applied.
- `add_unique` patch operations are idempotent and dedupe existing profile
  values before applying the new version.

The first supported review CLI is:

```text
production-memory-loop-review-asset-profile-update-candidate
```

This command reads `asset_profiles.json` plus one update-candidate JSON and
writes:

```text
asset_profile_promotion_decision.json
asset_profile_promotion_decision.md
asset_profile_version.json
asset_profile_version.md
```

The version files are omitted when the explicit decision blocks versioning.

Each written profile version includes `version_change_summary` with the source
profile, target profile, source candidate, source decision, patch operation
count, and applied patch paths. This is trace metadata for downstream context
projection; it is not a durable memory write.

Downstream context projection must treat the profile version as the inclusion
authority. The promotion decision may explain why a version was allowed, but
Node 4 must still check `profile_version_applied`, `usable_for_next_context`,
the embedded profile `context_eligibility`, blockers, superseded profile IDs,
and missing refs before including anything in the next context.

## Asset Profile Context Projection

`agentflow_production_memory_asset_profile_context_projection` is the
deterministic Node 4 artifact that turns explicitly versioned profiles into the
next context payload:

```text
asset profile version
  -> included_refs / blocked_refs
  -> context_payload.asset_profile_refs
```

Rules:

- Only `agentflow_production_memory_asset_profile_version` artifacts may enter
  this projection.
- A promotion decision by itself is explanation evidence, not context
  inclusion authority.
- The projected version must have `profile_version_applied: true`,
  `usable_for_next_context: true`, an embedded promoted profile, included
  `context_eligibility`, no profile blockers, and explicit decision refs.
- Superseded source profiles and stale profile versions are blocked rather
  than silently discarded.
- Every projection lists both `included_refs` and `blocked_refs`.
- The projection is no-provider only and writes neither durable memory nor
  Company KB.

The first supported CLI is:

```text
production-memory-loop-asset-profile-context-projection
```

## Asset Consistency Review

`agentflow_production_memory_asset_consistency_review` is the deterministic
Node 5 artifact that records explicit tester/operator observations against
projected asset profile context:

```text
asset profile context projection
  + sanitized consistency review fixture
  -> asset consistency review
```

Rules:

- Consistency review uses only explicitly projected profile refs from
  `included_refs`.
- Unknown or blocked profile refs become `blocked_findings`.
- `cannot_judge` is neutral and does not create feedback, candidates, or
  promotion decisions.
- The review records `kept`, `partially_kept`, `not_kept`, and
  `cannot_judge` results using the same first taxonomy as asset feedback
  intake.
- The review is evidence only. It does not apply profile updates, unlock
  context, write durable memory, or write Company KB.
- Review input is a sanitized JSON or markdown-derived JSON fixture. Free-form
  Markdown parsing remains out of scope for this node.

The first supported CLI is:

```text
production-memory-loop-review-asset-consistency
```

## Web Read-Only Asset Cockpit

Node 6 adds Web Workbench rendering for the deterministic asset loop. It is a
read-only selected-file view over existing JSON artifacts:

```text
selected local asset JSON
  -> artifact workspace normalization
  -> read-only asset cockpit view
```

Supported asset artifacts include:

- `agentflow_production_memory_asset_profile_seed`
- `agentflow_production_memory_asset_profile`
- `agentflow_production_memory_asset_profile_readiness`
- `agentflow_production_memory_asset_test_package`
- `agentflow_production_memory_asset_feedback_event`
- `agentflow_production_memory_asset_profile_update_candidate`
- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`
- `agentflow_production_memory_asset_profile_context_projection`
- `agentflow_production_memory_asset_consistency_review`
- optional provider validation plan/blocker/result artifacts

The cockpit prioritizes the latest selected deterministic node for display:

```text
consistency review
  -> context projection
  -> profile version
  -> promotion decision
  -> update candidate
  -> feedback event
  -> readiness / test package / seed
```

Rules:

- The view only uses explicit selected local files.
- It does not follow refs or scan folders.
- It does not persist browser state.
- It does not execute providers or workflows.
- It does not create feedback, profile updates, promotion decisions, profile
  versions, context projections, or consistency reviews.
- It does not write durable memory or Company KB.
- It is generic AFS behavior and does not add project-specific inspectors.

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
