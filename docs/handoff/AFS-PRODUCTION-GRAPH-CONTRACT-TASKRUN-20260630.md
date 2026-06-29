# AFS 第九波 TaskRun - Production Graph 合同 - 2026-06-30

## 任务

Task ID：`AFS-T3 Data Model + AFS-T4 Production Graph`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`d55ecdb92177cf48988fb730d1b8bb55e1b8c53f`

本轮目标是在不扩展生成能力、不接 Studio UI、不打开 provider gate 的前提下，给 Runtime storyboard breakdown
增加一个安全的 `production_graph` 快照。它把剧本节点、候选分镜、候选资产和内容质量报告放在同一个可测试的数据合同里，
为后续资产卡、关键帧和视频链路提供结构化衔接点。

## 启动与脏改账本

本轮延续项目书目标模式分支，已在前置波次完成 startup scan。本轮接手时 AFS 工作树只包含当前 production graph
切片的未提交改动，以及既有 do-not-touch 本地目录：

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/production_graph/` | 本轮新增算法合同 | 保留，单一职责，只生成安全候选图快照。 |
| `agentflow/algorithms/__init__.py` | 本轮算法库登记 | 保留，只增加 `production_graph` 模块登记。 |
| `apps/api/runtime_storyboard_breakdown.py` | 本轮 Runtime 接入 | 保留，只增加 response、safe manifest 和 artifact 写出字段。 |
| `tests/test_api_runtime_production_graph_contract.py` | 本轮 focused contract test | 保留，覆盖 Runtime 输出和安全边界。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 读取范围

- `agentflow/algorithms/content_quality_evaluation/__init__.py`
- `agentflow/algorithms/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `apps/api/runtime_asset_graph.py`
- `tests/test_api_runtime_storyboard_content_quality.py`
- `tests/test_api_runtime_storyboard_breakdown.py`
- `tests/test_algorithm_library_contracts.py`
- `tests/test_api_runtime_openapi_snapshot.py`
- `docs/handoff/AFS-CONTENT-QUALITY-REPORT-TASKRUN-20260630.md`
- `docs/handoff/AFS-CONTENT-QUALITY-BENCHMARKS-TASKRUN-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

## 写入范围

- `agentflow/algorithms/production_graph/__init__.py`
- `agentflow/algorithms/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `tests/test_api_runtime_production_graph_contract.py`
- `docs/handoff/AFS-PRODUCTION-GRAPH-CONTRACT-TASKRUN-20260630.md`
- `docs/handoff/INDEX.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- 私有项目书 execution state YAML

## 合同判断

`production_graph` 现在是 Runtime storyboard breakdown 的内部安全响应合同和 artifact 合同，不是新的公共 OpenAPI path。
它是 additive 字段：不改变现有 route，不要求 Studio 立即消费，不引入数据库迁移，也不声明固定资产记忆已经形成。

稳定边界：

- `artifact_type=agentflow_production_graph_snapshot`
- `schema_version=0.1.0`
- `graph_stage=storyboard_candidate_graph`
- `summary` 只包含项目、脚本、节点数、关系数、分镜数、候选资产数、内容质量状态和人工复核需求。
- `nodes` 只包含 `script`、`shot`、`asset`、`quality_report` 四类安全节点。
- `relationships` 只表达 `script_contains_shot`、`shot_contains_asset`、`quality_report_evaluates_storyboard`。
- `writes_long_term_memory=false`，`writes_company_kb=false`。
- `non_claims` 明确排除生成媒体、provider smoke、人类验收、业务验证和 durable memory promotion。

安全边界：

- 不包含 provider key、token、cookie、signed URL、provider raw response、本地绝对路径或媒体字节。
- Runtime 写出前对 `production_graph` 运行 `reject_unsafe_payload`。
- focused test 对图快照做 unsafe marker 检查，并断言不含 `api_key`、`signed_url`、`d:\` 等危险片段。

## 本轮改动

新增 `agentflow.algorithms.production_graph`：

- 暴露 `build_storyboard_production_graph(...)`。
- 从脚本 id、结构化分镜、候选资产图、内容质量报告构建安全 graph snapshot。
- 保持 deterministic，本地运行，不访问 provider，不读取外部文件。

Runtime storyboard breakdown 现在会：

- 在 `content_quality_report` 后构建 `production_graph`。
- 在 API payload 中返回 `production_graph`。
- 在 safe manifest 中记录 `production_graph_node_count`。
- 写出 `production_graph_snapshot.json`。
- 注册 `production_graph_snapshot` artifact。

测试新增：

- `tests/test_api_runtime_production_graph_contract.py` 覆盖 Runtime 输出、节点类型、关系类型、安全字段、artifact 登记和算法库登记。
- 没有继续向既有超长的 `tests/test_algorithm_library_contracts.py` 塞入新断言，避免扩大测试维护债。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py -q
# 预期失败：KeyError: 'production_graph'
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_algorithm_library_contracts.py -q
# 17 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_algorithm_library_contracts.py -q
# 35 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_production_graph_contract.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 694 passed, 520 deselected, 2 warnings

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
# yaml_parse_ok; current_task_id=AFS-T3-T4
```

## 证据状态

当前证据状态：

```text
structure_verified_production_graph_contract
```

这不是 provider smoke，不是人类创意验收，不是业务验证，不是部署验证，不是服务器三端同步，也不是 durable memory promotion。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| `production_graph` 算法模块 | keep | 职责单一，服务候选生产图合同。 |
| Runtime additive response/artifact 字段 | keep | 提供后续资产卡和关键帧链路的结构化衔接，不扩 route。 |
| focused Runtime contract test | keep | 防止图快照、artifact、safe manifest 漂移。 |
| OpenAPI snapshot | unchanged | 本轮不新增 path，不扩公共 OpenAPI 面。 |
| Studio UI | unchanged | 本轮只稳定 Runtime 合同，暂不做消费界面。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、signed URL、secret、客户材料或真实成本。

## 延后事项

- 后续可以把 `production_graph` 与资产卡候选合同衔接，形成 `asset_card_candidate` 节点。
- 后续可以加入关键帧需求节点和视频 motion intent 节点，但应等对应合同稳定后再扩。
- Studio 是否展示 production graph 需要单独 UI 任务，不在本轮完成。
- 如果未来 public response model 明确化，再决定是否把 `production_graph` 字段提升为 OpenAPI schema 的显式响应模型。

## 下一步

推荐下一任务：

```text
AFS-T5 Asset Card Candidate Contract
```

目标是把当前候选资产图中的角色、场景、道具候选收敛成安全、可复核、可落地的资产卡候选合同，继续保持 provider gate 关闭。
