# AFS-T22 Studio Human Gate Asset Reuse Policy Surface

## 任务信息

- Task ID: `AFS-T22`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点: `5ef0e5d691dabd39b32bae8276cff1d6fe4739e4`
- 模式: provider-closed full goal-mode product slice
- 目标: 把 Runtime 产生的 `asset_card_candidates.reuse_policy` 带到 Studio human-gate surface，让操作者在记录 gate 前能看到候选资产是跨镜头复用候选还是单镜头候选。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/human-gate.js`
- `apps/studio/styles/human-gate.css`
- `tests/test_web_studio_human_gate_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-HUMAN-GATE-ASSET-REUSE-POLICY-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Studio `humanGateTargets(node)` 现在会把 asset-card candidate 的安全复用摘要带到 human gate target:

- `reuse_policy.suggested_reuse_scope`
  - `project_reuse_candidate`
  - `shot_local_candidate`
- `reuse_policy.shot_ref_count`
- `reuse_policy.requires_human_confirmation`
- `reuse_policy.writes_fixed_asset=false`
- `reuse_label`, 用于 human gate 菜单中的可见短标记。
- `note`, 用于提交 Runtime human-gate decision 时记录安全摘要。

这个 surface 只来自 Runtime 已返回的 safe candidate data。Studio 不读取 provider raw、本地绝对路径、signed URL、secret、生成媒体字节，也不直接写 fixed visual assets。

## 本轮改动

- Studio human gate 菜单左侧增加 `reuse_label` marker，例如 `Project reuse / 3 shots`。
- `recordHumanGateDecision` payload 的 `note` 现在可使用 target 级安全摘要。
- asset-card candidate target 输出最小 `reuse_policy`，并强制 `writes_fixed_asset=false`。
- 新增静态/Node contract 测试，确认 target 输出、可见 marker 和 no-promotion 边界。

## 非目标和边界

- 不扩展 Runtime API。
- 不修改 OpenAPI。
- 不写 fixed asset memory。
- 不调用 live LLM/image/video/ASR provider。
- 不做 provider smoke。
- 不部署、不服务器同步。
- 不声明 human creative acceptance 或 business validation。

## 验证

已完成 focused 验证:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_human_gate_static.py -q
# 2 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py tests\test_api_runtime_asset_card_candidates_contract.py -q
# 5 passed, 1 existing warning
```

已完成收口验证:

```text
npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T22

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 未新增 route、schema、provider path、一次性工具或重复 sanitizer。
- UI 改动只在已有 human-gate surface 内部完成。
- 新增测试文件仍低于维护阈值。
- `docs/demo-docs-20260629/` 未清理、未归入本轮成果。

## 下一步

下一批最有效切片: 在 provider-closed 前提下，把 accepted asset-card human gate summary 与固定资产 promotion review surface 进一步串联，或继续增强 storyboard/production graph 对固定资产复用的可解释证据。达到 20 commits、80 files 或 5000 insertions 任一阈值时必须停止新增功能并进入 merge review gate。
