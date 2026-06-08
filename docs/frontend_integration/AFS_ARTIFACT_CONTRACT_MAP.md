# AFS Artifact Contract 对照表

状态：Runtime Service v0.1 的前端 artifact 对照表。本文给前端团队说明“拿什么字段、画什么视图、哪些内容不能碰”。API path、JSON key、`artifact_type` 保持英文，因为它们是机器契约。

## 总原则

前端状态必须来自 safe artifact，不能来自私有本地路径，也不能直接理解 CLI 内部流程。

```text
API action returns job + artifact refs
-> frontend stores job_id and artifact_id
-> frontend reads artifact payload through /artifacts/{artifact_id}
-> UI renders known fields
```

前端可以保存 `project_id`、`job_id`、`artifact_id` 和 UI layout preferences。前端不得保存 private paths、provider configs、API keys、signed URLs、local media bytes 或 provider response bodies。

## 核心 artifact

| `artifact_type` | 生成来源 | 前端用途 |
|---|---|---|
| `agentflow_project_manifest` | `/projects`、Runtime Service project update | 项目首页、run/package/feedback/profile version 关系 |
| `agentflow_real_asset_test_run_harness` | `/runs/asset-test` | Round 1 状态、pass/block/non-claim |
| `agentflow_production_memory_asset_test_package` | `/runs/asset-test` | 测试包是否可 review |
| `agentflow_production_memory_asset_feedback_event` | `/runs/asset-test` | tester feedback raw evidence |
| `agentflow_production_memory_asset_profile_update_candidate` | `/runs/asset-test` | candidate-only profile update |
| `agentflow_production_memory_asset_profile_promotion_decision` | `/runs/asset-test` | 显式 operator decision |
| `agentflow_production_memory_asset_profile_version` | `/runs/asset-test` | 可复用 profile version |
| `agentflow_production_memory_asset_profile_context_projection` | `/runs/asset-test`、`/runs/two-round-validate` | included / blocked context refs |
| `agentflow_production_memory_asset_consistency_review` | `/runs/asset-test`、`/runs/two-round-validate` | kept / partial / failed / unknown review |
| `agentflow_two_round_context_runtime_report` | `/runs/two-round-validate` | Round 1 到 Round 2 的 context runtime report |
| `agentflow_runtime_feedback_event` | `/feedback` | 运行期 raw feedback evidence |
| `agentflow_provider_safe_manifest` | `/provider/validation-plan` | provider readiness / blocker state |

## Project Manifest 视图

主要字段：

- `project_id`
- `project_type`
- `goal`
- `status`
- `source_assets`
- `runs`
- `packages`
- `feedback_refs`
- `profile_version_refs`

允许的 `status`：

```text
in_progress
blocked
ready_for_next_round
```

前端把它渲染为项目首页：项目是什么、当前有哪些 runs、哪些 package 可看、哪些 feedback/profile version 可复用、项目是否被 block。

## Round 1 报告视图

`artifact_type`：

```text
agentflow_real_asset_test_run_harness
```

关键字段：

- `run_status`
- `project_id`
- `package.status`
- `material_evidence`
- `feedback.result`
- `candidate.status`
- `promotion.decision`
- `profile_version`
- `context_projection`
- `consistency_review`
- `passes`
- `blocks`
- `non_claims`
- `provider_calls_started`
- `writes_long_term_memory`
- `writes_company_kb`

前端解释：

- `run_status=passed`：Round 1 结构可 review。
- `run_status=completed_with_blocks`：展示 blockers，但仍允许 artifact inspection。
- `feedback.feedback_is_memory=false`：必须显示 raw evidence，不得显示为 durable memory。

## Context Projection 视图

关键字段：

- `projection_status`
- `included_refs`
- `blocked_refs`

每个 included ref 必须展示 `ref_id`、`profile_version`、`source_profile_id`、`source_version_id`、`source_decision_id`、`evidence_refs`。每个 blocked ref 必须展示 `ref_id` 和 `reason`。

## Two-Round Runtime Report 视图

`artifact_type`：

```text
agentflow_two_round_context_runtime_report
```

关键字段：

- `runtime_verification_status`
- `improvement_assessment`
- `reason_if_not_improved`
- `round_2_context_inclusions`
- `round_2_blocked_refs`
- `controls`
- `claim_boundaries`
- `non_claims`

允许的 `improvement_assessment`：

```text
improved
no_clear_improvement
blocked
```

允许的 `reason_if_not_improved`：

```text
context_insufficient
feedback_unclear
profile_granularity_wrong
test_materials_insufficient
provider_or_output_randomness_too_high
cannot_judge
```

## Provider Safe Manifest 视图

关键字段：

- `status`
- `provider_capability`
- `request_summary`
- `artifact_refs`
- `blockers`
- `redacted_metadata`
- `provider_calls_started`
- `non_claims`

前端解释：

- `blocked`：展示 blocker list。
- `ready_not_run`：provider preflight ready，但没有发起 live call。
- `succeeded`：provider smoke 按 safe manifest 成功。
- `failed`：provider smoke 失败，只展示 safe failure summary。

## 画布节点映射

| UI 节点 | 后端 artifact/action | 状态来源 |
|---|---|---|
| Project | `agentflow_project_manifest` | `manifest.status` |
| Asset Test | `/runs/asset-test` | `job.status`、`report.run_status` |
| Feedback | `asset_feedback_event` 或 `agentflow_runtime_feedback_event` | feedback result |
| Candidate | `asset_profile_update_candidate` | candidate status |
| Profile Version | `asset_profile_version` | promotion decision |
| Context Projection | `asset_profile_context_projection` | projection status |
| Round 2 Validation | `two_round_context_runtime_report` | runtime verification status |
| Provider Gate | `provider_safe_manifest` | manifest status |

## 非声明边界

这些 artifact 只能支持结构验证和 runtime verification。它们不等于 human acceptance、business validation、durable memory，也不会自动写入 `10-Startup`。
