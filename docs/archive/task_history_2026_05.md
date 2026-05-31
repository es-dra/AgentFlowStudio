# AgentFlow Studio Task History - 2026-05

Status: historical archive created during `AFS-MAINTENANCE-RESET-001`.

This file preserves the pre-reset task history at a readable summary level.
`TASK_TRACKER.md` is now reserved for active, next, and blocked work.

Raw pre-reset tracker bytes were preserved under the ignored path:

```text
data/processed/maintenance_backups/AFS-MAINTENANCE-RESET-001/TASK_TRACKER.pre_reset_original_bytes.md
```

The raw file contained invalid UTF-8 around an old Company memory path, so it
should not remain the live tracker.

## Integrated Or Completed Historical Work

| ID / group | Outcome | Current evidence |
|---|---|---|
| AFS-OPS-001 | completed | Company OS projection into repo-facing docs |
| AFS-MEM-001 / AFS-CTX-001 / AFS-QLT-001 | integrated to `master` | PosterFlow feedback, memory review, context bundle, and quality signal work |
| AFS-DEMO-001 | integrated to `master` | Two-round PosterFlow Memory OS demo hardening |
| AFS-PROV-001 | integrated to `master` | MiniMax PosterFlow provider support replayed on fresh mainline |
| AFS-ALPHA-001 | integrated to `master` | Alpha readiness evidence replay |
| AFS-WEB-001 | archived and superseded | Old independent Web branch archived by tag and replayed later |
| AFS-PROD-001 / AFS-QA-001 / AFS-MEM-002 / AFS-WEB-REPLAY | integrated to `master` | Alpha smoke, evidence summary, memory promotion review, and Web replay |
| AFS-ALPHA-PKG-001 / AFS-WEB-UX-001 / AFS-MEMORY-DEMO-001 / AFS-POSTER-LIVE-001 | completed / integrated | Local Alpha 0.2 package, Web UX, memory demo, and live-smoke blocked evidence |
| AFS-PROD-NEXT-001 / AFS-WEB-REVIEW-001 / AFS-MEMORY-RUNTIME-001 | completed / integrated | Local Alpha 0.3 planning, Web review loop, and promotion/context reuse contract |
| AFS-POSTER-LIVE-002 | remains blocked | No local image-provider env; provider smoke is optional and gated |
| AFS-PROD-LOOP-001 | completed after integration | Local Alpha 0.4 scenario package and runbook |
| AFS-RUN-PACKAGE-001 | completed after local inputs were supplied | Runtime package evidence under ignored `data/processed/runs/local_alpha_0_4_product_loop` |
| AFS-WEB-OPERATOR-002 | integrated with follow-up readiness fix | Web operator defaults and readiness behavior for Local Alpha 0.4 |
| AFS-MEMORY-QUALITY-002 | completed as structural review | Evidence reuse review contract and validator; no durable Memory runtime |
| AFS-ALPHA-0-4-ACCEPTANCE | completed | `docs/local_alpha_0_4_acceptance_reconciliation.md` |
| AFS-KLING-PROVIDER-DRYRUN-001 | completed | Safe request planning and Kling JWT shape validation without live calls |
| AFS-KLING-SMOKE-CLIENTS-001 | completed with local transport caveat | Gated Kling video clients; authenticated video uses `--transport curl` here |
| AFS-MEMORY-ADVANTAGE-DEMO-001 through DEMO-003 | setup/probe/fallback history | Early route probing; not a memory-advantage proof |
| AFS-MEMORY-ADVANTAGE-DEMO-006 through DEMO-011 | intermediate experiment history | Prompt/protocol/reference refinement; should not become product surface as numbered modules |
| AFS-MEMORY-ADVANTAGE-DEMO-012 | early comparison evidence | Fixed character reference -> MiniMax I2I keyframes -> Kling I2V clips |
| AFS-MEMORY-ADVANTAGE-DEMO-013 / DEMO-014 | 15s I2V comparison history | Desert occlusion/recovery material; useful evidence but not definitive proof |
| AFS-MEMORY-ADVANTAGE-DEMO-015 | protocol/runtime evidence generated | Stateless baseline vs asset/scene/feedback memory reuse on fixed keyframe |
| RECORDING-016 | strongest current demo signal | Repeated same-keyframe same-task I2V; baseline varied more, memory-backed outputs were more consistent |

## Historical Branch / Worktree Notes

- The old `origin/codex/narratocut-web-ui` branch was archived by tag and
  deleted after useful work was replayed.
- Completed Local Alpha 0.2 and 0.3 implementation worktrees were removed after
  verified integration.
- Future nontrivial work should use isolated `codex/*` worktrees with explicit
  write scopes unless the lane is intentionally controller/docs-only.

## Claim Boundaries

- Local Alpha 0.4 has structure and runtime evidence, not business validation.
- Memory reuse review currently proves traceability, not durable Memory runtime.
- Memory-advantage demos are provider/runtime evidence plus visual review
  material; they are not statistical proof or human product acceptance unless a
  separate acceptance lane records that review.