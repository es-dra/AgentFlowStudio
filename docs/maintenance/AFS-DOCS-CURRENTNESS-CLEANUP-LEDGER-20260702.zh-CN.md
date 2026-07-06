# AFS 文档当前性清理账本 - 2026-07-02

本文记录 C1 与 C2 的实质文档瘦身动作。C1 把散落在 `docs/handoff/`
和 `docs/maintenance/` 中、没有当前索引入口且没有外部引用的历史说明文档移出活跃目录；
C2 继续删除这些低价值 archive 副本，只保留摘要、清单和 git 恢复路径。本文不触碰
provider、server、runtime evidence、本地 demo docs、私有素材、客户/成本信息或
CompanyOS active rule。

## 判定方法

| 检查 | 结果 |
|---|---|
| C1 工作分支 | `codex/afs-c1-docs-cli-micro-cleanup-20260702`，已合入当前 `origin/master` 的 T54 主线 |
| C2 工作分支 | `codex/afs-docs-low-value-deletion-cleanup-20260702`，从 T56 / `origin/master` 提交 `61b5b8b9d98577df1d2b7c0c273f32869ffb8518` 开始 |
| 受保护状态 | `docs/demo-docs-20260629/` 保持 untracked、未读取为清理输入、未移动、未删除 |
| Handoff 候选 | 不在 `docs/handoff/INDEX.md`，且 `rg --fixed-strings <filename>` 除自身外无引用 |
| Maintenance 候选 | 不在当前 handoff index，且除自身外无引用 |
| 删除策略 | C1 先 `git mv` 到 archive；C2 删除 archive 副本，恢复路径改为 git 历史 |

## 分类表

| 分类 | 文件或规则 | 处理 |
|---|---|---|
| keep_current | `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md`, `BACKLOG.md`, `DEVLOG.md`, `docs/handoff/INDEX.md`, T46-T54 release-gate handoffs, Runtime/Studio/provider-gated current handoffs, `docs/maintenance/AFS-FULL-MAINTENANCE-QUEUE-AUDIT-NEXT-ACTION-20260702.md` | 保留为当前入口或当前证据 |
| consolidate | `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`, 本账本, `docs/handoff/INDEX.md` 的维护证据入口 | 用摘要和索引承接历史说明，不再把每个旧 handoff 当作任务入口 |
| archive | 下表 20 个文件 | C1 从活跃目录移动到 `docs/archive/handoff/` 或 `docs/archive/maintenance/` |
| delete_executed | 下表 20 个文件 | C2 从 live tree 删除常驻 archive 副本；摘要和恢复命令保留 |
| delete_candidate_deferred | 仍被 `TASK_TRACKER.md`、`DEVLOG.md` 或维护账本引用的旧 runbook/QA/Studio 文件；`repository_retention_review` 中剩余 `archive_or_delete_when_indexed` 项 | 后续必须先解除引用、更新索引、再跑维护审计 |
| do_not_touch | `docs/demo-docs-20260629/`, local configs, secrets, provider raw response, signed URL, generated/private media bytes, ignored runtime evidence, active product worktree files | 未读取、未移动、未删除 |

## C1 已归档 / C2 已删除文件

### `docs/archive/handoff/`

| 原路径 | C2 删除安全性 |
|---|---|
| `docs/handoff/AFS-COMPANY-OS-FEEDBACK-CANDIDATE-20260614.md` | 候选反馈历史证据已由本账本和历史摘要承接；不得自动晋升为 active rule；无当前入口 |
| `docs/handoff/AFS-COMPANY-OS-FEEDBACK-CANDIDATE-20260618.md` | 同上，保留摘要即可；原文从 git 恢复 |
| `docs/handoff/AFS-D1-PROJECT-BOOK-NEXT-MAINLINE-DISPATCH-PACKET-20260701.md` | 已被 T51-T56 当前主线记录替代；不作为任务入口 |
| `docs/handoff/AFS-DIRECTOR-STAGE-V2-CONTRACT-20260623.md` | 旧 Director Stage 合同记录；当前 index 已从 Studio/Runtime 主线进入 |
| `docs/handoff/AFS-SOCIAL-SQUARE-MVP-20260623.md` | 旧 Social Square MVP 说明；当前本地 MVP 不从此入口恢复 |
| `docs/handoff/AFS-STUDIO-FRONTEND-BASELINE-20260617.md` | 旧前端基线说明，已被当前 Studio 架构和后续 handoff 覆盖 |
| `docs/handoff/AFS-STUDIO-FRONTEND-REFERENCE-20260617.md` | 旧前端参考说明；计划性内容低于常驻 archive 保留价值 |
| `docs/handoff/AFS-STUDIO-FRONTEND-WAVE-20260617.md` | 旧前端 wave 长文，已不作为当前入口 |
| `docs/handoff/AFS-STUDIO-MASCOT-EDGE-REVIEW-20260619.md` | 旧 mascot edge review，当前 TuanTuan/Studio 状态不从此入口恢复 |
| `docs/handoff/AFS-STUDIO-TUANTUAN-MOTION-20260619.md` | 旧 TuanTuan motion 记录；无当前索引入口 |
| `docs/handoff/AFS-STUDIO-TUANTUAN-V2-SPRITE-MEMORY-API-20260623.md` | 旧 TuanTuan V2 sprite memory API 记录；无当前索引入口 |

### `docs/archive/maintenance/`

| 原路径 | C2 删除安全性 |
|---|---|
| `docs/maintenance/AFS-CLI-HELP-CLEANUP-001.md` | 旧 CLI 帮助清理账本；当前 CLI 状态由测试和最新记录覆盖 |
| `docs/maintenance/AFS-IGNORED-RUNTIME-CLEANUP-MANIFEST-001.md` | 旧 ignored runtime 清理清单；不是当前 repo 清理入口 |
| `docs/maintenance/AFS-KLING-MEDIA-RETENTION-20260613.md` | 旧 Kling 媒体保留说明；provider/media 字节清理另开 lane |
| `docs/maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md` | 旧 mainline foundation 清理账本；当前维护入口已替代 |
| `docs/maintenance/AFS-MAINTENANCE-DEBT-CLOSURE-001.zh-CN.md` | 旧维护债关闭说明；由当前 summary/ledger 承接 |
| `docs/maintenance/AFS-R3-REDUNDANCY-EVIDENCE-PRESERVATION-CLEANUP-20260701.md` | R3 已收口；当前队列不再从该文件进入 |
| `docs/maintenance/AFS-RUNS-RETENTION-20260613.md` | 旧 runs retention 说明；ignored runtime evidence 未触碰 |
| `docs/maintenance/AFS-SCRIPT-REVIEW-FLOW-MAINLINE-DEPLOY-20260622.md` | 旧 script review/deploy 说明；本轮无 deploy authority |
| `docs/maintenance/AFS-TEST-MAINTENANCE-AUDIT-20260629.md` | 旧 test maintenance audit 说明；当前审计由 `tools/maintenance_audit.py` 和最新队列进入 |

## 恢复路径

删除文件仍可从 C2 父提交恢复：

```powershell
git restore --source=61b5b8b9d98577df1d2b7c0c273f32869ffb8518 -- docs/archive/handoff docs/archive/maintenance
```

如只恢复单个文件，将命令最后的目录替换为上表对应路径即可。

## C2 验证证据

| 检查 | 结果 |
|---|---|
| `docs/handoff/INDEX.md` target check | passed |
| `tools/repository_retention_review.py --summary-only` | `delete_candidate_count=0`, `manual_review_required_count=0`, `remove_applied_pending_stage=20` |
| `tools/maintenance_audit.py` | `status=warning`, `failed=0`, warning-only existing categories |
| `pytest tests/test_repository_retention_review.py tests/test_maintenance_audit.py -q` | `15 passed` |
| `git diff --check` | passed |
| `git diff --cached --check` | passed before staging |

## 剩余债务

| 债务 | 下一负责人 / 动作 |
|---|---|
| 仍有 tracker/devlog 引用的旧 handoff 和 maintenance 文件 | 后续 docs-only lane 逐个解除引用或保留索引后再归档 |
| `DEVLOG.md` 和 `TASK_TRACKER.md` 仍然 oversized | 单独 current-state index / compact ledger lane，不能混入产品实现 |
| `secret_like_fragments` 仍为低置信 warning | 只读安全/provider 分类 lane；不得在 docs cleanup 中误删代码 |
| active Runtime/Studio/provider/test oversized files | 对应模块维护 lane，按 focused pytest 和 full gate 验证 |

## 非声明

本账本不声明 product readiness、provider smoke、live provider call、generated-media
quality、human creative acceptance、business validation、server/runtime health、deploy
alignment、public/legal/patent approval、durable-memory promotion 或 CompanyOS/COS
active-rule promotion。

## 2026-07-06 Batch 1 Docs Redundancy Standard

Dispatch:
`TD-AFS-V02-CLEAN-P1-DOCS-REDUNDANCY-STANDARD-AND-BATCH1-20260706-002`

Expected feedback:
`BU-AFS-V02-CLEAN-P1-DOCS-REDUNDANCY-STANDARD-AND-BATCH1-20260706-002`

Conservative redundancy deletion standard:

Delete or archive a docs candidate only when all of these are true:

1. It is not linked by current entrypoints such as `docs/README.md`,
   `docs/handoff/INDEX.md`, `TASK_TRACKER.md`, `DEVLOG.md`, or current cleanup
   ledgers.
2. It is not referenced outside itself by filename in the repo.
3. It is not current architecture, contract, test, provider, Runtime, Studio,
   OpenAPI, package, Owner/CTO decision, evaluator, active PR, or safety-boundary
   evidence.
4. It is obsolete, duplicated, low-quality, misleading, or superseded by a
   current summary/index.
5. Its restoration path from git is recorded before deletion.

Keep or defer any candidate that is active evidence, current task routing,
provider/runtime safety boundary, Owner/CTO decision evidence, PR #96/#97/#100
review or record surface, or material whose currentness cannot be proven in the
cleanup lane.

Batch 1 classification:

| Classification | Path or rule | Rationale | Action |
|---|---|---|---|
| keep | `docs/README.md`, `docs/handoff/INDEX.md`, this cleanup ledger, active P0/P1/P2 handoffs, current maintenance evidence, PR #96/#97/#100 review/record surfaces | Current entrypoints or active evidence; not deletion candidates in this lane. | Unchanged |
| consolidate | Historical docs already summarized by `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`, `docs/handoff/INDEX.md`, and this ledger | Summary/index surfaces carry the recoverable context; individual stale packets require fresh proof before removal. | Defer unless no-reference rule passes |
| delete_now | `docs/maintenance/AFS-R2-REDUNDANCY-BRANCH-WORKTREE-DISPOSITION-PACKET-20260701.md` | Not linked by current entrypoints; `rg --files-with-matches --fixed-strings` found no filename references outside itself; branch/worktree residue disposition is superseded by current maintenance summary/ledger surfaces. | Delete in Batch 1 |
| defer | All other `docs/handoff/` and `docs/maintenance/` files not proven by the strict no-reference check | Many remain indexed, active, or referenced by current records; others need separate review. | No change |
| do_not_touch | Code, tests, provider/OpenAPI/Runtime/server files, generated media/private KB/CompanyOS/COS, local configs/secrets, `docs/demo-docs-20260629/`, PR #96/#97/#100 surfaces | Outside dispatch scope or explicitly protected. | No change |

Restoration path:

```powershell
git restore --source=a1f92690 -- docs/maintenance/AFS-R2-REDUNDANCY-BRANCH-WORKTREE-DISPOSITION-PACKET-20260701.md
```

Batch 1 verification evidence:

| Check | Result |
|---|---|
| Base readback | `HEAD` matched fetched `origin/master` before branch creation. |
| Working branch | `codex/docs-redundancy-standard-batch1-20260706` |
| Initial dirty state | Clean before edits. |
| Reference check | Candidate had zero filename references outside itself and no current entrypoint references. |
| Post-delete reference readback | Filename references exist only in this deletion record and `DEVLOG.md` restoration notes. |
| `python tools\repository_retention_review.py --root . --summary-only` | `delete_candidate_count=0`, `manual_review_required_count=0`, `remove_applied_pending_stage=1`. |
| `python tools\maintenance_audit.py` | `status=warning`, `failed=0`; warnings are existing legacy/chinese-coverage/secret-like/oversized categories. |
| `python -m pytest tests\test_repository_retention_review.py tests\test_maintenance_audit.py -q` | `15 passed`. |
| `git diff --check` | passed. |
| Scope | Docs-only; no code, tests, provider, Runtime, OpenAPI, server, generated media, private KB, COS, or CompanyOS mutation. |

## 2026-07-07 Batch B Branch / Worktree History Compaction Gate

Dispatch:
`TD-AFS-V02-CLEAN-P1-DOCS-MAINTENANCE-BATCHB-BRANCH-WORKTREE-HISTORY-COMPACTION-20260707-001`

Bottom-up feedback:
`BU-AFS-V02-CLEAN-P1-DOCS-MAINTENANCE-BATCHB-BRANCH-WORKTREE-HISTORY-COMPACTION-20260707-001`

Working branch:
`codex/docs-batchb-history-compaction-20260707`

Base:
`origin/master=33b176139c0b7df37977a39d10112be3b8c1e66e`

This lane rechecked the Batch B branch/worktree history candidates after PR
#101 and PR #97 merged, after PR #96 refreshed onto current master, and after
the Candidate B local docs branches were cleaned. The accepted Batch 1
redundancy standard still applies. No Batch B candidate met all archive/delete
conditions without touching currently active or PR-overlapped records, so this
lane records a hold/defer decision instead of deleting files.

Active PR overlap:

| PR | State | Head | Changed records | Handling |
|---|---|---|---|---|
| #96 | open draft; current PR body/readback records `mergeable=true`, exact-head CI green, base/merge-base `33b176139c0b7df37977a39d10112be3b8c1e66e` | `codex/afs-package-project-book-draft-20260706` at `ef2e8a6dde5b9aac2c9d99a763a4c7e39a8ec3ba` | `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, `docs/handoff/AFS-P1-AFS-PACKAGE-PROJECT-BOOK-DRAFT-NONFINAL-20260706.md` | No edits to overlapped active PR record streams. |
| #97 | merged into `master`; PR page shows merged state and deleted remote source branch | `codex/true-local-edit-contract-reconciliation-20260706` final head `c48349e94b99fea134221ea85f29f28377abb9e8`; merge commit/current master `33b176139c0b7df37977a39d10112be3b8c1e66e` | `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, `docs/handoff/AFS-P1-TRUE-LOCAL-EDIT-CONTRACT-RECONCILIATION-NONFINAL-20260706.md` | No active PR overlap remains; records are now protected current-master evidence. |

Batch B candidate classification:

| Classification | Path | Reference evidence | Action |
|---|---|---|---|
| defer_reference_hold | `docs/maintenance/AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md` | Referenced by `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md`; deleting it would require rewriting a related historical decision packet. | Keep. |
| defer_reference_hold | `docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md` | Referenced outside itself by `DEVLOG.md` and `docs/handoff/AFS-T53-INTERACTIVE-MANGA-BRANCH-PACKAGE-CONTRACT-20260701.md`; `DEVLOG.md` is also PR #96/#97 overlap. | Keep. |
| defer_current_handoff_hold | `docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md` | Referenced by current handoffs `docs/handoff/AFS-FULL-PYTEST-RESIDUAL-TRIAGE-20260701.md` and `docs/handoff/AFS-STUDIO-MAIN-PATH-BROWSER-QA-20260701.md`, plus the maintenance status packet. | Keep. |
| defer_index_overlap_hold | `docs/maintenance/AFS-BRANCH-MERGE-CLEANUP-20260622.md` | Linked from `docs/handoff/INDEX.md` Current Maintenance Evidence. Removing the link would touch an active PR #96/#97 overlap file and a Batch A-held index zone. | Keep. |

Future restore source if a later authorized lane removes any Batch B file after
clearing references:

```powershell
git restore --source=33b176139c0b7df37977a39d10112be3b8c1e66e -- docs/maintenance/AFS-BRANCH-WORKTREE-CONSOLIDATION-DECISION-PACKET-20260701.md
git restore --source=33b176139c0b7df37977a39d10112be3b8c1e66e -- docs/maintenance/AFS-MAINTENANCE-REDUNDANCY-STATUS-20260701.md
git restore --source=33b176139c0b7df37977a39d10112be3b8c1e66e -- docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md
git restore --source=33b176139c0b7df37977a39d10112be3b8c1e66e -- docs/maintenance/AFS-BRANCH-MERGE-CLEANUP-20260622.md
```

Verification notes:

| Check | Result |
|---|---|
| Startup scan | `project-development-workflow` fallback skill, `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md`, `DEVLOG.md`, `docs/handoff/INDEX.md`, current maintenance ledgers, candidate files, git status, live master, PR #96/#97 metadata/pathlists read. |
| Current live master | `origin/master=33b176139c0b7df37977a39d10112be3b8c1e66e`; matches PR #97 merge record after PR #101. |
| Branch base refresh | Branch rebased from previous `10b8821f7f9b5edcb53dff84253f60d0c4edbc04` base onto current `origin/master=33b176139c0b7df37977a39d10112be3b8c1e66e`; changed path set remained this ledger only. |
| PR #96 readback | Open draft at `ef2e8a6dde5b9aac2c9d99a763a4c7e39a8ec3ba`, base/merge-base `33b176139c0b7df37977a39d10112be3b8c1e66e`, exact-head CI green per current PR body/readback. |
| PR #97 readback | Merged; final head `c48349e94b99fea134221ea85f29f28377abb9e8`, merge commit/current master `33b176139c0b7df37977a39d10112be3b8c1e66e`, remote source branch deleted per PR page. |
| Initial dirty state | Clean before edits on `codex/docs-batchb-history-compaction-20260707`. |
| Reference scans before action | Ran fixed-string scans for each candidate filename and full path. Results are summarized in the classification table above. |
| Post-action reference posture | No candidate was deleted or archived, so reference graph remains intentionally unchanged. |
| `git diff --check` | passed. |
| `python tools\repository_retention_review.py --summary-only` | `delete_candidate_count=0`, `manual_review_required_count=0`. |
| `python tools\maintenance_audit.py` | `status=warning`, `failed=0`; warnings are existing legacy-frozen, Chinese coverage, secret-like fragment, and oversized-file categories. |
| Added-lines secret scan | passed; no added secret/token/key pattern matches. |
| Tests | Not run; no code, schema, Runtime, Studio, OpenAPI, provider, or test files changed. |
| Changed path boundary | This ledger only. No code, tests, provider, Runtime, OpenAPI, Studio, package, server, media, private KB, source-KB, COS, or CompanyOS mutation. |

Non-claims:

- No broad cleanup completion, Batch A index compaction, PR #96/#97 mutation,
  primary checkout normalization, branch/worktree deletion, archive execution,
  provider/runtime/browser/media/server action, release, deploy, Owner/human/
  business/legal/public acceptance, package finality, COS/CompanyOS/source-KB
  mutation, durable-memory promotion, or self-archive is claimed.
