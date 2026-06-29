# AFS 第十二波 TaskRun - Storyboard-to-Asset Evidence Ledger - 2026-06-30

## 任务

Task ID：`AFS-T9 Evidence Ledger`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`0121a9956b232086d5720b96d795d442ff3c523c`

本轮目标是在 storyboard breakdown 已有 `content_quality_report`、`production_graph`、`asset_card_candidates` 和 candidate-boundary 测试之后，补齐一个安全、可测试的 evidence ledger。

本轮不是生成能力扩展，不是 provider smoke，不是 Studio UI 改动，也不是服务器同步。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/evidence_ledger/__init__.py` | 本轮 T9 合同实现 | 保留，单职责构建 storyboard-to-asset 安全证据账本。 |
| `agentflow/algorithms/__init__.py` | 本轮算法注册 | 保留，将 `evidence_ledger` 纳入算法模块清单。 |
| `apps/api/runtime_storyboard_breakdown.py` | 本轮 Runtime additive integration | 保留，返回并持久化 `evidence_ledger` artifact。 |
| `tests/test_api_runtime_storyboard_evidence_ledger.py` | 本轮 focused regression | 保留，覆盖算法注册、Runtime payload、safe manifest 和 unsafe marker 边界。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-CONTEXT-RESOLVER-CANDIDATE-BOUNDARY-TASKRUN-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Project-Book-v0.1.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Task-Ledger-v0.1.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`
- `apps/api/runtime_storyboard_breakdown.py`
- `apps/api/runtime_tracing.py`
- `apps/api/runtime_store.py`
- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/content_quality_evaluation/__init__.py`
- `agentflow/algorithms/production_graph/__init__.py`
- `agentflow/algorithms/asset_card_candidates/__init__.py`
- `agentflow/contracts/agentops.py`
- Focused Runtime tests around storyboard, production graph, asset card candidates, and context resolver candidate boundary.

## 合同判断

`evidence_ledger` 是 storyboard-to-asset 阶段的安全证据聚合合同。

它记录以下事实：

- request plan 已形成。
- storyboard safe artifact 已形成。
- safe manifest 已形成。
- candidate `asset_graph` 已形成。
- `content_quality_report` 已形成。
- `production_graph_snapshot` 已形成。
- `asset_card_candidates` 已形成。
- provider gate 仍按环境门控，当前本地测试未启动 provider call。

它不记录、不声明：

- provider raw response。
- 本地绝对路径。
- secret、token、cookie、provider key。
- 私有媒体字节。
- signed/private external link。
- fixed asset memory。
- human creative acceptance。
- business validation。
- durable memory promotion。

## 本轮改动

- 新增 `agentflow.algorithms.evidence_ledger`。
- 新增 `build_storyboard_evidence_ledger(...)`，输出：
  - `artifact_type=agentflow_evidence_ledger`
  - `ledger_stage=storyboard_to_asset_candidate`
  - `summary.evidence_state=structure_verified_needs_human_review`
  - `evidence_items[]`，按 artifact role 分层记录证据状态。
  - `asset_evidence`，记录 candidate asset 和 asset-card candidate 计数。
  - `provider_evidence`，记录 gate 与 no raw/media/private-link storage 边界。
  - `trace_policy`，说明 run trace 在安全 artifact 写入后引用 ledger role。
- Runtime storyboard breakdown 现在：
  - response 增加 `evidence_ledger`。
  - safe manifest 增加 `evidence_ledger_entry_count` 和 `evidence_ledger_stage`。
  - 写入并注册 `evidence_ledger.json`。
  - `agentflow_run_trace` 的 generated artifact refs 会包含 `evidence_ledger`。
- Full pytest 发现 route 文件因本轮 additive 接入达到 313 行，触发
  `tests/test_api_runtime_storyboard_modules.py` 的 300 行维护阈值。
  已将 storyboard artifact 写入/注册逻辑拆到
  `apps/api/runtime_storyboard_artifacts.py`，`runtime_storyboard_breakdown.py`
  回到 267 行。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_evidence_ledger.py
# 预期失败：缺少 evidence_ledger 算法模块和 Runtime payload。
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_context_resolver_asset_card_candidates.py
# 7 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_modules.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_context_resolver_asset_card_candidates.py
# 8 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 699 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings remain existing categories: legacy_frozen_surface,
# human_doc_chinese_coverage, secret_like_fragments, oversized_files.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T9
```

## 证据状态

当前本轮 focused evidence state：

```text
structure_verified_storyboard_to_asset_evidence_ledger
```

这不是 provider smoke，不是 human acceptance，不是 fixed asset promotion，不是 business validation，不是部署验证，也不是服务器三端同步。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| `evidence_ledger` 算法包 | keep | 单职责、确定性、与现有算法包风格一致。 |
| Runtime storyboard additive field | keep | 不新增路由，不扩 OpenAPI path，不改变 Studio UI。 |
| `apps/api/runtime_storyboard_artifacts.py` | keep | 从 route 中拆出 artifact 写入/注册，修复 300 行维护阈值回归。 |
| focused evidence ledger test | keep | 避免把合同塞进现有 oversized 静态测试文件。 |
| `signed_url_stored` 初始字段名 | repaired | 被 unsafe marker 正确拦截；改为不含 forbidden fragment 的安全字段名。 |
| provider, Studio UI, OpenAPI | unchanged | 本轮不触达。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、secret、客户材料、真实成本或私有素材字节。

## 下一步

推荐下一任务：

```text
AFS-T8 Generation Path fake/local deterministic bridge
```

原因：当前 storyboard -> asset graph -> production graph -> asset candidates -> context resolver -> evidence ledger 已形成结构证据链。下一步最有效的是在 provider gate 仍关闭的前提下，为图片/关键帧生成路径补一个 fake/local deterministic artifact bridge，验证 ledger 如何承接生成 job、safe manifest 和 keyframe artifact refs。
