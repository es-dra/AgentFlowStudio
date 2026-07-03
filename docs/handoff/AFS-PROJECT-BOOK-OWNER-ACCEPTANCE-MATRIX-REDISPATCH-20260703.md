# AFS Project Book Owner Acceptance Matrix Redispatch - 2026-07-03

Status: `draft / owner_review_acceptance_matrix`

Close state: `project_book_owner_acceptance_matrix_update_redispatch_completed`

This document is an Owner-facing acceptance matrix for the Project Book package
landing route. It is a review and decision aid only. It does not claim package
completion, human acceptance, product readiness, provider readiness, generated
media quality, public/business/legal readiness, or CompanyOS/COS promotion.

## Dispatch

| Field | Value |
|---|---|
| Source thread | `019f25c8-37c9-7e30-8c57-279e40a3a1fc` |
| Lane | `DOC-P1-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-UPDATE-REDISPATCH` |
| Top-down dispatch | `TD-AFS-V02-DOC-P1-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-UPDATE-REDISPATCH-20260703-001` |
| Expected BU | `BU-AFS-V02-DOC-P1-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-UPDATE-REDISPATCH-20260703-001` |
| Route basis | CTO disposition `accept_pending_worktree_materialization_failures_supersede_and_redispatch` and `accept_recovery_sweep_and_supersede_unrecovered_materialization_failures` |
| Superseded pendingWorktreeId | `remote-ssh-discovered:afs-bwg-ops:792b0510-ea03-46c0-a0c6-8bd06486cad4` |
| Task class | `Standard` docs-only update because this adds a matrix and updates routing records |
| Write scope | This handoff, `docs/handoff/INDEX.md`, `TASK_TRACKER.md`, `DEVLOG.md` |
| Handoff location | `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md` |
| Provider gate | Closed for LLM, ASR, image, video, external download, provider smoke, live provider calls, and generated-media QA |

Startup protocol:

- `project-development-workflow` was not exposed; fallback startup scan used
  `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md`, and
  `docs/handoff/INDEX.md`.
- Source docs used for this matrix:
  `docs/handoff/AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md` and
  `docs/handoff/AFS-OWNER-REVIEW-PACKAGE-LANDING-CHECKLIST-20260703.md`.
- The superseded old pending worktree was not used, waited on, fetched, pulled,
  pushed, merged, or repaired.
- No source-KB, DOC2, OpenAPI, CompanyOS, COS, Runtime, Studio, provider,
  generated-media, deploy, restart, server, branch, archive, cleanup, delete,
  move, or config path was mutated.

## Dirty Ownership Ledger

Pre-write status observed in `/home/afs-ops/AgentFlowStudio`:

```text
## master...origin/master [ahead 5]
?? docs/demo/
?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md
```

| Path | Pre-existing state | Lane action |
|---|---|---|
| `docs/demo/` | Untracked before this lane | Preserved; not used as source evidence, edited, staged, moved, deleted, archived, or cleaned |
| `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md` | Untracked before this lane | Preserved; not used as source evidence, edited, staged, moved, deleted, archived, or cleaned |
| `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md` | Absent before this lane | Added as the bounded Owner acceptance matrix |

Maintenance ledger: this is an additive docs-only routing update. It performs no
cleanup, pruning, deletion, archive, branch movement, source-sync, provider
operation, runtime operation, or legacy route migration.

## Source Boundary

| Source | How it is used |
|---|---|
| `AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md` | Navigation map for current Owner review landing, evidence groups, decision surfaces, version fields, and non-claims |
| `AFS-OWNER-REVIEW-PACKAGE-LANDING-CHECKLIST-20260703.md` | Stage A-H source checklist for Owner review, package split, `/studio/`, SPEC2, provider/media, ops, and human/business/legal/COS gates |
| `docs/handoff/INDEX.md` | Current handoff routing entry, including Owner Review / Package Landing |
| `TASK_TRACKER.md` and `DEVLOG.md` | Project-level record locations for this docs-only redispatch |

Out of scope as source: deleted or retired Workbench routes, old pending
worktree materialization, source-KB private files, provider raw responses,
generated media, runtime-loaded code claims, and non-repo commercial or legal
judgments.

## Owner Acceptance Matrix

| Matrix row | Current evidence from owner index/checklist | Owner can accept or decide | Still blocked / not accepted | Next action |
|---|---|---|---|---|
| 1. Landing route and audience | Owner index is `draft / owner_review`; checklist applies CPO decision `owner_review_first`; current entry is Runtime-hosted `/studio/` with source `apps/studio/` and Runtime Service as frontend backend boundary | Accept this as the Owner review landing route and reviewer ordering aid | Does not accept package completion, product readiness, public route, SaaS scope, or commercial package | Owner confirms whether Owner review remains first audience |
| 2. Package split and packet ordering | Owner index keeps Project Book evidence groups separate; checklist keeps Project Book, internal tryout, SPEC2, accepted-plan, recovery/current-state packets separate | Decide split/merge policy and packet ordering for future review | No merged package, no single final packet, no package-complete claim | Owner records keep-split or future merge instruction |
| 3. `/studio/` internal tryout path | `/studio/` is current user-facing Web entry; D5/T51/T50/T47 style evidence is provider-closed internal tryout structure evidence | Accept `/studio/` as internal tryout/review surface only | No human acceptance, generated-media QA, provider smoke, deploy/runtime freshness, or public readiness | If needed, authorize a separate internal tryout run and reviewer packet |
| 4. SPEC2 and accepted generation plan route | T53-T58, C, and D2 describe package contracts, residual boundary, generation planning, fixed-asset confirmation, and accepted-plan preview gate | Accept SPEC2 as contract-structure review evidence | Fixture/demo evidence is not accepted; no Runtime/OpenAPI/Studio/provider/media readiness follows from contract docs alone | Future accepted state requires project-scoped source artifact plus matching human-gate decision |
| 5. Provider and generated-media gates | Owner index and checklist keep provider/live smoke and generated-media QA as future gates | Decide whether to authorize exact capability, scope, cost/risk boundary, source, save path, cleanup, and reviewer rubric | No provider auth readiness, provider completion, post-integration smoke, image/video QA, or media quality claim | Open a separate authorized provider/media lane only if Owner approves |
| 6. Runtime recovery and ops freshness | I2 records server hash sync and `/health` readiness while blocking loaded-code freshness; P0 state recovery is an integration candidate route | Decide whether runtime freshness, restart, deploy, merge, or recovery integration needs a separate ops lane | No deploy, restart, runtime loaded-code freshness, merge, push, or operational readiness claim | Owner/ops authorizes exact runtime freshness or recovery follow-up if needed |
| 7. Human acceptance | Internal acceptance routes and runbooks exist; checklist says engineering evidence can only route review | Decide reviewer, rubric, artifact route, and human scoring packet | No human creative acceptance or final IP/media acceptance | Human reviewers complete a separate scoring packet |
| 8. Business, legal, public, COS, memory | Owner index and checklist keep these as independent gates | Decide whether any future business/legal/public/COS candidate route is warranted | No business validation, public/legal/patent readiness, durable memory promotion, or COS active-rule promotion | Route future feedback through candidate/limited process only |
| 9. Archive and closeout | Checklist defines archive policy; this redispatch keeps it explicit | Accept archive policy for this worker's thread after ACK delivery confirmation | Worker must not self-archive; no destructive archive action here | Owner ACKs delivery; app-level archive can occur only after ACK if useful |

## Version Fields

These are route fields, not completed version claims.

| Field | Matrix meaning | Required Owner gate |
|---|---|---|
| `v0.3.1` | Owner review landing route is explicit: Owner index is the map, this matrix is the acceptance aid, `/studio/` is the current internal tryout entry, and Runtime Service is the frontend boundary | Owner confirms audience-first routing and matrix usefulness |
| `v0.4` | Package split remains in force across Project Book evidence, internal tryout, SPEC2 generation-plan contract, accepted-plan packet, and recovery/current-state packets | Owner decides future split/merge and packet ordering, if any |
| `v0.5` | Provider/live smoke, generated-media QA, project-scoped accepted plan, and human review remain separate future gates | Owner authorizes exact gate execution with capability, scope, reviewer, artifact route, and cleanup boundary |
| `v0.5.1` | Runtime loaded-code freshness and post-integration smoke refresh remain separate ops gates | Owner or ops authorizes restart/freshness/smoke scope before any stronger operational claim |

## Non-Claims

This matrix does not claim:

- package completion;
- public publish readiness;
- provider auth readiness, provider smoke, live provider call, provider
  completion, or post-integration live provider evidence;
- generated-media QA or image/video quality;
- human creative acceptance;
- product, business, commercial, public, legal, or patent readiness;
- Runtime loaded-code freshness, server restart, deploy, merge, push, or
  runtime operational readiness;
- OpenAPI, DOC2, CompanyOS/COS mutation, active-rule promotion, or durable
  memory promotion;
- source-sync, fetch, pull, push, or branch/worktree recovery.

## Validation

No-op/docs validation for this lane:

```text
git status --short --branch
# ## master...origin/master [ahead 5]
#  M DEVLOG.md
#  M TASK_TRACKER.md
#  M docs/handoff/INDEX.md
# ?? docs/demo/
# ?? docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md
# ?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md

git diff --check
# passed; no output

test -f docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md
# matrix exists

rg -n "AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md" docs/handoff/INDEX.md TASK_TRACKER.md DEVLOG.md
# found in DEVLOG.md, TASK_TRACKER.md, and docs/handoff/INDEX.md

wc -l docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md
# 165
```

CLI, pytest, maintenance audit, Runtime, Studio, provider, server, and OpenAPI
checks are not part of this bounded docs-only redispatch.

## Archive Policy

| Field | Value |
|---|---|
| `archive_after_ack_delivery_confirmed` | `true` |
| `owner_manual_archive_excluded` | `no` |
| `thread_archive_policy` | `agent_created_archive_when_useless` |

This lane must not self-archive. Archive requires ACK delivery confirmation.

## Post-Closeout Next Action

Owner should review this matrix against the owner index and checklist, then
confirm one of:

- accept the matrix as the current Owner review aid;
- request a narrower matrix row or wording change;
- authorize a separate follow-up lane for package split/merge, project-scoped
  accepted-plan evidence, provider/media QA, runtime freshness, or human review.
