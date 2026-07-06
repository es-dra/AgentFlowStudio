# AFS P1 Dirty Primary Held Evidence Manifest

Date: 2026-07-06

top_down_dispatch_id: `TD-AFS-V02-WORK-P1-DIRTY-PRIMARY-HELD-EVIDENCE-MANIFEST-CLEAN-BRANCH-READWRITE-20260706-001`

bottom_up_feedback_id: `BU-AFS-V02-WORK-P1-DIRTY-PRIMARY-HELD-EVIDENCE-MANIFEST-CLEAN-BRANCH-READWRITE-20260706-001`

Branch: `codex/dirty-primary-held-evidence-manifest-20260706`

Base evidence: clean branch created from `26512312eb6c6f311108c97b906667dfbf21b6b9`, PR #95 merge.

Internal source checkout used only for hash readback: `D:\Projects\AgentFlowStudio`.

## Purpose

Preserve dirty-primary held evidence identities on a clean branch without landing,
restoring, replaying, or promoting the held files as current content.

This manifest records path, byte size, sha256, source classification, hold
reason, and current route only. It does not copy the held source packet prose.

## Source Decisions Consumed

- `BU-AFS-V02-REVIEW-P1-DIRTY-PRIMARY-CHECKOUT-DISPOSITION-READONLY-20260706-001`: `PASS_DIRTY_PRIMARY_DISPOSITION_PATHLIST`
- `BU-AFS-V02-REVIEW-P1-DIRTY-PRIMARY-PRESERVATION-REPLAY-SYNC-DECISION-READONLY-20260706-001`: `PASS_DIRTY_PRIMARY_REPLAY_DECISION_PATHLIST`
- `BU-AFS-V02-DECIDE-P1-DIRTY-PRIMARY-PRESERVATION-REPLAY-SYNC-CTO-20260706-001`: `DECISION_MANIFEST_FIRST`

## Held Evidence Identities

| Path | Size bytes | SHA256 | Source classification | Hold reason | Current route |
|---|---:|---|---|---|---|
| `docs/handoff/AFS-P1-OWNER-PROJECT-BOOK-REVIEW-PACKET-SYNTHESIS-NONFINAL-20260705.md` | 12372 | `6D6BDC022BFC8B7E9C41951B6124DE8D897B133A2A6DF89A8AA4233E11A2C46C` | dirty-primary untracked active non-final Owner-review input | Preserve identity only; decision-owner disposition is required before any package, finality, readiness, or Owner-acceptance use. | Route to Owner/CEO/CTO disposition or evaluator gate before any sync, landing, cleanup, archive, or package claim. |
| `docs/handoff/AFS-P1-TRUE-LOCAL-EDIT-SCHEMA-OPENAPI-CONTRACT-NO-PROVIDER-20260705.md` | 21216 | `4BC203F31D78FB7725B333AEC45F17D3B6DB2CFE06498BB6576C8DA8F86C87AF` | dirty-primary untracked active spec evidence only, no-provider | Preserve identity only; CTO/evaluator/implementation-lane disposition is required before code, OpenAPI, provider, runtime, or schema-acceptance claims. | Route to CTO/evaluator/implementation lane before any sync, demo disposition, provider descriptor, runtime, OpenAPI, or cleanup lane. |
| `docs/demo-docs-20260629/AFS-DEMO-DOCS-CHINESE-20260629.md` | 1772 | `0DF32D3F8FC005E4DCD940E59D278B5016E2953E74B6CC616BEE4896E5FB50C2` | dirty-primary pre-existing untracked demo-docs local state | Preserve identity only; directory remains do-not-touch local state and is not current deliverable content. | Defer until a separate authorized disposition lane; no cleanup, archive, restore, replay, staging, or package claim here. |
| `docs/demo-docs-20260629/AFS-DEMO-PACK-20260629.md` | 4578 | `53828C74D62C84E447DCE34162ED022F8E2CADB5E27B67B4E5195F826C8DAB30` | dirty-primary pre-existing untracked demo-docs local state | Preserve identity only; directory remains do-not-touch local state and is not current deliverable content. | Defer until a separate authorized disposition lane; no cleanup, archive, restore, replay, staging, or package claim here. |
| `docs/demo-docs-20260629/DEMO-1-MANGA-WORKBENCH-DIFFERENTIATION.md` | 10485 | `B281005AE5D7D77C0AF5FA2416AA3AFF395D1BE04074A1E23F6A757BD6537B33` | dirty-primary pre-existing untracked demo-docs local state | Preserve identity only; directory remains do-not-touch local state and is not current deliverable content. | Defer until a separate authorized disposition lane; no cleanup, archive, restore, replay, staging, or package claim here. |
| `docs/demo-docs-20260629/DEMO-2-CORE-TECH-MEMORY-AGENT-FRAMEWORK.md` | 10759 | `8070430411DAD40A7FAD381730F8A738261EADE212EED261AA9BDBD3C4AB10F9` | dirty-primary pre-existing untracked demo-docs local state | Preserve identity only; directory remains do-not-touch local state and is not current deliverable content. | Defer until a separate authorized disposition lane; no cleanup, archive, restore, replay, staging, or package claim here. |
| `docs/demo-docs-20260629/DEMO-TECH-EXECUTION-CHECKLIST.md` | 5726 | `4107C7D57469605D36D279AD93D19F4ED8DE645F04B34BA8330E12E8834A5884` | dirty-primary pre-existing untracked demo-docs local state | Preserve identity only; directory remains do-not-touch local state and is not current deliverable content. | Defer until a separate authorized disposition lane; no cleanup, archive, restore, replay, staging, or package claim here. |

## Verification Record

- Base contains PR #95 merge `26512312eb6c6f311108c97b906667dfbf21b6b9`.
- The two expected fixed source hashes matched the dirty-primary readback.
- The `docs/demo-docs-20260629/*.md` identities were freshly read from the
  dirty-primary checkout and recorded by path, byte size, and sha256.
- The clean branch does not restore, stage, or copy the held source files.
- Tests are not required because this is a docs-only identity manifest with no
  code, schema, OpenAPI, provider, runtime, Studio, or test changes.

## Non-Claims

- No primary dirty file was modified, deleted, moved, staged, committed, or
  replayed.
- No Owner packet, true-local-edit spec, demo-docs content, provider surface,
  code, schema, OpenAPI, Runtime, Studio, or test surface is landed as current
  content by this lane.
- No provider/media/runtime/browser/server action occurred.
- No generated-media QA, cleanup/delete/archive, push/PR/merge/release/deploy,
  restart, package finality, Owner/human/business/legal/public acceptance, or
  COS/CompanyOS/source-KB mutation is claimed.

archive_policy: no self-archive

post_closeout_next_action: route evaluator before any sync, demo disposition,
cleanup, archive, restore, or replay lane.
