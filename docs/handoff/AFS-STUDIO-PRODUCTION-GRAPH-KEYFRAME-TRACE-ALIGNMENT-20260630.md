# AFS-T34 Studio Production Graph Keyframe Trace Alignment

## 任务信息

- Task ID: `AFS-T34`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `992e53b8`
- 模式: provider-closed full goal-mode product slice
- 状态: 已实现并通过本地 closeout 验证；commit/push 和 post-push branch preflight 待执行

本轮把 Studio 已保存的 Runtime `production_graph` 复用审查摘要对齐到
keyframe layer 和 `lastKeyframeSourceEvidenceTrace`。目标是让输出记录能说明
关键帧来源证据与 production graph 固定资产复用之间的关系，同时不扩大 Runtime
API、OpenAPI 或 provider prompt inclusion policy。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/storyboard-keyframes.js`
- `apps/studio/src/keyframe-source-evidence-trace.js`
- `tests/test_web_studio_keyframe_production_graph_trace.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PRODUCTION-GRAPH-KEYFRAME-TRACE-ALIGNMENT-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

Studio 的 storyboard script node 已经保存:

```text
params.storyboardBreakdown.productionGraph
params.storyboardBreakdown.productionGraphArtifactId
```

T34 将这个已存在的本地 review 上下文投影为:

```text
keyframeLayer.production_graph_review
lastKeyframeSourceEvidenceTrace.production_graph_review
```

字段白名单:

```text
artifact_id
fixed_asset_reuse_count
fixed_visual_asset_ids
```

这些字段是 Studio 本地 review/trace contract，不是新的 public Runtime API。
它们不包含 provider raw、signed URL、本地绝对路径、secret、生成媒体字节或
素材字节。

## 本轮改动

- `storyboard-keyframes.js` 在创建 keyframe layer 时读取脚本节点上的
  production graph snapshot 摘要，并写入安全的 `production_graph_review`。
- `keyframe-source-evidence-trace.js` 在生成本地 keyframe trace 时复用该摘要，
  并在输出记录摘要中显示 `production_graph fixed_reuse=<count>` 和 artifact id。
- 新增 focused tests 验证 keyframe layer 和 trace 都只保留白名单字段。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不调用 live LLM/image/video/ASR provider。
- 不把 source evidence 或 production graph review 注入 provider prompt。
- 不生成、读取或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_keyframe_layer_source_evidence.py tests\test_web_studio_production_graph_reuse_static.py
# 9 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed

YAML parse check for external execution state
# pending final post-record check

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer 体系；只做本地白名单投影。
- 没有新增 UI 面板、Runtime/public API surface 或 OpenAPI path。
- 新测试独立成小文件，避免继续放大既有 keyframe source-evidence 测试文件。
- 本轮未清理历史不明文件，也未触碰 `docs/demo-docs-20260629/`。

## 下一步

T34 commit/push 和 branch preflight 通过后，如果分支仍低于 `20 commits`、
`80 files`、`5000 insertions` 任一阈值，可以继续 provider-closed 切片。
下一步最有效方向是让 fixed asset promotion/human gate 的 review 记录更清楚地进入
Studio operator evidence chain，同时仍不打开 provider gate。
