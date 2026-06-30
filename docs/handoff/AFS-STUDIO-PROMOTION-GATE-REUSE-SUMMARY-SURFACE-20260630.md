# AFS-T23 Studio Promotion Gate Reuse Summary Surface

## 任务信息

- Task ID: `AFS-T23`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点: `aacd4158275a46314db97120c7277d2f374b9806`
- 模式: provider-closed full goal-mode product slice
- 目标: 在固定资产确认弹窗中显示最新 accepted asset-card human gate 的安全复用摘要，让操作者在 promotion review 前看到该候选是否来自跨镜头复用建议。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/human-gate-provenance.js`
- `apps/studio/src/panels/visual-asset-panel-render.js`
- `apps/studio/index.html`
- `apps/studio/styles/visual-asset-promotion-gate.css`
- `tests/test_web_studio_visual_asset_promotion_gate_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PROMOTION-GATE-REUSE-SUMMARY-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Studio fixed-asset promotion review now has a local-only review summary:

- `promotionGateReviewSummary(node)` reads the latest accepted `asset_card_candidate` human-gate decision.
- It parses only safe `note` fragments produced by Studio human gate:
  - `reuse_scope`
  - `shot_ref_count`
  - `writes_fixed_asset=false`
- The visual asset panel displays `Human gate` plus a short label such as `Project reuse / 3 shots`.
- Legacy accepted decisions without reuse summary fall back to `Accepted asset-card gate` instead of inventing a reuse scope.

The Runtime promotion payload remains unchanged. `buildVisualAssetPromotionPayload` still sends only the existing `source_human_gate_id` and `source_asset_card_candidate_id` provenance fields; it does not send `reuse_scope`, provider raw, local paths, signed URLs, secrets, or media bytes.

## 本轮改动

- Added `promotionGateReviewSummary(node)` to `human-gate-provenance.js`.
- Rendered the summary in `visual-asset-panel-render.js`.
- Added a small `visual-asset-promotion-gate.css` stylesheet and loaded it from the Studio HTML entrypoint instead of adding to the already-oversized modal stylesheet.
- Extended static/Node tests for review surface, safe parsing, legacy fallback, and no Runtime payload expansion.

## 非目标和边界

- 不扩展 Runtime API。
- 不修改 OpenAPI。
- 不写 fixed asset memory beyond the existing explicit promotion action.
- 不调用 live LLM/image/video/ASR provider。
- 不做 provider smoke。
- 不部署、不服务器同步。
- 不声明 human creative acceptance 或 business validation。

## 验证

已完成 focused 验证:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 3 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_web_studio_human_gate_static.py -q
# 7 passed, 1 existing warning

npm.cmd run check:studio-js
# JS syntax check passed: 132 files
```

已完成收口验证:

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
# yaml_ok=True; current_task_id=AFS-T23

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 未新增 route、schema、provider path、一次性工具或重复 sanitizer。
- Review summary 只使用已有 safe human-gate decision note。
- Runtime promotion payload 不扩字段，避免 OpenAPI 漂移。
- 新样式没有继续增大既有 oversized `modals.css`。
- `docs/demo-docs-20260629/` 未清理、未归入本轮成果。

## 下一步

下一批最有效切片: 在 provider-closed 前提下，把 promotion 后的 fixed visual asset 与 storyboard/production graph 的复用证据链进一步连起来，或者补一个 Studio 可用入口让操作者更容易从脚本进入 storyboard -> candidates -> human gate -> promotion 的闭环。达到 20 commits、80 files 或 5000 insertions 任一阈值时必须停止新增功能并进入 merge review gate。
