# AFS 第十波 TaskRun - 资产卡候选合同 - 2026-06-30

## 任务

Task ID：`AFS-T5 Asset Cards`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`72f818c37f031524dd3f163acd61e7c7acc92f79`

本轮目标不是调用 vision provider 生成正式资产卡，也不是把候选资产写入固定资产记忆，而是在 storyboard breakdown 阶段从
`asset_graph` 派生一组安全的 `asset_card_candidates`。这些候选只表达角色、场景、道具的可复核资产卡草稿种子、证据引用、
确认状态和后续 provider enrichment gate，为后续资产卡确认、关键帧和上下文解析提供稳定合同。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/asset_card_candidates/` | 本轮新增算法合同 | 保留，单一职责，只从候选资产图生成安全资产卡候选。 |
| `agentflow/algorithms/__init__.py` | 本轮算法库登记 | 保留，登记 `asset_card_candidates`。 |
| `apps/api/runtime_storyboard_breakdown.py` | 本轮 Runtime 接入 | 保留，只增加 additive response、safe manifest 和 artifact 写出字段。 |
| `tests/test_api_runtime_asset_card_candidates_contract.py` | 本轮 focused contract test | 保留，覆盖登记、Runtime 输出、确认状态、安全边界和 artifact。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 读取范围

- `AFS-Task-Ledger-v0.1.md`
- `AFS-Project-Book-v0.1.md`
- `apps/api/runtime_storyboard_breakdown.py`
- `apps/api/runtime_asset_graph.py`
- `apps/api/runtime_asset_card_drafts.py`
- `agentflow/algorithms/asset_card_drafting/__init__.py`
- `agentflow/algorithms/production_graph/__init__.py`
- `tests/test_api_runtime_asset_card_drafts.py`
- `tests/test_api_runtime_production_graph_contract.py`
- `tests/test_api_runtime_storyboard_breakdown.py`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

## 写入范围

- `agentflow/algorithms/asset_card_candidates/__init__.py`
- `agentflow/algorithms/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `tests/test_api_runtime_asset_card_candidates_contract.py`
- `docs/handoff/AFS-ASSET-CARD-CANDIDATES-TASKRUN-20260630.md`
- `docs/handoff/INDEX.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- 私有项目书 execution state YAML

## 合同判断

`asset_card_candidates` 是 Runtime storyboard breakdown 的内部安全候选合同，不是现有 `/asset-card-drafts` provider 路线的替代品。

稳定边界：

- `artifact_type=agentflow_asset_card_candidate_set`
- `candidate_stage=storyboard_asset_card_candidates`
- 每个 candidate 绑定一个 `source_graph_asset_id`。
- 每个 candidate 固定为 `status=candidate`、`confirmation_state=needs_human_confirmation`。
- `draft_fields` 只包含 `display_name`、`narrative_role`、`visual_description_seed`、连续性约束、负面约束和后续 reference policy。
- `safe_evidence` 只包含 shot refs、证据 span 摘要和 confidence。
- `asset_memory_policy.writes_fixed_asset=false`。
- `provider_policy.provider_calls_started=false`，后续 enrichment 需要 `AFS_ALLOW_REMOTE_VISION`。

非声明边界：

- 不写 fixed asset memory。
- 不调用 vision/image/video/LLM provider。
- 不生成媒体。
- 不声明人类确认、创意验收、业务验证或 durable memory promotion。
- 不新增公共 OpenAPI path。
- 不改 Studio UI。

## 本轮改动

新增 `agentflow.algorithms.asset_card_candidates`：

- 暴露 `build_asset_card_candidates(project_id, asset_graph)`。
- 从 `asset_graph.assets` 生成角色、场景、道具候选资产卡。
- 保留 graph asset id、shot refs、evidence spans、continuity locks 和 negative locks。
- 明确 provider enrichment gate 和 fixed asset memory 禁止状态。

Runtime storyboard breakdown 现在会：

- 返回 `asset_card_candidates`。
- 在 safe manifest 中记录 `asset_card_candidate_count`。
- 写出 `asset_card_candidates.json`。
- 注册 `asset_card_candidates` artifact。
- 在写出前对 candidate set 运行 `reject_unsafe_payload`。

测试新增：

- `tests/test_api_runtime_asset_card_candidates_contract.py` 验证算法库登记、Runtime 输出、候选状态、人工确认边界、provider 关闭边界、artifact 登记和 unsafe marker。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py -q
# 预期失败：
# ImportError: cannot import name 'asset_card_candidates'
# KeyError: 'asset_card_candidates'
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py -q
# 2 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py -q
# 22 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_drafts.py tests\test_api_runtime_asset_card_modules.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_asset_card_candidates_contract.py -q
# 8 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 696 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings remain existing categories: legacy_frozen_surface, human_doc_chinese_coverage,
# secret_like_fragments, oversized_files

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T5
```

## 证据状态

当前证据状态：

```text
structure_verified_asset_card_candidate_contract
```

这不是 provider smoke，不是 human acceptance，不是 fixed asset memory，不是 business validation，不是部署验证，也不是三端服务器同步。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| `asset_card_candidates` 算法模块 | keep | 职责单一，服务 T5 候选资产卡合同。 |
| Runtime additive response/artifact 字段 | keep | 连接 asset graph 与后续资产卡确认，不改变 provider route。 |
| focused Runtime contract test | keep | 覆盖候选状态、artifact、安全字段和 provider closed 边界。 |
| `/asset-card-drafts` route | unchanged | 仍是 vision-gated enrichment 路线，本轮不扩展。 |
| OpenAPI snapshot | unchanged | 本轮不新增 path，不扩公共 OpenAPI 面。 |
| Studio UI | unchanged | 候选合同先稳定，后续再决定展示方式。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、signed URL、secret、客户材料或真实成本。

## 延后事项

- 后续需要把候选资产卡连接到人类确认状态和 fixed asset memory promotion gate。
- 后续可以让 Studio 展示候选资产卡并提供确认/编辑入口。
- 后续 provider-backed `/asset-card-drafts` 可以读取候选卡作为 enrichment seed，但必须继续由 vision gate 控制。
- 后续 context resolver 应只在人工确认后把资产纳入固定上下文，除非任务显式允许候选上下文实验。

## 下一步

推荐下一任务：

```text
AFS-T6 Context Resolver Candidate-to-Confirmed Boundary
```

目标是验证上下文解析器不会把未确认资产卡候选当成固定资产，同时为后续确认后的最小上下文选择建立合同。
