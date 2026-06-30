# AFS-T28 Studio Production Graph Fixed Asset Reuse Surface

## 任务信息

- Task ID: `AFS-T28`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `698bc28abf6bec8519450b4af8f5da55278ef2af`
- 模式: provider-closed full goal-mode product slice
- 状态: 本地验证待提交和推送

本轮目标是把 T25 Runtime production graph 中的 fixed visual asset reuse
证据接到 Studio 操作者路径里。Studio 之前只保存 asset-card candidates，
没有保存 `production_graph`，因此 graph 的 fixed-asset reuse 关系无法进入
human gate / inspection surface。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/script-breakdown.js`
- `apps/studio/src/human-gate.js`
- `tests/test_web_studio_production_graph_reuse_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PRODUCTION-GRAPH-FIXED-ASSET-REUSE-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Studio storyboard breakdown state 现在保存 Runtime 返回的:

- `productionGraph`
- `productionGraphArtifactId`

Human gate target metadata 现在会读取该 graph，并在 asset-card candidate
target 上显示 fixed asset reuse 摘要，例如:

```text
Fixed reuse / 1 asset
```

同时 human-gate note 增加安全计数字段:

```text
fixed_asset_reuse_count=1
```

本轮不新增 Runtime `target_type`，不改变 human gate API 的枚举。该字段只是
Studio review metadata，用于让操作者看到 production graph 已识别出的固定资产
复用上下文。

## 本轮改动

- `script-breakdown.js` 保存 `payload.production_graph` 和
  `artifacts.production_graph_snapshot.artifact_id`。
- `human-gate.js` 读取 production graph summary 或 fixed visual asset nodes，
  生成 `graph_reuse_label`。
- 新增小型 static/Node regression，覆盖 graph 持久化和 human gate target
  metadata。

## 非目标和边界

- 不新增 Runtime route。
- 不新增 Runtime request 字段。
- 不扩展 OpenAPI path。
- 不新增 provider 调用。
- 不生成或保存媒体字节。
- 不写入 provider raw response、signed URL、本地绝对路径、token 或 secret。
- 不新增 human gate `target_type`。
- 不做 deploy、server sync 或 Runtime health check。
- 不声明 human creative acceptance 或 business validation。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_production_graph_reuse_static.py tests\test_web_studio_human_gate_static.py -q
# 4 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T28

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增重复 sanitizer。
- 没有新增一次性工具。
- 没有新增 Runtime route 或 public API。
- `script-breakdown.js` 是既有 oversized warning，本轮新增字段直接服务
  Runtime graph -> Studio review 的产品闭环；maintenance audit 需要确认
  warning 数量不增加。
- 新测试文件保持小型，不增大已有 oversized static test。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

下一切片可以继续把 production graph / storyboard / fixed asset reuse 连接到
更直接的 Studio inspection surface，或加强从 candidate human gate 到 promotion
的操作路径。分支达到 20 commits、80 changed files 或 5000 insertions 任一
阈值时，必须停止新增功能并进入 merge review gate。
