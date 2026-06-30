# AFS 第十五波 TaskRun - Studio Human Gate UI Hook - 2026-06-30

## 任务

Task ID：`AFS-T11 Studio Human Gate UI Hook`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`4c18b2660ed1bef2875eb529330eb84cb74ead1b`

本轮目标是在 T10 Runtime human gate contract 之后，为 Studio 加一个最小 UI hook，让用户能从现有节点菜单记录 asset-card candidate 和 keyframe generation bridge 的本地人工 gate 决策。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `apps/studio/src/human-gate.js` | 本轮 Studio UI hook | 保留，单职责生成 human gate target、弹层和事件 payload。 |
| `apps/studio/src/main.js` | 本轮事件总线接入 | 保留，处理 `afs:human-gate-decision` 并调用 Runtime client。 |
| `apps/studio/src/panels/node-menu.js` | 本轮菜单入口 | 保留，仅当节点存在 human gate target 时显示 `记录人工 Gate`。 |
| `apps/studio/src/script-breakdown.js` | 本轮 asset-card candidate target 来源 | 保留，将 Runtime `asset_card_candidates` 安全引用挂到源节点参数。 |
| `apps/studio/src/node-keyframe-response.js` | 本轮 keyframe bridge target 来源 | 保留，将 `generation_bridge` 和 artifact id 挂到 image 节点参数。 |
| `apps/studio/styles/node-result.css` | 本轮弹层样式 | 保留，新增紧凑 human gate popover 样式。 |
| `tests/test_web_studio_human_gate_static.py` | 本轮 focused regression | 保留，防止 UI 绕过 Runtime 或误触发 promotion/provider。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 合同判断

T11 只把 T10 的 Runtime contract 接到 Studio：

- Studio 使用 `runtime.recordHumanGateDecision(payload)`。
- UI 入口是节点菜单中的 `记录人工 Gate`。
- asset-card candidate target 来自 storyboard breakdown 的 `asset_card_candidates` safe artifact。
- keyframe target 来自 keyframe generation response 的 `generation_bridge` safe artifact。
- 点击 `下一步` 发送 `accepted_for_next_step`。
- 点击 `需修订` 发送 `needs_revision`。

T11 不做：

- fixed asset promotion。
- provider gate open。
- provider smoke。
- generated media acceptance。
- business validation。
- durable memory promotion。

## 本轮改动

- 新增 `apps/studio/src/human-gate.js`：
  - `humanGateTargets(node)` 生成可记录目标。
  - `openHumanGateMenu(node, anchor)` 打开轻量弹层。
  - 弹层派发 `afs:human-gate-decision`，不直接接触 provider 或 CLI。
- `main.js` 新增 `bindHumanGateDecisionEvents()` 和 `handleHumanGateDecision(...)`：
  - 调用 Runtime client。
  - 将返回的 `human_gate_id` 作为安全摘要写入 `node.params.humanGateDecisions`。
- `script-breakdown.js` 保存 `assetCardCandidates` 和 `assetCardCandidateArtifactId`。
- `node-keyframe-response.js` 保存 `lastGenerationBridge` 和 `lastGenerationBridgeArtifactId`。
- `node-menu.js` 在存在 human gate target 时显示菜单入口。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# 预期失败：缺少 apps/studio/src/human-gate.js。
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py tests\test_web_studio_assets_generation_static.py::test_mvp_experience_hardening_video_status_and_feedback_markers tests\test_api_runtime_human_gate.py -q
# 5 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 126 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe -m pytest
# 705 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 126 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings remain existing categories: legacy_frozen_surface,
# human_doc_chinese_coverage, secret_like_fragments, oversized_files.
# oversized_files remains at 59 after moving human gate styles out of node-result.css.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T11
```

## 证据状态

当前本轮 evidence state：

```text
structure_verified_studio_human_gate_ui_hook
```

这不是 provider smoke，不是 generated media evidence，不是 human creative acceptance，不是 fixed asset promotion，不是 business validation，不是部署验证，也不是服务器三端同步。

## Cleanup Review

- 未清理 `docs/demo-docs-20260629/`。
- 未读取或提交 secret、provider key、signed URL、cookie、token、本地私有素材字节、provider raw response 或生成媒体字节。
- 没有打开 LLM/image/video/vision/ASR provider gate。
- 没有部署、没有服务器同步、没有 Runtime restart。
- 新 UI hook 是 thin event/client layer，不新增第二套 Runtime contract。
- 没有改 OpenAPI；T11 复用 T10 已公开 route。

## Deferred Items

- 需要后续任务定义 accepted asset-card candidate 如何进入 fixed asset promotion。T11 不自动晋升。
- 需要后续任务定义 keyframe bridge accepted 后的 provider smoke 条件。T11 不打开 gate。
- 可在后续浏览器 QA 中检查弹层交互和节点状态展示，但本轮只做静态/contract verification。

## 下一步

建议下一步任务：

```text
AFS-T12 Asset Promotion Gate
```

目标是定义 human-gate accepted asset-card candidate 到 fixed visual asset promotion 的显式边界，仍需保持 provider gate、human creative acceptance 和 business validation 分离。
