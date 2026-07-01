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
