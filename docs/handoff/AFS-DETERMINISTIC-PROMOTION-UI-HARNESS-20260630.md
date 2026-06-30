# AFS TaskRun - Deterministic Promotion UI Harness - 2026-06-30

## 任务

Task ID: `AFS-T14 Deterministic Promotion UI Harness`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `e2a4862222444783a6c4cfe53246d150c886c379`

Status: implemented and locally verified; commit/push handled after this record.

本轮目标是把 T12 的 Studio promotion provenance 从“字符串存在”提升为“可执行的确定性
payload contract”。T13 已证明 `/studio/` 可以在浏览器里走空项目 gate 和新建项目
流程，但还没有证明固定视觉资产 promotion 请求在 UI 层真的会构造出正确的 Runtime
payload。T14 只补这个 harness，不启动 provider，不生成媒体，不改 Runtime/OpenAPI。

## 中文结论

`visual-asset-panel.js` 过去直接拼 `promoteVisualAsset` payload，静态测试只能看见某些
字符串在文件里。T14 新增 `visual-asset-promotion-request.js`，把 promotion 请求构造抽成
可 import 的小函数 `buildVisualAssetPromotionPayload(...)`。测试现在用 Node 直接调用它，
验证 accepted asset-card human gate 会进入 `source_human_gate_id` 和
`source_asset_card_candidate_id`，并且没有 accepted gate 时不会发送这两个字段。

这让后续 UI 或浏览器 harness 可以复用同一个 builder，而不是在测试里猜 DOM 或复制
Runtime payload 逻辑。面板文件因此从 300 行降到 298 行，没有新增 oversized warning。
本轮没有改变 Runtime contract，也没有改变直接人工固定资产仍可用的产品行为。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/studio/src/panels/visual-asset-promotion-request.js` | T14 harness module | Keep; single-responsibility payload builder. |
| `apps/studio/src/panels/visual-asset-panel.js` | T14 integration | Keep; calls builder, behavior unchanged. |
| `tests/test_web_studio_visual_asset_promotion_gate_static.py` | T14 executable harness | Keep; Node-import payload contract test. |
| `tests/test_web_studio_prompt_script_static.py` | T14 test calibration | Keep; `supersedes_asset_id` now asserted in builder module. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T14 records | Keep. |
| External execution state YAML | T14 state | Update minimally outside AFS git. |
| `docs/demo-docs-20260629/` | Existing untracked docs | Do not touch, do not stage, do not clean. |

## Contract

The harness verifies:

- fixed promotion payload includes `source_image_asset_refs`, `source_node_id`,
  `supersedes_asset_id`, `review_decision`, and deterministic `reviewed_at`;
- latest accepted `asset_card_candidate` human gate is selected;
- human gate IDs and candidate IDs are sanitized before entering the payload;
- direct promotion without an accepted gate omits provenance fields;
- payload does not include provider fields or media bytes.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# red baseline: missing visual-asset-promotion-request.js

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 2 passed

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_web_studio_human_gate_static.py tests\test_api_runtime_visual_asset_promotion_gate.py tests\test_api_runtime_visual_assets.py -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# first run: 1 failed due brittle static assertion after builder extraction
# final run: 709 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed
```

## Evidence State

```text
structure_verified_deterministic_promotion_ui_harness
```

This is deterministic Studio contract verification. It is not provider smoke,
not generated media evidence, not human creative acceptance, not business
validation, not deploy verification, and not server three-end sync.

## Cleanup Review

- No duplicate promotion path was added.
- `visual-asset-panel.js` line count decreased to 298.
- New builder module is 28 lines and single-purpose.
- Existing `docs/demo-docs-20260629/` remains untouched.

## Deferred Items

- A future browser harness can combine deterministic image asset fixture upload,
  visual asset modal interaction, and Runtime response inspection.
- Provider smoke still requires explicit user authorization for the specific
  capability.

## Next Valid Task

```text
AFS-T15 Deterministic Promotion Browser Harness or Provider-Smoke Readiness Review
```
