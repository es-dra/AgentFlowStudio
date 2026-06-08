---
doc_type: historical_docs_summary
status: active
last_updated: 2026-06-08
owner_role: Maintainability Steward
confidentiality: internal
---

# AFS 历史文档中文摘要索引

本文是旧英文长文的中文摘要归档入口。它不逐字翻译旧文档，而是给出当前是否仍有效、替代路径、保留理由和退休条件。

## 适用范围

以下文档属于历史证据或旧规划，不再作为新任务的第一入口：

- `docs/handoff/`
- `docs/task_briefs/`
- `docs/company-kb-feedback-candidates/`
- `docs/retrospectives/`
- `docs/maintenance/` 中已经被当前维护账本替代的旧维护记录。
- `docs/strategy/`
- `docs/agentflow_*.md`
- `docs/local_alpha_*.md`
- `docs/product_*.md`
- `docs/architecture/production_memory_*.md`
- `docs/testing/`
- `docs/workbench/`
- 旧 alpha、golden path、real slicing、tool contract、workflow plan、workspace contract 等阶段性文档。

## 当前替代入口

新任务优先阅读：

- `README.md`
- `AGENTS.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/README.md`
- `docs/company_operating_model.md`
- `docs/local_internal_test_runbook.md`
- `docs/project_manifest_contract.md`
- `docs/frontend_integration/`
- `docs/maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`
- `docs/maintenance/AFS-REPOSITORY-RETENTION-REVIEW-001.zh-CN.md`
- `docs/handoff/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.md`

## 分类摘要

| 类别 | 做了什么 | 当前是否仍有效 | 替代路径 |
|---|---|---|---|
| 旧 handoff | 记录过去每个小切片的范围、验证、边界和剩余风险 | 只作为历史证据有效 | 当前任务看 `TASK_TRACKER.md`、`DEVLOG.md`、当前 handoff |
| 旧 task brief | 记录过去分支的任务边界和验收 | 只作为任务历史有效 | 新任务用当前维护账本和 Runtime Service v0.2 计划 |
| 旧路线图 | 记录 Local Alpha、Phase 15、产品化等阶段判断 | 只作为背景有效 | 当前路线看 `TASK_TRACKER.md` 的下一步队列 |
| 旧 contract 文档 | 记录早期 schema、router、skill、memory 约束 | 作为历史背景和测试引用有效 | 当前机器契约以 `agentflow/contracts/`、`examples/agentflow/`、测试为准 |
| 旧 provider / media 文档 | 记录 MiniMax、Kling、Image2 等 smoke 过程 | 只作为 provider recovery evidence 有效 | 当前 provider 能力必须走 Provider Validation Gate |
| 旧 Company KB feedback | 记录过去候选反馈 | 只作为 candidate evidence 有效 | 当前源头知识库是 `D:\Learning materials\Learning_notes\10-Startup` |

## 保留理由

- 这些文档包含历史验证命令、边界声明、provider 失败和恢复证据。
- 多个测试仍读取其中的路径、关键词或 contract 说明。
- 直接删除会破坏可追溯性，也会让后续维护无法解释历史设计来源。

## 退休条件

历史文档可以在满足以下条件后被删除或进一步压缩：

1. 当前测试不再读取该文档。
2. 关键信息已进入中文维护账本、contract、runbook 或 archive summary。
3. `repository_retention_review` 不再给它保留状态。
4. `maintenance_audit` 和 focused tests 通过。
5. 删除动作写入 `DEVLOG.md`、`TASK_TRACKER.md` 或新的 maintenance ledger。

## 非声明边界

- 本摘要不是 human acceptance。
- 本摘要不是 business validation。
- 本摘要不是 durable memory。
- 本摘要不晋升 `10-Startup` / COS active rule。
- 本摘要不复制 secret、signed URL、本地私有素材字节、生成媒体或 provider response body。
