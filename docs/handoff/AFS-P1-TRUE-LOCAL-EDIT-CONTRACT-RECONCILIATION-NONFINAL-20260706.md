# AFS P1 True Local Edit Contract Reconciliation Non-Final

Date: 2026-07-06

top_down_dispatch_id:
`TD-AFS-V02-RECORD-P1-TRUE-LOCAL-EDIT-CONTRACT-RECONCILIATION-NONFINAL-NO-PROVIDER-20260706-001`

bottom_up_feedback_id:
`BU-AFS-V02-RECORD-P1-TRUE-LOCAL-EDIT-CONTRACT-RECONCILIATION-NONFINAL-NO-PROVIDER-20260706-001`

verdict: `PASS`

## Scope

This packet reconciles a held, untracked July 5 true-local-edit
schema/OpenAPI no-provider spec against the current tracked PR #94 local-edit
preflight package and current records.

Held source evidence:

- sanitized display path:
  `docs/handoff/AFS-P1-TRUE-LOCAL-EDIT-SCHEMA-OPENAPI-CONTRACT-NO-PROVIDER-20260705.md`
- source size verified before use: 21216 bytes
- source SHA256 verified before use:
  `4BC203F31D78FB7725B333AEC45F17D3B6DB2CFE06498BB6576C8DA8F86C87AF`

The original held source remains held evidence. This packet does not restore,
land, or copy it unchanged.

## Current Tracked Contract

Current tracked PR #94 package is preflight-only:

- Studio and Runtime can record a local-edit request/draft and call
  `POST /projects/{project_id}/keyframe-local-edits/preflight`.
- Complete drafts return `ready_no_provider_execution` while execution remains
  blocked as `blocked_no_local_transform`.
- Incomplete drafts return `draft_needs_input` while execution remains blocked
  as `blocked_missing_required_input`.
- Runtime rejects unsafe payload markers and forbidden fallback settings before
  any execution.
- Persisted Studio state prunes raw preflight receipts before save.
- No submit route, poll route, preview route, local pixel/image transform,
  generated media, provider call, provider gate mutation, or full-frame fallback
  implementation is claimed.

Current tracked provider descriptor metadata also includes future
`provider_descriptor.v0.3` image-edit capability vocabulary. That metadata is
not Runtime local-edit submit support, provider QA, generated-media QA, true
local-edit capability, or fallback execution.

## Classification

| Source section or theme | Disposition | Reconciliation note |
|---|---|---|
| Source packet as active/current evidence | `superseded_by_current_contract` | This packet is now the tracked current-checkout disposition record. The held July 5 source is not active/current-checkout-verifiable evidence by itself. |
| Contract-only/no-provider/non-claim boundary | `absorbed_by_pr94` | PR #94 records no provider call, no generated media, no local transform, no full-frame fallback, and no acceptance/finality claims. |
| `POST /keyframe-local-edits/preflight` route vocabulary | `absorbed_by_pr94` | Runtime exposes the preflight endpoint and Studio client/draft flow can call it. |
| `POST /keyframe-local-edits`, poll route, and candidate preview route | `requires_implementation_lane` | Submit, poll, and preview are not implemented or claimed. |
| Minimal request schema and draft fields | `absorbed_by_pr94` | Tracked request uses schema `afs_keyframe_local_edit_request.v0.1`, parent lineage, edit intent, edit scope, preserve/negative locks, fallback policy, and no-provider capability mode. |
| Broader OpenAPI component set for response, target, locks, fallback policy, provider capability, and audit state | `future_backlog_input` | Useful names remain planning vocabulary; only the current request/preflight subset is tracked. |
| Parent lineage and child-version audit vocabulary | `absorbed_by_pr94` | Current request/preflight carries immutable parent lineage, parent keyframe job, parent image asset, parent candidate, and safe source presence. |
| Full target object with `target_type`, `target_id`, labels, graph confidence, and provider-inferred confidence | `future_backlog_input` | PR #94 uses target node id plus target description only; richer target objects require a later contract/UI lane. |
| Scope kinds `mask_asset`, `bbox`, `polygon`, and `semantic_region` | `absorbed_by_pr94` | Current preflight validates these draft scope kinds and blocks missing required scope inputs. |
| `full_frame`, `unknown`, and temporal scope planning vocabulary | `future_backlog_input` | These are not current submit or provider capability claims. |
| Preserve/change lock taxonomy | `future_backlog_input` | Current package has simple preserve and negative lock arrays; structured lock conflict semantics require a later lane. |
| Full-frame fallback and fallback truth labels | `absorbed_by_pr94` | Current contract forces fallback off and reports `fallback_full_frame_edit=false`; forbidden fallback settings are rejected. |
| Expanded fallback labels such as provider full-frame edit or full regeneration fallback | `future_backlog_input` | Labels are useful for future honesty/evaluator work but are not current execution support. |
| Provider descriptor image-edit capability vocabulary | `superseded_by_current_contract` | Current descriptor contract has v0.3 metadata fields and validators, while still defaulting absent fields to blocked/no-support. |
| Provider descriptor support as Runtime execution capability | `requires_implementation_lane` | Metadata alone does not implement submit, provider translation, masks, media generation, or provider QA. |
| Preflight response statuses and no-provider flags | `absorbed_by_pr94` | Current preflight returns `ready_no_provider_execution` / `draft_needs_input`, `blocked_no_local_transform` / `blocked_missing_required_input`, and false provider/media/transform/fallback flags. |
| Submit response, safe manifest additions, local-edit bridge, candidate previews, and reusable image assets | `requires_implementation_lane` | Not implemented by PR #94. |
| Audit/review state for local-edit candidates | `future_backlog_input` | Useful evaluator/human-review vocabulary; no current candidate acceptance surface exists. |
| Validation and safe error semantics for missing input, unsafe media/provider markers, and forbidden fallback | `absorbed_by_pr94` | Runtime tests cover blocked/draft states, unsafe marker rejection, and safe error detail. |
| Future HTTP errors for parent lookup, stale preflight, lineage conflict, unsupported capability, and provider-gate-open submit | `requires_implementation_lane` | These require submit/manifest/provider lanes and are not claimed by current preflight. |
| Backward compatibility with keyframe generation and video revision routes | `absorbed_by_pr94` | PR #94 adds separate local-edit preflight without reinterpreting existing generation/revision routes. |
| Future implementation gates and verification route | `future_backlog_input` | Keep as lane planning vocabulary; current tests validate only the preflight/draft slice. |
| Residual risks around provider marketing language, mask storage, chained lineage, temporal confusion, and preserve-lock limits | `future_backlog_input` | Risks remain relevant for later evaluator/implementation lanes. |

## Captured Non-Final Vocabulary

Useful vocabulary retained without implementation claims:

- submit, poll, and preview route family for future lanes;
- provider descriptor image-edit capability fields, including supported scope
  kinds, fallback modes, input fidelity, and `local_edit_truth_label`;
- lineage terms for parent keyframe job, parent image asset, parent candidate,
  parent/root edit chain, and child/fallback lineage;
- target/scope vocabulary for user-selected or graph-inferred targets,
  `mask_asset`, `bbox`, `polygon`, and `semantic_region`;
- preserve/change locks, negative locks, preserve risk, and conflict handling;
- lock/fallback labeling that distinguishes true local edit from provider
  masked edit, provider region edit, provider full-frame edit, full regeneration
  fallback, and blocked no-support states;
- OpenAPI/no-provider/fallback wording that keeps request shape separate from
  execution and capability truth;
- evaluator gates for OpenAPI, blocked default behavior, fallback wording,
  parent lineage audit, non-claim boundaries, provider smoke, generated-media
  QA, and human/Owner acceptance.

## Records Disposition

`DEVLOG.md`, `TASK_TRACKER.md`, and `docs/handoff/INDEX.md` should no longer
route future readers to the missing July 5 held source as active/current
evidence without disposition. The current active tracked record is this
reconciliation packet plus the PR #94 post-merge packet.

The held source remains source evidence with verified hash, not a tracked spec,
implementation, OpenAPI snapshot, provider descriptor/adaptor change, Runtime
route beyond preflight, generated media, or acceptance artifact.

## Verification Results

- Starting base contained PR #95 merge
  `26512312eb6c6f311108c97b906667dfbf21b6b9`; `HEAD` and `origin/master`
  both contained that commit before edits.
- Held source existed at the primary checkout source location and matched the
  expected SHA256 listed above before use.
- Changed path boundary: only `DEVLOG.md`, `TASK_TRACKER.md`,
  `docs/handoff/INDEX.md`, and this new handoff packet.
- `git diff --check`: passed.
- Staged whitespace check: passed before commit.
- Added-line scans for local absolute paths, raw thread ids, credential-marker
  patterns, finality/readiness/capability leakage, provider/media/
  runtime/source-KB/COS promotion, and original source restoration: passed after
  intended non-claim/status vocabulary review.
- Tests were not run because this lane changes only Markdown records and does
  not modify code, schemas, OpenAPI snapshots, provider descriptors/adapters,
  Runtime routes, Studio JavaScript, generated media, browser/runtime/server
  surfaces, or deployment state.

## Non-Claims

This packet does not claim:

- true local-edit execution or provider capability;
- local pixel/image transformation;
- generated media, media QA, provider call, provider spend, or provider gate
  mutation;
- full-frame fallback execution or fallback acceptance as true local edit;
- submit, poll, preview, safe manifest, local-edit bridge, or candidate review
  implementation;
- Runtime server/browser action, loaded-code freshness, release, deploy, or
  restart;
- schema/OpenAPI/provider descriptor finality;
- Owner, human, business, legal, public, customer, creative, or package
  acceptance;
- source-KB, COS, CompanyOS, or durable-memory mutation;
- archive execution or self-archive.

## Residual Risks

- The July 5 source remains held evidence outside the tracked handoff set; any
  later restoration must re-verify source provenance and hash.
- Future implementation lanes must avoid treating provider descriptor metadata
  or fallback labels as execution capability.
- Submit/poll/preview, mask storage, lineage lookup, provider-gate-open
  behavior, safe manifests, generated-media QA, and evaluator acceptance remain
  separate gates.
- The current records are intentionally non-final; a decision-owner still needs
  to route whether the next lane is evaluator/publication decision or bounded
  implementation.

## Closeout

archive_policy: `no self-archive`

upward_feedback_delivery: `sent_to_ceo`

post_closeout_next_action: route reconciliation evaluator/publication decision;
no auto-implementation, provider/runtime/browser action, release, deploy,
acceptance, package finality, or source restoration is valid from this packet.
