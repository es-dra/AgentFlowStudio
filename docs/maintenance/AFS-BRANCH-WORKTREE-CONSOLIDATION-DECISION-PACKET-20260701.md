# AFS Branch / Worktree Consolidation Decision Packet - 2026-07-01

## 中文耐久化摘要

本文件把当前 AFS branch / worktree hygiene 状态整理成可决策、可登记、可延后的维护包。它只说明哪些分支、远端分支和 worktree 应保持 active、keep_hold、merged_archive_candidate、remote_delete_candidate、local_delete_candidate、owner_decision_required 或 do_not_touch；不执行删除、归档、push、merge、PR、reset、clean、provider、runtime、deploy、UI 或高成本动作。

当前耐久化通道的决定是：在验证为 green 时，仅把本文件和
`AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`
作为维护文档提交并推送，使原本 loose/untracked 的分支卫生判断进入 Git 记录。真正的清理执行、旧分支删除、worktree 删除、远端分支删除、维护分支推送或合并，仍然必须等待 Owner 明确授权和新的边界扫描。

非声明边界保持不变：本文件不声明产品完成、Runtime 健康、provider smoke、生成媒体质量、人工创意验收、商业验证、公开发布、法律判断、CompanyOS 结论或 COS active-rule 晋升。产品工作不应被本维护队列阻塞；维护队列只要求状态可见、责任可分流、后续决策可恢复。

## 中文分流细则

- `keep_active` 表示仍在服务当前产品或当前 worker，后续维护人员只能观察和登记，不能借分支卫生名义修改、删除或移动。
- `keep_hold` 表示有维护价值但缺少 Owner 最终决定，默认保持可见并延后处理，直到有人明确选择 push、archive、delete、defer 或 rebuild。
- `merged_archive_candidate` 表示分支内容已经进入 `master` 和 `origin/master`，可以作为后续归档候选，但执行前仍要重新做 ancestry、dirty boundary 和 worker 占用检查。
- `remote_delete_candidate` 只代表远端分支具备删除候选资格，不代表本文件已经授权删除。远端删除会影响其他线程和人工回滚路径，必须单独获得 Owner 决策。
- `local_delete_candidate` 只代表本地分支或 worktree 可能清理。真正执行前必须确认没有 dirty 文件、没有 active worker 依赖、没有未登记成果，并且不得触碰受保护的 demo docs。
- `owner_decision_required` 是治理队列，不是产品 blocker。它要求 Owner 或 CTO 决定维护分支是否推送、合并、归档、删除或继续延后。
- `do_not_touch` 是硬边界。`docs/demo-docs-20260629/` 和活跃 T53 worktree 只能保留和报告，不能 stage、clean、delete、rename、archive 或拿来扩大本通道权限。

本通道的最小成功标准是把上述判断从 loose local artifact 变成可被 Git 找到的维护文档。后续如需真正减少分支数量或 worktree 数量，应另开 cleanup lane，重新声明写入范围、删除权限、验证命令、回滚边界和 close condition。

## Report Contract

| Field | Value |
|---|---|
| artifact_class | `afs_branch_worktree_consolidation_decision_packet` |
| workspace_root | `D:\Projects\AgentFlowStudio` |
| source CEO thread | `019f1e02-a8b2-7c93-a931-bfd1cc2c254a` |
| worker scope | read-only branch/worktree audit plus this packet |
| 2026-07-01 durability lane | scoped documentation registration only; no cleanup execution |
| cleanup authority | not granted |
| provider/tool gate | no provider, deploy, runtime, high-cost, or external-download action |

## Current Scan Summary

Primary checkout:

```text
D:\Projects\AgentFlowStudio
branch: master
HEAD: 56c3f700e9dc7ead18950c990b8b2c875c5f8800
upstream: origin/master
status: aligned with origin/master
```

Dirty boundary in the primary checkout:

```text
?? docs/demo-docs-20260629/
?? docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
?? docs/maintenance/AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md
```

`docs/demo-docs-20260629/` is known do-not-touch local state. The prior
maintenance report was present before this packet and was read as evidence, not
modified.

## Exact Local Branches

| Local branch | Head | Upstream / remote tracking | Worktree | Merge state |
|---|---:|---|---|---|
| `master` | `56c3f700` | `origin/master` at same head | `D:\Projects\AgentFlowStudio` | current integration baseline |
| `codex/afs-goal-mode-main-loop-e2e-20260630` | `72c698ac` | remote exists at same head | none | merged to `master` and `origin/master`; `master...branch = 10 / 0` |
| `codex/afs-goal-mode-threshold-gate-20260630` | `3f65c0a1` | remote exists at same head | none | merged to `master` and `origin/master`; `master...branch = 16 / 0` |
| `codex/afs-post-main-loop-e2e-continuation-20260630` | `9ef456a9` | remote exists at same head | none | merged to `master` and `origin/master`; `master...branch = 1 / 0` |
| `codex/afs-t52-shared-object-evidence-fixture-20260701` | `56c3f700` | remote exists at same head | `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701` | same as `master`; clean |
| `codex/afs-t53-interactive-manga-branch-package-20260701` | `56c3f700` | no remote branch | `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701` | active dirty product lane |
| `codex/afs-redundancy-maintenance-ledger-20260701` | `bb71d16a` | tracks `origin/codex/afs-post-main-loop-e2e-continuation-20260630` | none | unmerged; `master...branch = 5 / 2` |
| `codex/afs-redundancy-maintenance-ledger-rebuild-20260701` | `eb16cc3e` | tracks `origin/codex/afs-post-main-loop-e2e-continuation-20260630` | `C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701` | unmerged; `master...branch = 4 / 1`; worktree clean |

Left/right counts are from `git rev-list --left-right --count
master...<branch>` and mean `master-only / branch-only`.

## Exact Remote Branches

True remote heads from `git ls-remote --heads origin`:

| Remote branch | Head | State |
|---|---:|---|
| `origin/master` | `56c3f700` | current baseline |
| `origin/codex/afs-goal-mode-main-loop-e2e-20260630` | `72c698ac` | merged to `origin/master` |
| `origin/codex/afs-goal-mode-threshold-gate-20260630` | `3f65c0a1` | merged to `origin/master` |
| `origin/codex/afs-post-main-loop-e2e-continuation-20260630` | `9ef456a9` | merged to `origin/master` |
| `origin/codex/afs-t52-shared-object-evidence-fixture-20260701` | `56c3f700` | same as `origin/master` |

No true remote head was found for T53 or either redundancy maintenance branch.

## Exact Worktrees

| Worktree path | Branch | Head | Dirty state | Category |
|---|---|---:|---|---|
| `D:\Projects\AgentFlowStudio` | `master` | `56c3f700` | only known untracked local docs plus this packet | `keep_active` |
| `C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701` | `codex/afs-redundancy-maintenance-ledger-rebuild-20260701` | `eb16cc3e` | clean | `owner_decision_required` |
| `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701` | `codex/afs-t52-shared-object-evidence-fixture-20260701` | `56c3f700` | clean | `local_delete_candidate` after authorization |
| `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701` | `codex/afs-t53-interactive-manga-branch-package-20260701` | `56c3f700` plus dirty files | dirty active product lane | `keep_active` |

T53 dirty files:

```text
M DEVLOG.md
M TASK_TRACKER.md
M agentflow/algorithms/__init__.py
M docs/handoff/INDEX.md
?? agentflow/algorithms/interactive_manga_branch_package/__init__.py
?? docs/handoff/AFS-T53-INTERACTIVE-MANGA-BRANCH-PACKAGE-CONTRACT-20260701.md
?? tests/fixtures/interactive_manga_branch_package/branch_package_fixture.json
?? tests/test_interactive_manga_branch_package_contract.py
```

## Decision Categories

### keep_active

- `master` / `D:\Projects\AgentFlowStudio`: current integration baseline,
  aligned with `origin/master` at `56c3f700`.
- `codex/afs-t53-interactive-manga-branch-package-20260701` /
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701`:
  active product worker lane, local-only branch, dirty with T53 implementation
  files. Do not cleanup under branch hygiene.

### keep_hold

- `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`: prior
  untracked maintenance report present before this packet. Keep as evidence
  unless Owner decides how to stage, supersede, archive, or delete it.
- `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`: keep on hold
  until Owner decides whether this clean rebuild should be pushed, merged,
  archived, or deleted.
- `codex/afs-redundancy-maintenance-ledger-20260701`: keep on hold until Owner
  decides whether the superseded old branch should be deleted or retained for
  forensic comparison.

### merged_archive_candidate

These local/remote product branches are already merged to `master` and
`origin/master`, so they can be archived after explicit authorization and one
final ancestry check:

- `codex/afs-goal-mode-main-loop-e2e-20260630`
- `codex/afs-goal-mode-threshold-gate-20260630`
- `codex/afs-post-main-loop-e2e-continuation-20260630`
- `codex/afs-t52-shared-object-evidence-fixture-20260701`

### remote_delete_candidate

These remote branches remain on GitHub and are merged to `origin/master`; they
are remote-delete candidates only after Owner authorization:

- `origin/codex/afs-goal-mode-main-loop-e2e-20260630`
- `origin/codex/afs-goal-mode-threshold-gate-20260630`
- `origin/codex/afs-post-main-loop-e2e-continuation-20260630`
- `origin/codex/afs-t52-shared-object-evidence-fixture-20260701`

No remote-delete action was taken.

### local_delete_candidate

These local branches and worktrees are local-delete candidates only after Owner
authorization and final clean-status checks:

- `codex/afs-goal-mode-main-loop-e2e-20260630`
- `codex/afs-goal-mode-threshold-gate-20260630`
- `codex/afs-post-main-loop-e2e-continuation-20260630`
- `codex/afs-t52-shared-object-evidence-fixture-20260701`
- `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701`

The T52 branch is currently attached to a clean worktree, so local cleanup would
need to remove the worktree before deleting the branch. No local-delete action
was taken.

### owner_decision_required

- Decide whether to push, merge, archive, continue deferring, or delete
  `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`.
- Decide whether to delete/archive or keep
  `codex/afs-redundancy-maintenance-ledger-20260701`, which is unmerged and
  appears superseded by the rebuild lane.
- Decide whether to delete/archive the four merged remote product branches.
- Decide whether to delete local merged product branches/worktrees after
  confirming no worker still needs them.
- Decide how to handle the pre-existing untracked maintenance report
  `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`.

### do_not_touch

- `docs/demo-docs-20260629/`: known untracked local state; do not stage, edit,
  delete, clean, or use as cleanup evidence.
- `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701`:
  active dirty T53 worker lane; do not alter from consolidation cleanup.

## Product Blocker Verdict

`no_current_product_blocker_from_branch_or_worktree_consolidation`

The only active product lane observed is T53. It is local-only and dirty, but
that is expected active-worker state, not a consolidation blocker. The
unmerged redundancy branches are governance cleanup decisions, not product
blockers.

## Recommended Next Default Action

Keep product work moving on T53. In parallel, route an Owner decision packet for
branch hygiene:

1. Authorize deletion/archive of the four merged remote product branches, or
   defer.
2. Authorize local cleanup of merged local product branches and the clean T52
   worktree, or defer.
3. Decide the two maintenance branches separately: rebuild branch review/push
   versus old branch archive/delete.

Do not mix this cleanup with the active T53 product worktree.

## Verification Commands And Results

```text
Get-Content project-development-workflow/SKILL.md
result: read local fallback skill

Get-Content AGENTS.md, docs/company_operating_model.md, TASK_TRACKER.md,
DEVLOG.md, docs/handoff/INDEX.md,
docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
result: startup docs read; maintenance status report present

git status --short --branch --untracked-files=all
result: master aligned with origin/master; untracked demo docs, prior
maintenance report, and this packet

git remote -v
result: origin=https://github.com/es-dra/AgentFlowStudio.git

git worktree list --porcelain
result: four worktrees found: master, redundancy rebuild, T52, T53

git branch --all --verbose --no-abbrev
result: local and remote branch heads listed above

git ls-remote --heads origin
result: five true remote heads listed above

git -C <redundancy rebuild worktree> status --short --branch --untracked-files=all
result: clean; ahead 1, behind 3 vs continuation upstream

git -C <T52 worktree> status --short --branch --untracked-files=all
result: clean; aligned with origin T52 branch

git -C <T53 worktree> status --short --branch --untracked-files=all
result: dirty active T53 files listed above

git merge-base --is-ancestor <branch> master
git merge-base --is-ancestor <branch> origin/master
git rev-list --left-right --count master...<branch>
result: historical product branches and T52 are merged; redundancy branches
are not merged
```

## Non-Claims

This packet makes no provider, high-cost, deploy, runtime-health, human
acceptance, business, public-release, legal, CompanyOS, COS-active-rule, or
generated-media quality claims.
