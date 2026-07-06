# AFS Studio Package Project Book Draft - 2026-07-06

Status: `non-final / owner_review_draft`

This is an Owner-facing review draft for the current AFS Studio
asset/video/local-edit package posture after PR #94 and PR #95 were merged.
It is a package map and decision aid only. It is not a release note, launch
packet, acceptance record, deployment record, provider authorization, or
business/legal/public approval.

## Product Surface

Current product surface:

- User-facing entry: Runtime-hosted `/studio/` internal tryout and review
  surface.
- Source surface: `apps/studio/`.
- Frontend backend boundary: Runtime Service only.
- Provider posture: LLM, ASR, image, video, and external download gates remain
  closed unless a later task explicitly opens one capability with scope,
  source, destination, cost/risk boundary, and cleanup route.

Old Workbench, memory-workbench, and legacy distribution chains are not the
current package surface for this draft.

## Capability Inventory

| Capability area | Current package posture | Review boundary |
|---|---|---|
| Reference upload and Runtime error UX | Studio normalizes structured Runtime error bodies and locally blocks unsupported reference upload targets/file types before Runtime upload. | No browser/server/provider claim is added by this draft. |
| Fixed asset reuse and link intent | Runtime/Studio can preserve graph-bound fixed asset context and require explicit `link_existing`, `replace`, or `create_new` intent for duplicate/reuse situations. | Duplicate prevention and reuse behavior still need broader live path review before stronger operational claims. |
| Keyframe and video honesty | Studio copy separates whole-image/whole-video regeneration attempts from unsupported true local edit. Local-edit availability is shown as gated/unavailable where mask or temporal edit capability is absent. | This does not claim true provider-backed local edit, mask capability, or generated-media quality. |
| Runtime-backed local-edit preflight and Studio persistence | PR #94 wires Studio-to-Runtime local-edit preflight so explicit-scope local-edit requests can be represented as no-provider/no-media/no-local-transform preflight evidence. The P2 fix keeps missing-scope node-menu drafts blocked until user scope is supplied. | The path remains a preflight/review gate, not pixel transformation or provider execution. |
| Final-media decision packet route | The decision packet route can consume structured QA packet refs and explicit reviewer action without recalculating checklist truth. | It cannot create human creative acceptance or final media approval without the later reviewer gate. |
| Post-merge records state | PR #95 merged the evaluated PR #94 post-merge records package into `master`. | Records integration is governance/evidence progress only; it is not product release, runtime freshness, cleanup completion, or Owner acceptance. |

## Evidence Map

| Evidence item | Current readback | Source |
|---|---|---|
| PR #94 | Merged PR: `https://github.com/es-dra/AgentFlowStudio/pull/94` | GitHub connector PR readback |
| PR #94 head before merge | `6cee1511d2c72c951271325aeefb80076f62cf9d` | GitHub connector PR readback |
| PR #94 merge commit | `25b492f010f3a95ed3ae52ea298132052b2e67eb` | GitHub connector PR readback and local history |
| PR #94 post-merge CI | `AFS Maintenance Gate #205`, push to `master` for `25b492f`, status success, duration `3m 22s`, one non-failing Node.js 20 deprecation warning | GitHub Actions run `28766187584` |
| PR #95 | Merged PR: `https://github.com/es-dra/AgentFlowStudio/pull/95` | GitHub connector PR readback |
| PR #95 head before merge | `f717c4ffe6b3bfac4ce28b15aa7e6069cc03e59b` | GitHub connector PR readback |
| PR #95 merge commit | `26512312eb6c6f311108c97b906667dfbf21b6b9` | GitHub connector PR readback and local history |
| PR #95 exact-head PR CI | `AFS Maintenance Gate #206`, pull-request run for `f717c4f`, completed/success | GitHub connector workflow readback |
| PR #95 post-merge CI | `AFS Maintenance Gate #207`, push to `master` for `2651231`, status success, duration `3m 49s`, one non-failing Node.js 20 deprecation warning | GitHub Actions run `28767206361` |
| No-provider live QA | Prior PR #94 package body records local Runtime with provider/external gates false, seeded keyframe local-edit browser path, no forbidden provider/generation/upload/transform routes, and cleanup success. | PR #94 package body; this draft does not copy local screenshot paths. |
| Focused static/API tests | Current PR/package records include focused local-edit pytest, Studio JS checks, py-compile, focused reference upload, fixed asset reuse, keyframe/video honesty, QA checklist, and final-media decision packet checks. | DEVLOG and handoff records listed below |
| Record handoff | `docs/handoff/AFS-P1-STUDIO-RUNTIME-LOCAL-EDIT-PREFLIGHT-PR94-POSTMERGE-20260706.md` | Local repo |

## Evidence Caveats

These caveats are carried forward as review boundaries, not as new current
capability evidence:

- Prior package/control evidence: T50/T51 and D2/D5/T54-T58 remain prior
  deterministic/control evidence. They do not establish Owner/package
  readiness, acceptance, finality, release, or current package capability by
  themselves.
- Generation-plan guardrail: D2/D5 and T54-T58 can inform later planning only
  after evaluator and Owner gates. They must not be used as
  accepted-generation-plan or project-book finality evidence without that later
  review.
- Current-checkout evidence: any Neon Rain or static-skeleton references are
  historical/current-checkout-suspended context only, not current package
  capability evidence for this PR.
- Runtime freshness: loaded-code/runtime freshness remains a separate ops
  lane. Prior runtime blockers or server facts are not current facts unless an
  authorized runtime lane revalidates them.

## Operational Boundary

This package draft may reference safe public GitHub URLs, commit SHAs, run
numbers, and repo-relative handoff paths. It must not introduce:

- secrets, tokens, cookies, provider keys, signed URLs, or auth material;
- raw provider responses;
- generated media bytes or local private media bytes;
- new local private absolute paths;
- provider/video/download authorization;
- runtime freshness, deployment, restart, or public-edge claim unless that
  state is separately verified in an authorized runtime lane.

Runtime verification, provider smoke, generated-media QA, human review,
business validation, legal/public judgment, and Company OS rule promotion
remain separate evidence states.

## Non-Claims Map

This draft does not claim:

- release, deploy, restart, server sync, or runtime loaded-code freshness;
- Runtime server run, Studio browser QA, or live `/studio/` operator approval
  in this lane;
- provider call, provider spend, provider gate mutation, provider readiness,
  image/video generation, video generation, or external download;
- generated media, generated-media QA, local pixel/image transform, true local
  edit provider capability, mask capability, or full-frame fallback;
- final media approval, Owner acceptance, human creative acceptance, business
  validation, legal approval, public launch, customer validation, or patent
  readiness;
- package finality, cleanup completion, archive execution, or self-archive;
- source-KB, COS, CompanyOS, durable-memory, or active-rule mutation.

## Residual Gate Map

| Gate | Why it remains open | Candidate owner |
|---|---|---|
| Mobile/responsive review | Recent evidence is focused on local/static or seeded desktop paths, not broad viewport coverage. | Studio reviewer / QA |
| Multiple node shapes | Local-edit and reference behavior need broader node-type coverage beyond the focused paths. | Studio/Runtime worker plus evaluator |
| Auth-on Runtime behavior | Package posture does not prove the same routes under auth-on Runtime conditions. | Runtime/API evaluator |
| Provider-gate-open behavior | Current posture is provider-closed; opening any provider changes risk, cost, and evidence requirements. | Owner/CTO/ops gatekeeper |
| Generated-media QA | Static/API success does not validate image/video quality or creative fit. | Media QA evaluator / human reviewer |
| Human creative acceptance | Engineering evidence can route a reviewer packet but cannot supply creative acceptance. | Owner or named creative reviewer |
| Runtime freshness/deploy/readiness | CI and merge evidence do not prove loaded runtime code, deployment, restart, or public edge state. | Ops/runtime lane |
| Cleanup/worktree hygiene | Records/package docs do not close cleanup, stale worktree, or archive decisions. | CEO/COO/maintenance lane |
| Reviewer identifiers | Some reviewer-hold identifiers remain absent or unresolved in the current record trail. | CEO/PR reviewer routing |

## Owner Decision Map

| Decision | Options | Consequence |
|---|---|---|
| Package split and order | Keep this draft as a map over separate packets, or authorize a future merged Owner packet. | Keeps evidence states separate unless Owner chooses a merge lane. |
| Review this draft | Route to package evaluator/reviewer, request wording changes, or defer. | A reviewer lane is required before any stronger Owner-facing claim. |
| Provider/media authorization | Keep gates closed, or authorize an exact capability lane later. | Any provider/media lane needs scope, cost/risk boundary, artifact route, and cleanup plan. |
| Runtime freshness lane | Defer, or authorize runtime/server/browser freshness verification. | Required before any loaded-code, deploy, public-edge, or operational claim. |
| Human creative review | Defer, or assign reviewer/rubric/artifact route. | Required before any creative acceptance or final media decision. |

## Next Lanes

Recommended sequence:

1. Package evaluator/reviewer lane checks this draft against PR #94/#95,
   current handoffs, non-claims, and residual gates.
2. Owner decides whether this should stay as a map over separate packets or be
   converted into a narrower Owner review packet.
3. Only after explicit authorization, open separate lanes for provider/media,
   runtime freshness, mobile/responsive QA, or human creative review.

No automatic release, deploy, provider/media action, runtime/browser action,
cleanup execution, archive execution, or acceptance claim follows from this
draft.

## References

- PR #94: `https://github.com/es-dra/AgentFlowStudio/pull/94`
- PR #95: `https://github.com/es-dra/AgentFlowStudio/pull/95`
- PR #94 post-merge CI #205:
  `https://github.com/es-dra/AgentFlowStudio/actions/runs/28766187584`
- PR #95 post-merge CI #207:
  `https://github.com/es-dra/AgentFlowStudio/actions/runs/28767206361`
- Handoff index: `docs/handoff/INDEX.md`
- PR #94 post-merge record:
  `docs/handoff/AFS-P1-STUDIO-RUNTIME-LOCAL-EDIT-PREFLIGHT-PR94-POSTMERGE-20260706.md`
- Reference upload/error UX:
  `docs/handoff/AFS-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705.md`
- Fixed asset reuse/link intent:
  `docs/handoff/AFS-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705.md`
- Keyframe/video honesty:
  `docs/handoff/AFS-P1-KEYFRAME-LOCAL-EDIT-UX-HONESTY-20260705.md`
- Final-media decision packet:
  `docs/handoff/AFS-P0-FINAL-MEDIA-ACCEPTANCE-LINKED-QA-DECISION-PACKET-20260705.md`
- Owner package landing index:
  `docs/handoff/AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md`
- Owner package checklist:
  `docs/handoff/AFS-OWNER-REVIEW-PACKAGE-LANDING-CHECKLIST-20260703.md`

## Appendix A - Worker Record

The human-facing package map is the body above. This appendix is execution
ledger metadata only and does not create package readiness, finality,
acceptance, release, runtime, provider, media, cleanup, or Company OS claims.

| Field | Value |
|---|---|
| top_down_dispatch_id | `TD-AFS-V02-DOC-P1-PR-96-PACKAGE-DRAFT-OWNER-PACKET-DELTA-EXTRACTION-NO-RELEASE-20260706-001` |
| bottom_up_feedback_id | `BU-AFS-V02-DOC-P1-PR-96-PACKAGE-DRAFT-OWNER-PACKET-DELTA-EXTRACTION-NO-RELEASE-20260706-001` |
| Worker verdict | `PASS_DELTA_EXTRACTION_PENDING_EVALUATOR_OR_CI_MONITOR` |
| Task class | `Standard` docs-only package delta extraction |
| Write scope | This handoff. The wider PR already includes `docs/handoff/INDEX.md`, `DEVLOG.md`, and `TASK_TRACKER.md` from the original package publication lane. |
| Provider gate | Closed for LLM, ASR, image, video, external download, live provider calls, provider smoke, and generated-media QA |
| Tests | Not run; docs-only lane with no code, schema, OpenAPI, Runtime, Studio JS, provider config, or generated-media changes |
| archive_policy | `no self-archive` |
| upward_feedback_delivery | `sent_to_ceo` |
| post_closeout_next_action | Evaluator/reviewer or CI monitor should review the new PR #96 head before any Owner-facing acceptance, release, readiness, public, provider, media, or finality claim. |

Verification route for this lane:

- Confirm branch/head, PR #96 draft/open/unmerged state, and base
  `26512312eb6c6f311108c97b906667dfbf21b6b9`.
- Confirm this delta-extraction commit writes only this handoff, with total PR
  path set remaining within the existing allowed docs/package paths.
- Run stale/overclaim scan for release/deploy/provider/media/acceptance/
  finality claims.
- Run secret/path scan.
- Run `git diff --check`.
- Commit and non-force push only if checks pass. Do not mark PR #96 ready for
  review, merge, release, deploy, runtime, provider, media, acceptance, or
  finality.
