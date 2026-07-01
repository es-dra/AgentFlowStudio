# AFS Maintenance / Redundancy Next-Action Decision Packet - 2026-07-01

## 2026-07-01 耐久化登记补充

本文件和
`AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md`
已进入受限文档耐久化通道。当前授权只允许在验证为 green 时提交并推送这两个维护文档，使原本容易丢失的本地未跟踪报告进入 Git 记录；不授权 cleanup 执行、分支删除、worktree 删除、PR、merge、provider/runtime/UI 更改、部署、公开发布、CompanyOS active-rule 晋升或任何高成本动作。

下文出现的 `local_untracked`、`not staged`、`not committed` 等表述，是本决策包生成时的来源状态；本通道的最终证据以 Git commit/push 记录和 worker closeout 为准。

中文摘要：本文件把原本未跟踪的 AFS redundancy / maintenance 状态报告转换为 CTO / Owner 可执行的下一步决策包。它只汇总当前耐久性、分流选项、授权边界和默认建议；不执行 cleanup、不删除 branch/worktree、不 reset/clean、不 push/PR/merge，也不打开 provider、image、video、LLM、ASR、external download 或 high-cost gate。

## 中文决策摘要

本包的核心判断是：维护冗余问题已经可见，但还没有形成足够耐久的仓库记录。当前文件存在于本地目录中，却仍然是未跟踪文件；它能帮助董事长、技术负责人和项目 Owner 判断下一步，但不能等同于已经提交、已经评审或已经进入长期任务账本。只要它没有被提交或被明确登记到任务跟踪面，未来清理工作区、切换上下文或重新派发线程时就可能漏掉它。因此，本包首先解决“下一步该由谁授权、授权什么、不授权什么”的问题，而不是直接解决清理问题。

当前可选路线有四条。第一条是把本维护包作为耐久文档提交，让后续工作可以从版本记录中稳定找到它；这需要 Owner 或 CTO 认可提交范围。第二条是暂时不提交，但由 CEO 或 CTO 在管理登记中保留可见状态；这不会改变仓库，但耐久性最弱。第三条是把结论转成有限的待办或任务跟踪项，只记录负责人、范围、验证门和非声明边界，不执行清理。第四条是以后另开一个有边界的清理 lane，从本包和冗余审计账本出发，但必须在 Owner 明确批准后才能进行删除、归档、推送、合并或迁移。

本包建议的默认动作是先走第三条：把维护结论转成非破坏性的任务登记，同时向 Owner 或 CTO 请求是否选择第一条并把本包提交为耐久文档。这样既能避免未跟踪报告继续漂浮，也不会把维护清理混入当前产品实现或集成。真正的清理执行、分支删除、工作树归档、维护分支推送、维护 PR、维护合并、历史路径隔离、旧测试拆分和 provider/video 表面治理，都必须等待 Owner 明确授权。

本包明确不声称产品已完成、不声称清理已执行、不声称维护分支可自动合并、不声称 Runtime 或部署健康、不声称 provider smoke、不声称生成媒体质量、不声称人工创意验收、不声称商业验证、不声称法律或公开发布判断，也不把任何经验晋升为 CompanyOS 或 COS 的 active rule。它只提供一个可操作的决策边界：哪些事情现在可以记录，哪些事情需要 Owner 批准，哪些事情应该继续延期，哪些事情应该拆成后续独立 lane。

当前产品阻塞判断是：维护队列不是产品 blocker。主工作区当前没有 tracked diff；受保护的演示文档目录仍然是本地未跟踪状态，不能触碰；另一个分支和工作树整合决策包也处于未跟踪状态，应视为并行本地材料而不是本包的写入范围。产品工作可以继续，但每个产品 lane 必须自己通过启动扫描、脏边界检查、验证命令和非声明边界，不能借用本维护包来扩大权限。

## Decision Packet Contract

| Field | Value |
|---|---|
| status | `durability_registration_lane_active` |
| artifact_class | `afs_maintenance_next_action_decision_packet` |
| workspace_root | `D:\Projects\AgentFlowStudio` |
| decision packet worker | current delegated Codex worker |
| source CEO thread | `019f1e02-a8b2-7c93-a931-bfd1cc2c254a` |
| write scope | this existing report file only |
| provider gate | closed; no provider/image/video/high-cost/external download |
| cleanup authority | not granted |
| destructive authority | not granted |
| durability state | source packet was local-only; current scoped lane may commit/push this file and the branch/worktree packet after green verification |

## Current Durability State

This section records the packet source state before the durability registration
lane. See the Git history and worker closeout for the final committed state.

| Artifact | Current state | Decision meaning |
|---|---|---|
| `docs\maintenance\AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md` | present on disk, untracked by Git, not staged, not committed, not pushed | visible locally but not fully durable; it can be lost in workspace cleanup or missed by future Git-based review |
| `docs\demo-docs-20260629\` | untracked protected local state | explicit do-not-touch; not part of this packet and not a cleanup target |
| Current packet edit | same file, still local-only unless later committed | converts report into an actionable decision packet but does not itself create Git durability |

Current verification snapshot as of this packet:

```text
branch: master
head: 56c3f700e9dc
upstream: origin/master
tracked diff: none
untracked: docs\maintenance\AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
parallel untracked maintenance packet: docs\maintenance\AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md
protected untracked: docs\demo-docs-20260629\
```

The older branch snapshot later in this file is retained as historical context where useful, but the current live checkout snapshot above is the decision baseline for this packet.

## Decision Options

| Option | Action | Owner / CTO authorization needed | Result | Risk / residual |
|---|---|---|---|---|
| A. Commit maintenance report as durable doc | Review this file, optionally rename it later, then commit it on an approved branch | Owner or CTO approval to make the maintenance packet durable; commit message and branch scope should be explicit | Best durability; future workers can find the packet through Git and handoff indexes | Creates a durable maintenance governance record; still no cleanup authorization |
| B. Defer but keep visible | Leave the file untracked and mention it in CEO / CTO register or next handoff | CEO / CTO can do this as non-destructive reporting; Owner not required unless it becomes a commit/push/delete action | Lowest immediate disruption; no Git history change | Weak durability; future cleanup, worktree pruning, or context loss can hide it |
| C. Convert findings to backlog / task tracker | Add bounded backlog entries without executing cleanup | CEO / CTO can authorize non-destructive backlog update; Owner approval needed only if the update commits, pushes, or changes cleanup authority | Turns the audit into actionable work items with owners and gates | Does not preserve the full report unless the file is also committed or referenced |
| D. Route a bounded cleanup lane later | Start a fresh cleanup worker from this packet and the rebuild audit | Owner approval required before cleanup execution, branch/worktree archive/delete, maintenance push/PR/merge, or legacy quarantine/delete | Cleanest route for actual debt reduction | Must stay separate from product integration and requires fresh verification before any edit/delete |

Recommendation: choose Option A if CTO/Owner wants the current maintenance state to be durable now. If not, choose Option C as the minimum non-destructive operational step, then keep Option D pending until Owner explicitly authorizes cleanup execution.

## Authorization Boundary

Requires Owner approval before execution:

- Deleting, pruning, archiving, or otherwise removing any branch or worktree.
- Pushing, opening a PR, merging, or publishing a maintenance-only branch.
- Quarantining, deleting, or migrating legacy code, docs, tests, examples, provider/video surfaces, or runtime paths.
- Turning maintenance classifications into cleanup execution.
- Promoting any AFS/COS lesson into Company OS active rules.

Can proceed under CEO / CTO authority as non-destructive reporting or backlog control:

- Keep this packet visible in the CEO thread / managed register.
- Add a backlog or task-tracker item that records owner, scope, gates, and non-claims.
- Request Owner decision on commit-vs-defer and cleanup-lane timing.
- Prepare a fresh bounded cleanup prompt without running cleanup.
- Keep product lanes moving when their own verification and dirty-boundary checks are green.

## 董事长可见结论

当前维护队列的关键结论是：冗余维护问题已经从“线程里有 closeout、但队列不可见”的状态，恢复为一个可以被 Owner、CTO 和 CEO 注册、分流、延期或授权执行的明确队列。旧的冲突分支不再是当前产品工作必须修补的对象；它的有效信息已经被新的干净维护账本承接。新的维护账本本身只是证据和分类，不是删除授权，也不是合并授权。

当前产品主线不需要等待维护清理。当前主 checkout 是 `master` 且没有 tracked diff；T52 分支已有独立 worktree 且当前 clean；另有 T53 worktree 处于活跃 dirty 状态，但它不是本维护包的写入范围。维护队列只要求保持可见，不要求阻塞产品推进。

需要 Owner 决策的是清理执行层，而不是报告层。具体包括：是否审阅并推送新的冗余维护账本分支，是否归档或删除旧分支和历史 worktree，是否启动 legacy quarantine、文档迁移、测试拆分或 provider/video 表面治理。没有 Owner 授权前，本报告只建议保留分类、继续延期、避免在产品集成窗口中做破坏性清理。

默认建议是先让 CEO / CTO 把本文件登记为当前维护决策包，再由 Owner 在“提交耐久化 / 继续延期 / 转 backlog / 后续清理 lane”之间选择。除非 Owner 现在希望处理 cleanup，否则冗余维护分支保持 `archive_deferred` 即可。这样既不丢失维护债，也不让维护债伪装成产品 blocker。

执行边界补充：本报告面向决策可见性，不替代代码评审、集成评审或清理授权。任何后续动作都应先明确“只记录、只评估、还是执行清理”，并把验证命令、回滚边界、非目标和 Owner 决策点写清楚。这样可以避免把维护账本误当作自动执行命令。

## Current Maintenance Status

| Queue item | Current state | Product blocker | Next owner |
|---|---|---|---|
| AFS redundancy rebuild | `archive_deferred_not_product_blocker`; fresh rebuild exists at `eb16cc3e` | No | Owner / CTO for review, push, archive, or continued defer |
| Old redundancy lane | `superseded`; old branch remains local, old conflict worktree path is absent | No | Owner only if deletion/archive is desired |
| Current master checkout | `master` at `56c3f700e9dc`, aligned with `origin/master`; no tracked diff | No | CEO / CTO for decision registration |
| Current T52 shared-object fixture | isolated worktree on `codex/afs-t52-shared-object-evidence-fixture-20260701`; current status clean | No | CEO / CTO if further routing is needed |
| Current T53 worktree | isolated worktree on `codex/afs-t53-interactive-manga-branch-package-20260701`; dirty with intended T53 files | No maintenance blocker | T53 lane owner / CEO, separate from this packet |
| Maintenance debt classes | classified as keep, migrate, quarantine candidate, delete-candidate after proof, or defer | No | Owner if cleanup execution is requested |

AFS product work can continue in parallel. The maintenance queue is a governance and cleanup-authorization queue, not a current product blocker.

## Startup / Dirty Boundary Scan

Current primary checkout:

```text
branch: master
head: 56c3f700e9dc7ead18950c990b8b2c875c5f8800
upstream: origin/master
```

Observed dirty boundary before this packet edit:

| Class | Paths |
|---|---|
| tracked primary checkout diff | none |
| parallel untracked maintenance packet | `docs/maintenance/AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md`; observed during verification and left untouched |
| do-not-touch local state | `docs/demo-docs-20260629/` |
| current decision packet write | `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md` |

`docs/demo-docs-20260629/` is still untracked local state and has no tracked diff. This report did not edit it.

## Exact Branch / Worktree Status

| Item | Exact state | Disposition |
|---|---|---|
| Primary checkout | `D:\Projects\AgentFlowStudio`, branch `master`, head `56c3f700e9dc`, upstream `origin/master` | keep clean except this untracked decision packet and protected demo docs |
| Continuation branch | `codex/afs-post-main-loop-e2e-continuation-20260630`, head `9ef456a980e9` and present on origin | historical/current product branch context; no action by this packet |
| Fresh redundancy rebuild worktree | `C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701`, branch `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`, head `eb16cc3e`, clean, `[ahead 1, behind 3]` against continuation upstream | owner_review_pending / archive_deferred |
| Fresh redundancy rebuild diff | `DEVLOG.md` plus `docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md`, 90 insertions | safe maintenance evidence; not product code |
| Old redundancy branch | `codex/afs-redundancy-maintenance-ledger-20260701`, head `bb71d16a`, `[ahead 2, behind 4]` | superseded; delete/archive only after Owner approval |
| Old redundancy worktree path | `C:\Users\chenzy\.codex\worktrees\7dd1\AgentFlowStudio` | path no longer exists and is not in `git worktree list`; no cleanup executed |
| T52 worktree | `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701`, branch `codex/afs-t52-shared-object-evidence-fixture-20260701`, head `56c3f700e9dc`, status clean | separate from maintenance |
| T53 worktree | `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t53-interactive-manga-branch-package-20260701`, branch `codex/afs-t53-interactive-manga-branch-package-20260701`, head `56c3f700e9dc`, dirty with T53 files | separate active product lane; do not touch from this packet |
| Historical T46 branch | `codex/afs-goal-mode-main-loop-e2e-20260630`, head `72c698ac`, also on origin | integrated historical branch; cleanup can defer |
| Historical threshold branch | `codex/afs-goal-mode-threshold-gate-20260630`, head `3f65c0a1`, also on origin | integrated historical branch; cleanup can defer |

## Exact Thread / Register Entries

| Thread | Role | Current report status | Close / archive condition |
|---|---|---|---|
| `019f1e02-a8b2-7c93-a931-bfd1cc2c254a` | CEO v2 / delivery dispatcher | active register owner | consume this report and route Owner decisions |
| `019f1d81-6546-77b1-a130-6133d713e848` | AFS R1 redundancy disposition | `maintenance_state_closed_or_owner_review_pending`; upward feedback sent | Owner reviews fresh rebuild and decides push/archive/defer |
| `019f1e16-de37-76f3-8c3f-d99e550eef52` | this AFS maintenance report worker | `reported_result` after this packet | CEO registers latest artifact, then Owner/CTO decides cleanup route |
| `019f1d87-63da-7313-8dd9-606bbfe77dfe` | original T51 worker | historical registered product lane context | recheck latest lane closeout before routing |
| `019f1e0e-0c8d-7b40-9b35-31e7cd653590` | T51 integration evaluator | historical evaluator context; prior disposition was `commit_ready_provider_closed` | recheck latest lane closeout before routing |
| `019f1e16-b3c6-72b3-b946-6686afc1900e` | T51 normal product integration | historical product lane context, not maintenance cleanup | no maintenance action from this packet |
| `019f1e0e-1e95-7641-9542-938fd7ab4da0` | T52 shared-object fixture worker | current local worktree is clean at `56c3f700e9dc` | separate product routing if needed |

## Already Superseded Or Closed

- The old conflicted redundancy lane is superseded by the clean rebuild branch at `eb16cc3e`.
- The old conflict worktree path from the rebuild ledger is absent locally and not listed by Git worktrees.
- The fresh rebuild is limited to maintenance evidence and is not required before product work proceeds.
- T46/T47/T48/T49/T50 evidence remains product-history context; none of those require maintenance cleanup before current product lanes continue.

## Safe To Keep Deferred

- Fresh redundancy rebuild push/archive can stay `archive_deferred` until Owner wants a maintenance branch reviewed.
- Historical integrated branches can remain undeleted; deleting or pruning them is housekeeping, not a product blocker.
- `agentflow/memory`, legacy SOP/distribution surfaces, `runtime_v02`, oversized tests, and large handoff/tracker files should remain classified debt until a dedicated cleanup lane is authorized.
- Provider/video surfaces and low-confidence secret-like warning classes should stay deferred to separate read-only classification before any edit.
- `docs/demo-docs-20260629/` remains explicitly do-not-touch.

## Requires Owner Approval Before Execution

- Deleting or archiving any branch or worktree.
- Pushing, opening PRs, or merging maintenance-only branches such as `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`.
- Quarantining or deleting legacy code, docs, tests, examples, provider/video surfaces, or old runtime paths.
- Turning a maintenance classification into cleanup execution.
- Promoting any AFS/COS lesson into Company OS active rules.

Normal product integration is different: product lanes can continue through normal scoped integration if their own verification, dirty-boundary safety, and claim boundaries are green.

## Product Blocker Status

`no_current_product_blocker_from_maintenance_queue`

The maintenance/redundancy state is visible and actionable, but it does not block current product work. The only active risks are governance risks: owner decision debt, stale branch cleanup debt, weak durability while this packet is untracked, and the need to avoid mixing maintenance cleanup with product integration.

## Recommended Default Action

1. Default to Option C now: register a bounded backlog / task-tracker item from this packet without cleanup execution.
2. Ask Owner / CTO whether to choose Option A and commit this packet as the durable maintenance doc.
3. Keep the AFS redundancy rebuild in `archive_deferred` unless Owner wants a maintenance review branch pushed or archived now.
4. If Owner wants cleanup execution, start a fresh bounded cleanup lane from this packet plus `AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md`; do not resume the old stale branch.
5. Keep product implementation lanes separate from maintenance cleanup.

## Verification Notes

Read-only checks performed before writing this report:

```text
git status --short --branch
git worktree list --porcelain
git branch --all --verbose --no-abbrev
git show --stat --oneline --decorate eb16cc3e
git diff --name-status origin/codex/afs-post-main-loop-e2e-continuation-20260630...codex/afs-redundancy-maintenance-ledger-rebuild-20260701
git -C C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701 status --short --branch
git -C C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t52-shared-object-evidence-fixture-20260701 status --short --branch
git status --porcelain=v1 --untracked-files=all docs/demo-docs-20260629
git ls-files docs/demo-docs-20260629
git diff --name-status -- docs/demo-docs-20260629
```

Post-write verification must include `git diff --check`, a trailing-whitespace scan for this report, and a scope scan confirming only this report was added by this lane.
