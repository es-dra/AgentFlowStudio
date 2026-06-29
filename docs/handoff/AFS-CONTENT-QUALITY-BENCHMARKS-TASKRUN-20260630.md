# AFS 第八波 TaskRun - 内容质量基准剧本回归 - 2026-06-30

## 任务

Task ID：`AFS-T13/T14 Benchmark Script Pack + Content Quality Regression`

当前分支：`codex/afs-project-book-full-goal-20260630`

基线提交：`8c20e4da098afc7b0f21ed3599c3d7783a64a723`

本轮目标是在第七波 `content_quality_report` 合同之后，增加第一组 repo-safe
基准剧本 fixture，用 deterministic 测试覆盖不同内容类型下的动态分镜、资产识别、
source grounding、关键帧/视频意图字段和非声明边界。

## 读写范围

读取范围：

- `apps/api/runtime_storyboard_local.py`
- `apps/api/runtime_asset_graph.py`
- `agentflow/algorithms/content_quality_evaluation/__init__.py`
- `tests/test_api_runtime_storyboard_breakdown.py`
- `examples/agentflow/`

写入范围：

- `examples/agentflow/content_quality_benchmark_scripts.example.json`
- `tests/test_storyboard_content_quality_benchmarks.py`
- `apps/api/runtime_storyboard_local.py`
- 项目记录与 handoff
- 私有项目书 execution state YAML

非目标：

- 不联网调研竞品。
- 不做 provider smoke。
- 不做 Studio UI。
- 不扩 OpenAPI。
- 不部署、不同步服务器。
- 不声明人类验收、创意质量验收、业务验证或 durable memory promotion。

## 本轮改动

新增 `examples/agentflow/content_quality_benchmark_scripts.example.json`，包含 6 个
安全虚构剧本样例：

- 双人对话 / 调查铺垫：办公室、照片、电话压力。
- 动作戏：山巅双角色对决和关键道具。
- 情绪转折：海边信件。
- 多场景追踪：办公室、街道、地图。
- 逐行步骤脚本：10 行设备悬疑步骤，防固定五镜。
- 多角色餐厅戏：两人、餐厅、信件交接。

新增 `tests/test_storyboard_content_quality_benchmarks.py`，对每个 fixture 执行：

- `local_storyboard_shots`
- `build_asset_graph`
- `evaluate_storyboard_content_quality`

测试断言：

- 分镜数量落在每个样例的预期范围内。
- 不把所有剧本压成同一个固定镜头数量。
- source grounding 通过。
- dynamic shot-count 检查通过。
- asset evidence 检查通过。
- keyframe / video intent 检查通过。
- 预期角色、场景和道具进入 candidate asset graph。
- 报告仍然要求 human review。

测试红线暴露两个真实小缺口：

- 剧本里出现 `海边` 时，fallback 已有 scene hint，但 `_infer_scene_label` 未归一成
  `海边`，导致回退到 `主要场景`。
- 剧本里出现 `餐厅` 时，同样回退到 `主要场景`。

本轮只做同类最小修正：在 `_infer_scene_label` 中补 `海边/海面/沙滩/灯塔` 和
`餐厅` 的场景归一。没有增加 provider、UI 或新路线。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_storyboard_content_quality_benchmarks.py -q
# 预期失败：benchmark fixture 文件不存在
```

fixture 后第一次 focused 运行：

```text
# 失败：emotion_beach_letter 缺少 ('海边', 'scene')
```

补 `海边` 后第二次 focused 运行：

```text
# 失败：multi_character_restaurant_note 缺少 ('餐厅', 'scene')
```

补 `餐厅` 后 focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_storyboard_content_quality_benchmarks.py -q
# 1 passed
```

storyboard/content-quality focused set：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_storyboard_content_quality_benchmarks.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py tests\test_api_runtime_storyboard_modules.py -q
# 20 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout 在本文件写入后执行并补充到 DEVLOG / execution state。

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 692 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# human_doc_chinese_coverage=22，未包含本轮新增 handoff

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T13-T14
```

## 证据状态

当前 focused 证据状态：

```text
structure_verified_content_quality_benchmark_regression
```

这不是 provider smoke，不是人类创意验收，不是业务验证，不是 durable memory
promotion。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| benchmark fixture JSON | keep | 安全虚构文本，服务 T13/T14 回归。 |
| benchmark pytest | keep | 一条测试覆盖 6 个样例，避免堆多个重复测试文件。 |
| `_infer_scene_label` 两个场景归一 | keep | 同类最小修正，修复 fixture 暴露的真实缺口。 |
| provider / Studio / OpenAPI | unchanged | 本轮不触碰。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、signed URL、secret、客户材料或真实成本。

## 延后事项

- 后续可把 benchmark fixture 扩到 8-10 个，并加入人工评分字段。
- 后续可为 `街道空间` / 多场景 asset graph 的场景拆分做更细的 production graph
  表达；本轮不扩大 scope。
- Studio UI 是否展示内容质量报告，仍需在积累更多 deterministic 结果后再决定。

## 下一步

推荐下一任务：

```text
AFS-T3/T4 Production Graph Data Model Contract
```

目标是把当前 Runtime 内部的 `asset_graph`、`content_quality_report`、storyboard
shots 和后续 asset card candidate 关系整理成更稳定的数据模型合同，不急着做 UI。
