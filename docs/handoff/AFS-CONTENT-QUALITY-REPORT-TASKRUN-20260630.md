# AFS 第七波 TaskRun - 内容质量报告合同 - 2026-06-30

## 任务

Task ID：`AFS-T14 Content Quality Evaluation`

关联任务域：`AFS-T3 Data Model`、`AFS-T4 Production Graph`、
`AFS-T5 Asset Cards`、`AFS-T18 Logs / Tests / Quality`、
`AFS-T19 Handoff / COS Feedback`。

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`6071ef1aa665930df2b9fa383260fc68ed4e4e64`

本轮是项目书长周期目标模式的第一条实际工程切片。目标不是扩展生成能力，
也不是开启 provider，而是给 Runtime 的 storyboard breakdown 输出增加一个
可测试、可记录、可交接的内容质量报告合同。后续剧本理解、动态分镜、资产识别、
关键帧定义和视频分镜质量都应先能被这个安全报告观察，再进入 UI 或 provider。

## 启动与脏改账本

已按项目规则读取 `project-development-workflow` fallback：

```text
C:\Users\chenzy\.codex\skills\project-development-workflow\SKILL.md
```

本轮读取范围包括 AFS 本地规则、冻结基线 handoff、Runtime Service 入口、
Studio 与 algorithm 文件索引、OpenAPI snapshot parity 测试、以及 2026-06-30
AFS 项目书包。

启动时本地状态：

```text
## master...origin/master
HEAD 6071ef1aa665930df2b9fa383260fc68ed4e4e64
origin/master 6071ef1aa665930df2b9fa383260fc68ed4e4e64
?? docs/demo-docs-20260629/
```

随后从冻结基线创建并切换到：

```text
codex/afs-project-book-full-goal-20260630
```

脏改归属：

| 表面 | 归属 | 处理 |
|---|---|---|
| `docs/demo-docs-20260629/` | 既有 do-not-touch 本地演示文档 | 不读取为本轮成果，不 stage，不清理。 |
| `agentflow/algorithms/content_quality_evaluation/` | 本轮新增算法合同 | 保留，职责单一，只做 deterministic 质量报告。 |
| `agentflow/algorithms/__init__.py` | 本轮算法库登记 | 保留，只登记新算法模块。 |
| `apps/api/runtime_storyboard_breakdown.py` | 本轮 Runtime 接入 | 保留，新增安全 artifact 和响应字段。 |
| `tests/test_api_runtime_storyboard_content_quality.py` | 本轮 focused regression | 保留，表达项目书质量合同。 |
| `tests/test_algorithm_library_contracts.py` | 本轮算法库合同测试 | 保留，防止模块隐藏化。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和下一步；不处理 Learning_notes 其他脏状态。 |

## 本轮 TaskRun Packet

目标：

- 为 storyboard breakdown 输出增加 `content_quality_report`。
- 报告必须检查剧本来源 grounding、动态拆镜策略、资产证据、关键帧/视频意图字段、
  安全边界和人工复核边界。
- Runtime 必须把报告写成 artifact，并在 safe manifest 里记录报告状态。

写入范围：

- `agentflow/algorithms/content_quality_evaluation/__init__.py`
- `agentflow/algorithms/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- focused tests 与项目记录
- 私有项目书包 execution state YAML

非目标：

- 不做 Studio UI。
- 不扩 OpenAPI 公共面。
- 不改 provider gate。
- 不调用 live LLM、image、video、vision、ASR 或 external download。
- 不部署、不同步服务器。
- 不声明人类创意验收、业务验证或 durable memory promotion。

Provider gate 状态：

本轮只走本地 deterministic path。服务器 `/health` 曾观察到的 provider gate 状态
不构成本轮授权，本轮没有使用这些 gate。

## 本轮改动

新增 `agentflow.algorithms.content_quality_evaluation`，暴露：

```text
evaluate_storyboard_content_quality(...)
```

报告包含这些检查项：

- `script_understanding`
- `script_source_grounding`
- `dynamic_shot_count`
- `asset_evidence`
- `keyframe_and_video_intent`
- `safe_boundary`

Runtime storyboard breakdown 现在会：

- 在 `asset_graph` 和 graph asset id 生成后构建内容质量报告；
- 在 safe manifest 中写入 `content_quality_report_status`；
- 写出 `content_quality_report.json`；
- 注册 `content_quality_report` artifact；
- 在 API payload 中返回 `content_quality_report`。

报告固定保留：

```text
human_review_needed=true
```

这意味着它只能证明结构质量合同已经生成，不能证明内容被人类接受、创意质量通过、
provider smoke 通过、业务验证成立或经验已经晋升为长期记忆。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_content_quality.py -q
# 预期失败：KeyError: 'content_quality_report'
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_algorithm_library_contracts.py -q
# 33 passed, 1 existing Starlette/httpx deprecation warning
```

OpenAPI parity：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_storyboard_content_quality.py -q
# 2 passed, 1 existing Starlette/httpx deprecation warning
```

全量与 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 691 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# 初次运行 failed=0，但本 handoff 英文比例过高，新增 human_doc_chinese_coverage warning。
# 已将本 handoff 改为中文主文档后重跑：
# status=warning; failed=0; passed=3; warning=4
# human_doc_chinese_coverage=22，未包含本 handoff；新增维护债已修复。

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T14; evidence_state=structure_verified_content_quality_contract
```

## 证据状态

当前证据状态：

```text
structure_verified_content_quality_contract
```

非声明边界：

- 不是 provider smoke。
- 不是人类创意验收。
- 不是业务验证。
- 不是公网发布。
- 不是 durable memory promotion。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| 新内容质量算法模块 | keep | 单一职责、deterministic、无 provider 访问。 |
| Runtime storyboard 接入 | keep | 增量安全 artifact/响应字段，不改 route 行为和 provider gate。 |
| 新 focused test | keep | 表达项目书质量合同，避免脆弱字符串断言。 |
| OpenAPI snapshot | keep unchanged | parity 测试通过，不需要公共 schema 扩面。 |
| 本 handoff 初版英文比例过高 | merge/repair | 已改成中文主文档，避免引入新增中文覆盖维护债。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

本轮没有新增重复 route、重复 schema、provider adapter、生成媒体、provider raw、
signed URL、secret 或客户材料。

## 延后事项

- 做第一组 benchmark script fixture，用来覆盖对话戏、动作戏、情绪转折、多场景、
  关键道具和多角色群戏。
- 把 `content_quality_report` 接到 Studio QA 视图前，先用 deterministic workflow
  积累至少一轮真实回归样例。
- 如果未来 Runtime response schema 要显式化，再决定是否把报告公开进 OpenAPI
  response model；本轮保持 additive 且 snapshot-compatible。
- 人类仍需判断这些质量 rubrics 是否符合真实创作者使用方式。

## 下一步

推荐下一任务：

```text
AFS-T13/T14 Benchmark Script Pack + Content Quality Regression
```

目标是在不调用 provider 的情况下，建立第一批基准剧本 fixture，并用它们检查
动态分镜、资产识别、关键帧/视频意图和固定模板化风险。
