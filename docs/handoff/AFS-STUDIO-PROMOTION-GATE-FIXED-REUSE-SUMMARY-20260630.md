# AFS-T29 Studio Promotion Gate Fixed Reuse Summary

## 任务信息

- Task ID: `AFS-T29`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `bf4bc7fc4b6b3bac653fdf46125d0daf35601a66`
- 模式: provider-closed full goal-mode product slice
- 状态: 本地验证待提交和推送

本轮目标是把 T28 写入 human-gate note 的 `fixed_asset_reuse_count` 接到固定
视觉资产 promotion review summary。这样操作者确认固定资产前，能同时看到
asset-card candidate provenance 和 production graph fixed reuse 背景。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/human-gate-provenance.js`
- `apps/studio/src/panels/visual-asset-panel-render.js`
- `tests/test_web_studio_visual_asset_promotion_gate_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PROMOTION-GATE-FIXED-REUSE-SUMMARY-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Studio promotion gate summary 现在会从最近一次 accepted asset-card human gate
note 中解析:

- `reuse_scope`
- `shot_ref_count`
- `fixed_asset_reuse_count`

Promotion panel 的二级摘要会显示:

```text
asset_card_candidate:main_character · Fixed reuse / 1 asset
```

这只是 Studio review metadata，不改变 Runtime promotion payload，不新增
OpenAPI 字段，也不声明 human creative acceptance 或 business validation。

## 本轮改动

- `promotionGateReviewSummary()` 增加 `fixed_asset_reuse_count` 和
  `fixed_asset_reuse_label`。
- `visual-asset-panel-render.js` 使用 `promotionGateSummaryMeta()` 展示
  candidate id 与 fixed reuse label。
- 更新 visual asset promotion gate static regression。

## 非目标和边界

- 不新增 Runtime route。
- 不新增 Runtime request 字段。
- 不扩展 OpenAPI path。
- 不新增 provider 调用。
- 不生成或保存媒体字节。
- 不写入 provider raw response、signed URL、本地绝对路径、token 或 secret。
- 不做 deploy、server sync 或 Runtime health check。
- 不声明 human creative acceptance 或 business validation。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 3 passed

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
# yaml_ok=True; current_task_id=AFS-T29

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增重复 sanitizer。
- 没有新增一次性工具。
- 没有新增 Runtime route 或 public API。
- 触达 Studio JS 文件和测试文件均低于 300 行。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

下一切片可以继续加强 promotion 后 fixed asset 与 keyframe/production graph
之间的证据链，或进入更高价值的 Studio 可用入口。分支达到 20 commits、
80 changed files 或 5000 insertions 任一阈值时，必须停止新增功能并进入
merge review gate。
