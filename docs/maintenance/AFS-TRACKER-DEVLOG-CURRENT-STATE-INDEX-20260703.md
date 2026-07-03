# AFS Tracker Devlog Current State Index - 2026-07-03

Status: `additive_docs_maintenance_lane`

Close state: `current_state_index_added_pending_owner_cto_prune_gate`

This index gives maintainers a short current-state entry for oversized
`TASK_TRACKER.md` and `DEVLOG.md` streams. It is additive only. It does not
remove, rewrite, archive, prune, or consolidate any old tracker or devlog
content.

## Dispatch

| Field | Value |
|---|---|
| Source thread | `019f25c8-37c9-7e30-8c57-279e40a3a1fc` |
| Lane | `IMP-P1-TRACKER-DEVLOG-CURRENT-STATE-INDEX-ADDITIVE` |
| Top-down dispatch | `TD-AFS-V02-IMP-P1-TRACKER-DEVLOG-CURRENT-STATE-INDEX-ADDITIVE-20260703-001` |
| Bottom-up feedback | `BU-AFS-V02-IMP-P1-TRACKER-DEVLOG-CURRENT-STATE-INDEX-ADDITIVE-20260703-001` |
| Task class | `Standard` docs-only maintenance |
| Write scope | This file, short pointer blocks in `TASK_TRACKER.md` and `DEVLOG.md`, and one optional `docs/handoff/INDEX.md` maintenance evidence link |
| Provider gate | Closed for LLM, ASR, image, video, external download, provider smoke, live provider calls, and generated-media QA |
| Handoff location | No new handoff file; maintenance route is this file plus `docs/handoff/INDEX.md` current maintenance evidence |

Startup protocol:

- `project-development-workflow` was not exposed; fallback startup scan used
  `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md`,
  `DEVLOG.md`, and `docs/handoff/INDEX.md`.
- `fractal_decomposition_probe` was not exposed:
  `manual_completed_no_tool_exposed`.
- Manual surface split completed:
  `maintenance_index`, `tracker_pointer`, `devlog_pointer`,
  `handoff_index_link`.

## Dirty Ownership Ledger

Pre-write status observed in `/home/afs-ops/AgentFlowStudio`:

```text
## master...origin/master [ahead 1]
 M docs/handoff/INDEX.md
?? docs/demo/
?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md
```

Ownership:

| Path | Pre-existing state | Lane action |
|---|---|---|
| `docs/handoff/INDEX.md` | Modified before this lane; existing diff adds Owner Review / Package Landing block | Preserve existing block; add only one maintenance evidence link if needed |
| `docs/demo/` | Untracked before this lane | Do not read, stage, edit, move, delete, or use as cleanup input |
| `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md` | Untracked before this lane | Do not read, stage, edit, move, delete, or use as cleanup input |

No branch, checkout, fetch, pull, merge, rebase, reset, clean, commit, push,
runtime operation, server operation, deploy, install, or build was authorized
for this lane.

## Canonical Current Entrypoints

| Surface | Current entry | Boundary |
|---|---|---|
| Product UI | `/studio/` | Current user-facing Web entry |
| Frontend source | `apps/studio/` | Studio canvas and review surfaces |
| Backend boundary | Runtime Service | Only frontend backend boundary; frontend must not consume CLI internals |
| Project rules | `AGENTS.md`, `docs/company_operating_model.md` | Rule hierarchy, provider gates, maintenance and recording rules |
| Current task streams | `TASK_TRACKER.md`, `DEVLOG.md` | Long live streams retained until refscan and Owner/CTO gates |
| Handoff route | `docs/handoff/INDEX.md` | Current handoff and maintenance evidence index |
| Historical docs route | `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` | Summary-first historical evidence entry |
| Cleanup ledger route | `docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` | Currentness cleanup decisions and recovery path |

## Release And Current-State Summary

AFS remains a local internal-test MVP line, not SaaS and not a commercial or
public release. The current main path is:

```text
/studio/ canvas -> Runtime Service -> prompt optimization -> fixed visual assets
  -> graph context resolver -> provider-gated keyframe/image evidence
```

Current tracked state:

- P0 Runtime + Studio state recovery is an integration candidate with safe
  runtime recovery envelopes and Studio recovery surfaces; it is not a merge,
  push, deploy, runtime-loaded-code freshness, provider, or media QA claim.
- I2 records integration/server hash sync and ready health checks, while
  explicitly not claiming runtime loaded-code freshness.
- Provider-closed accepted-plan, package, and internal tryout records are
  structure evidence only.
- REL1B/provider auth remains blocked pending Owner-approved auth material and
  explicit capability authorization.

## Current Blockers And Decision Gates

| Gate | Current status | Required before stronger claim |
|---|---|---|
| Provider auth / REL1B | Blocked | Owner-approved auth material, exact capability, source, save path, cleanup strategy, and task-level authorization |
| Runtime loaded-code freshness | Not claimed | Separate ops authorization and fresh verification route |
| Provider smoke | Not claimed | Explicit provider gate and smoke scope |
| Generated-media QA | Not claimed | Reviewer, rubric, artifact route, and authorized run |
| Human acceptance | Not claimed | Completed human review/scoring packet |
| Product/business/public/legal readiness | Not claimed | Separate Owner/CTO/business/legal gates |
| CompanyOS/COS promotion | Not claimed | Candidate/limited feedback route only; no active-rule promotion by agent |

## Historical Summary Map

Use these summary documents before reading or pruning old stream content:

| Need | Entry |
|---|---|
| Historical docs summary and currentness map | `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` |
| C1/C2 cleanup ledger, deleted archive recovery path, and remaining debt | `docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` |

Historical tracker/devlog material remains evidence until a future lane proves
specific references are safe to remove.

## Tracker And Devlog Retention Rule

No old-stream content in `TASK_TRACKER.md` or `DEVLOG.md` may be removed,
rewritten, archived, consolidated, or pruned until all of the following pass:

1. A docs reference scan identifies the exact old content and all active
   references.
2. A proposed replacement route or summary is written and reviewed.
3. Owner and CTO gates authorize the specific pruning action.
4. Required maintenance verification runs, including `git diff --check` and
   maintenance audit when applicable.

This lane only adds current-state pointers. It is not that pruning lane.

## Version Fields For Owner Review

These are routing fields, not completed version claims.

| Field | Draft meaning | Owner/CTO gate |
|---|---|---|
| `v0.3.1` | Current-state entrypoints are linked from tracker/devlog and the maintenance evidence index. | Confirm this is the current docs landing route. |
| `v0.4` | Tracker/devlog pruning remains blocked pending docs refscan and Owner/CTO gate. | Decide whether to authorize a future compact/prune lane. |
| `v0.5` | Provider/live smoke, generated-media QA, project-scoped accepted plan, and human review remain separate gates. | Authorize exact gates individually, if any. |
| `v0.5.1` | Runtime loaded-code freshness and post-integration smoke refresh remain separate ops gates. | Authorize freshness/smoke scope before stronger operational claims. |

## Non-Claims

This lane makes no claim of:

- pruning, deletion, archive, consolidation, cleanup completion, or history
  rewrite;
- package completion or release readiness;
- provider auth readiness, provider smoke, live provider call, or provider
  completion;
- generated-media QA or human acceptance;
- product, business, public, legal, patent, or commercial readiness;
- Runtime loaded-code freshness, deploy, server sync, or service restart;
- OpenAPI, DOC2, CompanyOS/COS active-rule promotion, or durable-memory
  promotion.

## Verification Record

Pre-write check:

```text
git status --short --branch
# ## master...origin/master [ahead 1]
#  M docs/handoff/INDEX.md
# ?? docs/demo/
# ?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md
```

Post-write checks:

```text
python3 - <<'PY'
from pathlib import Path
root = Path('/home/afs-ops/AgentFlowStudio')
index = root / 'docs/handoff/INDEX.md'
text = index.read_text(encoding='utf-8')
needle = '`../maintenance/AFS-TRACKER-DEVLOG-CURRENT-STATE-INDEX-20260703.md`'
target = (index.parent / '../maintenance/AFS-TRACKER-DEVLOG-CURRENT-STATE-INDEX-20260703.md').resolve()
print('contains_new_link=', needle in text)
print('target_exists=', target.exists())
print('target=', target.relative_to(root))
raise SystemExit(0 if needle in text and target.exists() else 1)
PY
# contains_new_link= True
# target_exists= True
# target= docs/maintenance/AFS-TRACKER-DEVLOG-CURRENT-STATE-INDEX-20260703.md

python3 tools/maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings are existing maintenance categories: legacy frozen surface,
# human-doc Chinese coverage, secret-like fragments, and oversized files.

git diff --check
# passed; no output

git status --short --branch
# ## master...origin/master [ahead 1]
#  M DEVLOG.md
#  M TASK_TRACKER.md
#  M docs/handoff/INDEX.md
# ?? docs/demo/
# ?? docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md
# ?? docs/maintenance/AFS-TRACKER-DEVLOG-CURRENT-STATE-INDEX-20260703.md
```
