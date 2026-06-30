# AFS Multi-Character Keyframe Bridge Regression

## 中文摘要

本轮对应 `AFS-T43`，目标是在不打开 provider 的前提下，为主闭环增加第二个
真实基准剧本回归。新增测试使用 `multi_character_restaurant_note`，覆盖两个
角色 `周岚` 和 `陈默` 的固定资产交接：先把两个角色各自提升为 fixed visual
asset，再运行真实 storyboard/content-quality 路径，记录本地反馈 overlay，
最后把两个固定角色资产一起送入 keyframe preflight 和 blocked keyframe
generation bridge。

本轮重点不是新增 Runtime API、OpenAPI、Studio UI 或 provider adapter，而是
证明多角色上下文不会在生成桥前丢失：bridge 的 `context_evidence` 同时包含
两个固定资产的安全来源证据，包括 fixed asset id、source human-gate id、
source asset-card candidate id 和非声明布尔值。由于 image provider gate
保持关闭，最终 keyframe job 仍然是 `blocked`，`provider_calls_started=false`，
没有 candidate preview，没有 reusable generated image asset，也没有生成媒体。

清理上，本轮没有复制 T41/T42 的长 setup，而是把既有
`tests/runtime_main_loop_e2e_support.py` 做最小参数化，用同一个上传图片和固定资产
promotion helper 支持第二个角色。所有新增或修改的测试文件仍低于 300 行理想阈值。
本轮只声明 Runtime deterministic verification，不声明 provider smoke、人类创意验收、
业务验证、公开发布、专利/法律判断或 COS active rule 晋升。

## Task

- Task ID: `AFS-T43`
- Branch: `codex/afs-goal-mode-main-loop-e2e-20260630`
- Mode: provider-closed Runtime regression
- Evidence state:
  `runtime_verified_multi_character_bridge_regression_no_provider_no_acceptance`

## What Changed

- Added `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py`.
- Parameterized `tests/runtime_main_loop_e2e_support.py` upload/promotion
  helpers for additional fixed character assets.
- No production Runtime behavior changed in this slice.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings
```

## Evidence Boundary

- Two fixed character assets reach bridge `context_evidence`.
- `reference_image_count=1` remains consistent with the provider descriptor
  slot limit.
- `provider_calls_started=false`.
- `safe_manifest.local_generation_bridge_ready=true`.
- `candidate_previews=[]`.
- `reusable_image_assets=[]`.
- Feedback overlay prompt inclusion remains blocked by default.

## Non-Claims

- Not provider smoke.
- Not a live provider call.
- Not generated media.
- Not human creative acceptance.
- Not business validation.
- Not public release or customer validation.
- Not patent/legal decision.
- Not COS active-rule promotion.

## Cleanup Review

| Target | Classification | Decision |
|---|---|---|
| `tests/runtime_main_loop_e2e_support.py` parameterization | keep | Reuses existing helper path for additional benchmark characters; file remains below 300 lines. |
| `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py` | keep | Focused provider-closed regression for two-character bridge evidence. |
| Runtime routes, OpenAPI, Studio UI, provider adapters | unchanged | Not touched in this slice. |
| `docs/demo-docs-20260629/` | defer/do-not-touch | Existing local untracked docs remain out of scope. |

## Next Valid Action

Continue provider-closed main-loop work while below branch threshold. The most
useful next slice is cleanup/redundancy classification for the current branch,
or a narrow request-plan/bridge consistency check for multi-shot continuity.
Do not open provider smoke, video, high-cost generation, external download,
public claim, human creative acceptance, business validation, patent/legal
decision, or COS active-rule promotion without explicit authorization.
