# AFS Project Book Package Landing Owner Index - 2026-07-03

Status: `draft / owner_review`

Close state: `owner_index_reconstructed_from_BU_ready`

This owner index reconstructs the missing Project Book package landing owner
index from the registered BU summary and local repository evidence. It does not
read or depend on the missing source worktree path:

```text
/home/afs-ops/.codex/worktrees/c2cb/.../AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md
```

## Dispatch

| Field | Value |
|---|---|
| Source thread | `019f25c8-37c9-7e30-8c57-279e40a3a1fc` |
| Lane | `DOC-P1-PROJECT-BOOK-OWNER-INDEX-RECONSTRUCT-FROM-BU` |
| Top-down dispatch | `TD-AFS-V02-DOC-P1-PROJECT-BOOK-OWNER-INDEX-RECONSTRUCT-FROM-BU-20260703-001` |
| Bottom-up feedback | `BU-AFS-V02-DOC-P1-PROJECT-BOOK-OWNER-INDEX-RECONSTRUCT-FROM-BU-20260703-001` |
| Task class | `Light` docs-only reconstruction |
| Write scope | This file only |
| Provider gate | Closed; no provider call, deploy, restart, build, install, or generated-media QA |
| Handoff location | `docs/handoff/AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md` |

Startup protocol:

- `project-development-workflow` was not exposed; fallback startup scan used
  `AGENTS.md`, `docs/company_operating_model.md`, and `TASK_TRACKER.md`.
- `fractal_decomposition_probe` was not exposed:
  `manual_completed_no_tool_exposed`.
- Dirty ownership preserved: pre-existing untracked `docs/demo/` and
  `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md` remain untouched.

## Current Landing Entry

Owner-facing current entry:

```text
AFS current product entry is Runtime-hosted /studio/.
Source surface: apps/studio/.
Backend boundary: Runtime Service is the only frontend backend boundary.
```

Product framing remains local internal-test MVP work, not SaaS and not a
commercial/public package. Old Workbench and memory-workbench surfaces are not
current product entrypoints.

## Evidence Groups

| Group | Local evidence | Owner-readable conclusion |
|---|---|---|
| T47/T50/T51/D5 | `AFS-STUDIO-MAIN-PATH-BROWSER-QA-20260701.md`, `AFS-STUDIO-MAIN-PATH-DELIVERY-READINESS-GATE-20260701.md`, `AFS-T51-PROVIDER-CLOSED-INTERNAL-TRYOUT-PACKET-20260701.md`, `AFS-D5-PROVIDER-CLOSED-READINESS-PACKET-CURRENCY-20260702.md` | `/studio/` can carry the provider-closed Runtime main path through browser QA, delivery readiness, tryout packet, and accepted-plan blocked-preview evidence. This is internal tryout structure evidence only. |
| T53-T58 | T53 interactive manga branch package, T54 branch workflow package, T55 residual boundary, T56 generation-planning gate, T57 fixed-asset confirmation, T58 accepted generation plan packet handoffs | Deterministic package contracts exist through an accepted local generation plan packet path. They are structure evidence only and do not create Runtime/OpenAPI/Studio/provider/media readiness by themselves. |
| C/D2 | `AFS-ACCEPTED-GENERATION-PLAN-RUNTIME-STUDIO-BRIDGE-20260702.md`, `AFS-D2-ACCEPTED-GENERATION-PLAN-HARDENING-20260702.md` | Runtime/Studio expose a provider-closed accepted-plan preview/review bridge. D2 hardens the path so fixtures remain blocked demo evidence and accepted project packets require project-scoped source evidence plus matching human-gate decision. |
| I2/P0 | `AFS-I2-HARDENING-INTEGRATION-MERGE-SERVER-SYNC-20260702.md`, `AFS-P0-STATE-RECOVERY-INTEGRATION-CANDIDATE-20260703.md` | I2 records integration/server hash sync and ready health checks while blocking runtime loaded-code freshness. P0 records a recovery integration candidate with safe runtime recovery envelopes and Studio recovery surfaces; no merge/push/deploy claim. |
| Demo/internal acceptance | `AFS-INTERNAL-BETA-ACCEPTANCE-OPERATING-INDEX-20260619.md`, human acceptance runbooks | Internal acceptance has operational routes and review packets. Engineering evidence can reach `contract_verified_pending_human_acceptance`; only completed human scoring can upgrade a run to human acceptance. |
| Post-deploy freshness/smoke ops | T19/T40/I2 runtime health/sync records and `AFS-PROVIDER-SMOKE-READINESS-GATE-20260630.md` | Server hash sync and `/health` readiness have evidence, but runtime loaded-code freshness and post-integration provider smoke are separate gates. Existing E1 evidence is pre-integration external route smoke for one minimal route only. |

## Decision Surfaces

Owner decisions still required:

| Surface | Decision needed | Current state |
|---|---|---|
| Primary audience | Confirm whether this package is for Owner review, internal demo operators, or evaluator routing first. | Draft owner index defaults to Owner review. |
| Package scope split/merge | Decide whether Project Book package, accepted-plan packet, internal tryout packet, and state recovery packet stay separate or become one owner packet. | Evidence suggests separate packets with this owner index as the landing map. |
| Accepted-plan human gate | Decide when a project-scoped accepted plan packet may be marked accepted. | D2 requires matching human-gate decision; fixture demo remains blocked. |
| Provider/live smoke | Explicitly authorize exact capability, cost/risk boundary, source, save path, and cleanup plan before any live provider smoke. | Closed in this task. Existing readiness gates are not authorization. |
| Generated-media QA | Decide reviewer, rubric, and artifact route for generated image/video quality. | Not run and not claimed here. |
| Human/business/public/legal gates | Decide when human acceptance, business validation, public publishing, legal/patent readiness, or COS rule promotion can be evaluated. | All remain separate future gates. |

## Version Fields For Owner Review

These are routing fields, not completed version claims.

| Field | Draft meaning | Owner gate |
|---|---|---|
| `v0.3.1` | Landing index points to `/studio/`, `apps/studio/`, Runtime Service boundary, and provider-closed evidence groups. | Owner confirms current landing entry and audience. |
| `v0.4` | Package-map decision: keep Project Book evidence packets split with this owner index, or merge into a single review package. | Owner chooses split/merge and packet ordering. |
| `v0.5` | Acceptance-route decision: project-scoped accepted plan, provider/live smoke, generated-media QA, and human review become separately authorized gates. | Owner authorizes specific gate execution, if any. |
| `v0.5.1` | Freshness/smoke refresh decision: require runtime loaded-code freshness and post-integration smoke before any stronger operational claim. | Owner or ops authorizes restart/freshness and smoke scope. |

## Non-Claims

This document does not claim:

- package complete;
- public publish readiness;
- business, legal, or patent readiness;
- human acceptance;
- generated-media QA;
- provider completion or post-integration live provider smoke;
- runtime endpoint self-claim or loaded-code freshness;
- product readiness;
- CompanyOS/COS active-rule promotion;
- durable memory promotion.

## Validation

Commands run in `/home/afs-ops/AgentFlowStudio`:

```text
git status --short --branch
# ## master...origin/master
# ?? docs/demo/
# ?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md

find docs/handoff -maxdepth 1 -name AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md -ls
# no output before write; target absent
```

Post-write validation:

```text
git status --short --branch
# ## master...origin/master
# ?? docs/demo/
# ?? docs/handoff/AFS-PROJECT-BOOK-PACKAGE-LANDING-OWNER-INDEX-20260703.md
# ?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md

git diff --check
# passed; no output
```

Scope confirmation: the only new path is this owner index. The pre-existing
untracked `docs/demo/` and
`docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md` remain untouched.
