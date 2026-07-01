# AFS 历史文档摘要与当前性索引 - 2026-07-02

本文是 `docs/handoff/`、`docs/maintenance/` 和其它历史长文的当前性摘要。它的作用是降低维护审计噪声，让后续维护者区分“仍需阅读的当前入口”和“只需保留摘要的历史证据”。C2 清理已经把 C1 归档批次中无当前索引入口、无外部引用、且已由本摘要和清理账本承接的 20 个历史文件从 live tree 删除；恢复路径是 git 历史，不再是常驻 archive 目录。本文不把任何反馈晋升为长期记忆或 CompanyOS active rule。

## 范围

| 项目 | 处理方式 | 当前判断 |
|---|---|---|
| `docs/handoff/` | 先摘要和索引，后续再由独立 lane 判断是否归档或删除 | 保留为历史证据，不作为默认任务入口 |
| `docs/maintenance/` | 保留维护账本和决策记录，避免重复审计 | 当前维护入口仍从最新审计和本摘要进入 |
| `docs/task_briefs/`、`docs/testing/`、`docs/workbench/` | 只在需要追溯旧任务时读取 | 不作为当前 MVP 路线入口 |
| `docs/archive/` | 保留历史摘要；不再为低价值旧 handoff/maintenance 文件保留常驻副本 | 不作为产品、Runtime、provider 或发布状态声明 |

## 当前入口

当前 AFS 工作仍从这些入口开始：

| 类型 | 入口 | 用途 |
|---|---|---|
| 项目规则 | `AGENTS.md`、`docs/company_operating_model.md` | 规则层级、provider gate、仓库边界、记录要求 |
| 任务状态 | `TASK_TRACKER.md`、`BACKLOG.md` | 当前待办、后续维护项、非声明边界 |
| 维护队列 | `docs/maintenance/AFS-FULL-MAINTENANCE-QUEUE-AUDIT-NEXT-ACTION-20260702.md` | C1 之后的低风险清理入口和延后项 |
| Handoff 索引 | `docs/handoff/INDEX.md` | 当前可用交接文件的路由入口 |
| 产品主线 | `/studio/`、`apps/studio/`、Runtime Service | 当前本地内测 MVP 主线 |

## Handoff 当前性分组

| 分组 | 代表文件 | 当前动作 |
|---|---|---|
| T46-T54 主线 evidence | `AFS-MAIN-LOOP-E2E-INTEGRATION-GATE-20260630.md`、`AFS-T51-*`、`AFS-T52-*`、`AFS-T53-*`、`AFS-T54-*` | 保留；这些文件仍记录 provider-closed 主线证据、验证命令和非声明边界 |
| 2026-06-30 TASKRUN 包 | `*-TASKRUN-20260630.md` | 摘要保留；不逐个作为新任务入口，后续可在明确授权下合并或归档 |
| Studio/Runtime 当前能力记录 | `AFS-STUDIO-*`、`AFS-RUNTIME-*`、`AFS-PROVIDER-*` | 按 `docs/handoff/INDEX.md` 路由读取；旧 UI 或旧 Workbench 方向不自动恢复 |
| 早期 MVP/QA 记录 | `AFS-MVP-*`、`AFS-BROWSER-*`、旧 acceptance drill | 保留为历史 evidence；需要先检查当前 Runtime/Studio 状态再引用 |
| CompanyOS feedback candidates | `AFS-COMPANY-OS-FEEDBACK-CANDIDATE-*`、`COS-GFR-V1-PROJECTION-*` | 只作为候选反馈和执行投影证据；不能自动晋升为 active rule |
| 人工验收 runbook | `AFS-HUMAN-ACCEPTANCE-RUNBOOK-*` | 只代表人工验收流程材料，不代表验收已完成 |

## Maintenance 当前性分组

| 分组 | 代表文件 | 当前动作 |
|---|---|---|
| 最新维护队列 | `AFS-FULL-MAINTENANCE-QUEUE-AUDIT-NEXT-ACTION-20260702.md` | 当前维护入口；C1 从这里继承范围和验证 |
| 分支/冗余整理 | `AFS-R2-*`、`AFS-R3-*`、`AFS-BRANCH-*` | 保留结论；不要重复做已关闭的分支卫生审计 |
| legacy freeze | `AFS-LEGACY-FREEZE-20260613.md`、`AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613.md` | 保留；后续 legacy 删除必须单独 lane、单独验证 |
| provider/视频/媒体保留 | `AFS-PROVIDER-*`、`AFS-KLING-*`、`AFS-RUNS-RETENTION-*` | 延后复核；不在 docs cleanup lane 打开 provider 或清理媒体字节 |
| 浏览器 QA 与内部测试 | `AFS-BROWSER-*`、`AFS-STUDIO-FULL-COVERAGE-*`、`AFS-INTERNAL-BETA-*` | 作为验证历史保留；当前性需重新跑本地检查后声明 |
| 中文化与清理旧账本 | `*.zh-CN.md`、`AFS-ACTUAL-CLEANUP-*` | 保留；后续只做小范围索引或合并，不做批量删除 |

## 保留和延后规则

| 分类 | 规则 |
|---|---|
| keep | 最新规则、当前任务 tracker、Runtime/Studio 主线 handoff、最新维护队列 |
| summary-only | 旧 QA、旧 MVP、旧 TASKRUN 包、旧 handoff 证据 |
| review_for_currentness | 架构、contract、runbook、测试计划等可能仍被当前主线引用的文档 |
| archive-candidate | 已有摘要且不再服务当前 MVP 的旧 handoff 或历史 brief |
| owner-decision | 任何会删除历史证据、影响 server/deploy、触碰 provider、或改变 CompanyOS 规则状态的动作 |
| do-not-touch | `docs/demo-docs-20260629/`、local config、secret、provider raw response、signed URL、generated/private media bytes、ignored runtime evidence |

## 2026-07-02 已归档批次

本轮在 C1 分支上执行第一批实质瘦身：11 个无当前索引入口、无外部引用的 handoff
移动到 `docs/archive/handoff/`，9 个无当前索引入口、无外部引用的 maintenance 账本移动到
`docs/archive/maintenance/`。完整清单和判定理由见
`docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md`。

本轮没有物理删除 tracked docs。仍被 `TASK_TRACKER.md`、`DEVLOG.md` 或维护账本引用的旧文件
保留在原位置，后续必须先解除或明确保留引用，再判断归档或删除。

## 2026-07-02 已删除批次

C2 文档瘦身在 `codex/afs-docs-low-value-deletion-cleanup-20260702` 上执行直接删除：
C1 归档的 20 个文件已经由本摘要、`docs/handoff/INDEX.md` 的维护入口和
`docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` 承接。
这些文件没有当前索引入口，除 `DEVLOG.md` 与维护摘要/账本外没有活跃引用；继续保留
`docs/archive/handoff/` 与 `docs/archive/maintenance/` 的逐文件副本只会扩大历史噪声。

恢复方式：

```powershell
git restore --source=61b5b8b9d98577df1d2b7c0c273f32869ffb8518 -- docs/archive/handoff docs/archive/maintenance
```

## C1 清理结论

- 已建立历史文档中文摘要和当前性索引，供维护审计区分历史证据与当前入口。
- 本摘要允许后续维护审计把历史 handoff/maintenance 文档作为已摘要历史证据处理；C1 已将 20 个无当前索引入口且无外部引用的历史文件移出活跃目录，C2 已删除这些常驻 archive 副本，恢复路径保留在 git 历史中。
- 后续若要删除或归档文件，必须先基于本摘要列出候选清单、证明当前索引不再引用、运行维护审计，并取得明确授权。
- 本轮不执行 server sync、deploy、Runtime health 检查、provider smoke、外部下载、媒体清理、COS/CompanyOS active-rule promotion。

## 非声明

本文不声明产品完成、部署完成、Runtime 当前健康、provider smoke、live provider call、生成媒体质量、人工创意验收、商业验证、公开发布、法律或专利判断、长期记忆晋升、CompanyOS/COS active-rule 晋升。
