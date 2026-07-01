# AFS R2 Redundancy Branch / Worktree Disposition Packet - 2026-07-01

## Contract

| Field | Value |
|---|---|
| artifact_class | `afs_r2_redundancy_branch_worktree_disposition_packet` |
| workspace_root | `D:\Projects\AgentFlowStudio` |
| source_ceo_thread | `019f1e02-a8b2-7c93-a931-bfd1cc2c254a` |
| authority | CTO-authorized bounded non-destructive disposition lane |
| scope | classify remaining redundancy branch/worktree residue only |
| write_scope | this packet only |
| cleanup_authority | not granted |
| destructive_authority | not granted |
| provider_runtime_ui_authority | not granted |

This packet updates the branch/worktree state after the maintenance hygiene
packets became durable at `d2e383a63861e09657c1f2d67162dfc0002460eb`.

## Current Baseline

`git fetch origin` completed without pruning. Live baseline after fetch:

```text
master:        2d72a484fd7db0524a5738efc3fa1e4d0072a834
origin/master: 2d72a484fd7db0524a5738efc3fa1e4d0072a834
durable maintenance docs commit: d2e383a63861e09657c1f2d67162dfc0002460eb
```

Primary checkout dirty boundary:

```text
tracked diff: none before this packet
untracked do-not-touch local state:
  docs/demo-docs-20260629/AFS-DEMO-DOCS-CHINESE-20260629.md
  docs/demo-docs-20260629/AFS-DEMO-PACK-20260629.md
  docs/demo-docs-20260629/DEMO-1-MANGA-WORKBENCH-DIFFERENTIATION.md
  docs/demo-docs-20260629/DEMO-2-CORE-TECH-MEMORY-AGENT-FRAMEWORK.md
  docs/demo-docs-20260629/DEMO-TECH-EXECUTION-CHECKLIST.md
```

Remote heads from `git ls-remote --heads origin`:

```text
2d72a484fd7db0524a5738efc3fa1e4d0072a834 refs/heads/master
2d72a484fd7db0524a5738efc3fa1e4d0072a834 refs/heads/codex/afs-t53-interactive-manga-branch-package-20260701
```

No true remote heads exist for either redundancy branch.

## Exact Subject State

| Subject | Current state | Work classification | Recommended next action |
|---|---|---|---|
| `codex/afs-redundancy-maintenance-ledger-20260701` | local branch at `bb71d16a16f948fb84e4caff5727d51aba5b8c18`; configured upstream `origin/codex/afs-post-main-loop-e2e-continuation-20260630` is `[gone]`; no worktree | superseded; contains old source-composition ledger plus merge residue; not an ancestor of `origin/master`; no unrecoverable work found | Keep deferred until Owner authorizes local branch deletion/archive. Do not merge or push. Use rebuild branch or durable docs for future maintenance routing. |
| `codex/afs-redundancy-maintenance-ledger-rebuild-20260701` | local branch at `eb16cc3ecf7f6e72fa6d1bc7cacf478cf024e588`; configured upstream `origin/codex/afs-post-main-loop-e2e-continuation-20260630` is `[gone]`; attached worktree exists | unique maintenance evidence not integrated into `origin/master`: `DEVLOG.md` plus `docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md`; disposition boundary already summarized in durable docs | Keep hold. Owner must decide whether to preserve/commit that source-composition ledger, discard it as superseded, or keep the branch/worktree deferred. Do not delete until that decision is explicit. |
| `C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701` | worktree exists; branch `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`; head `eb16cc3ecf7f6e72fa6d1bc7cacf478cf024e588`; status clean; upstream `[gone]` | clean owner-decision worktree carrying the unique rebuild ledger | Safe to leave in place. Future destructive cleanup can remove it only after the Owner decides the unique ledger is preserved elsewhere or intentionally discarded. |
| upstream-gone configuration | both redundancy branches still track deleted remote branch `origin/codex/afs-post-main-loop-e2e-continuation-20260630`; remote branch is absent from `git ls-remote --heads origin` | configuration residue caused by prior branch hygiene; not source work | Future cleanup lane may unset upstreams or delete branches after clean-status and Owner-decision checks. No remote action is needed for these redundancy branches because no remote heads exist. |

## Relation To Durable Maintenance Docs

`d2e383a63861e09657c1f2d67162dfc0002460eb` added:

```text
docs/maintenance/AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md
docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
```

Those durable docs already register:

- the old redundancy branch as superseded;
- the rebuild branch at `eb16cc3e` as owner-review / archive-deferred;
- the rebuild worktree as clean;
- `docs/demo-docs-20260629/` as do-not-touch;
- cleanup execution as unauthorized without Owner approval.

The full `AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md` file is not on
`origin/master`. It remains unique to the redundancy branches. The old branch
has an older version; the rebuild branch has the cleaner replacement version.
That unique ledger is maintenance evidence only, not product code and not a
product blocker.

## Future Destructive Cleanup Gate

A future destructive cleanup lane can be authorized safely only if all of these
checks pass immediately before execution:

1. Run `git fetch origin` and record current heads; do not rely on this packet
   if branch heads changed.
2. Confirm `master` and `origin/master` still match the intended baseline or
   explicitly record the newer baseline.
3. Confirm `docs/demo-docs-20260629/` remains do-not-touch and is not staged,
   moved, deleted, or used as cleanup evidence.
4. Confirm the rebuild worktree status is clean.
5. Decide the unique source-composition ledger first:
   - preserve it in a durable doc/commit, or
   - explicitly discard it as superseded maintenance evidence.
6. Confirm no active thread or worktree depends on either redundancy branch.
7. Only then delete/archive local branches or remove the rebuild worktree.

Remote cleanup is not needed for the two redundancy branches because no remote
heads currently exist for them.

## Non-Claims

This packet makes no source/provider/runtime/UI change and no provider,
high-cost, deploy, runtime-health, generated-media-quality, human acceptance,
business, public-release, legal, CompanyOS, durable-memory-promotion, or
COS-active-rule claim.

## Verification Evidence

Commands run in this lane:

```text
Get-Content C:\Users\chenzy\.codex\skills\project-development-workflow\SKILL.md
Get-Content AGENTS.md docs\company_operating_model.md TASK_TRACKER.md DEVLOG.md docs\handoff\INDEX.md
Get-Content docs\maintenance\AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
Get-Content docs\maintenance\AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md
git fetch origin
git status --short --branch --untracked-files=all
git remote -v
git worktree list --porcelain
git branch --all --verbose --no-abbrev
git ls-remote --heads origin
git config --get-regexp ^branch\.codex/afs-redundancy-maintenance-ledger.*
git for-each-ref --format=%(refname:short)|%(objectname)|%(upstream:short)|%(upstream:track)
git rev-list --left-right --count origin/master...<redundancy-branch>
git log --oneline origin/master..<redundancy-branch>
git diff --name-status origin/master...<redundancy-branch>
git -C C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701 status --short --branch --untracked-files=all
Test-Path C:\Users\chenzy\.codex\worktrees\7dd1\AgentFlowStudio
Test-Path C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701
git status --porcelain=v1 --untracked-files=all -- docs/demo-docs-20260629 docs/maintenance
```

Observed residuals:

- `docs/demo-docs-20260629/` remains untracked do-not-touch local state.
- Old conflict worktree path `C:\Users\chenzy\.codex\worktrees\7dd1\AgentFlowStudio` is absent.
- T52 worktree path is absent.
- T53 worktree is clean and aligned with its remote; it is outside this cleanup scope.
