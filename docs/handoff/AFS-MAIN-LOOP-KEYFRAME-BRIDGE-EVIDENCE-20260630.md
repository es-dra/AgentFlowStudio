# AFS Main Loop Keyframe Bridge Evidence

## 中文摘要

本轮对应 `AFS-T42`，目标不是打开真实图片生成，也不是扩展 Studio
界面，而是在 provider 关闭的条件下，把上一轮真实基准剧本闭环继续推进到
关键帧生成桥。验证路径仍然使用 `multi_scene_map_chase`：真实剧本先经过
storyboard/content quality、Production Graph、Evidence Ledger、Human Gate、
Feedback Candidate 和反馈 overlay，再进入 keyframe preflight，最后提交到
`/keyframe-generations`。由于远程 image gate 未授权，作业按预期停在
`blocked`，但 Runtime 仍会写出本地 deterministic bridge artifact。

红线结果证明原有 bridge 只记录了上下文存在、固定资产数量和反馈 overlay
ID，没有记录固定资产的安全来源证据。因此本轮只在既有
`generation_bridge.context_evidence` 中补充安全摘要：
`included_asset_source_evidence_refs`。该摘要只包含固定资产 id、资产类型、
标签、状态、来源 human-gate id、来源 asset-card candidate id 和非声明布尔值；
不包含 provider raw、signed URL、本地私有路径、媒体字节、secret、客户材料或真实成本。

本轮清理点是测试结构而不是产品功能：原来的 T41 E2E 文件已经接近 300 行，
所以抽出 `tests/runtime_main_loop_e2e_support.py` 作为共享测试准备模块，避免
T42 复制同一套基准剧本、固定资产、反馈 overlay 和 preflight 构造逻辑。所有
新增或改动的测试文件仍低于单文件 300 行理想阈值。本轮验证只证明 Runtime
安全输入和 blocked evidence 链路正确，不声明 provider smoke、生成媒体、人类创意验收、
业务验证、公开发布、专利/法律判断或 COS active rule 晋升。

## Task

- Task ID: `AFS-T42`
- Branch: `codex/afs-goal-mode-main-loop-e2e-20260630`
- Base branch: `origin/master`
- Mode: provider-closed Runtime E2E regression
- Evidence state:
  `runtime_verified_blocked_keyframe_bridge_evidence_no_provider_no_acceptance`

## Objective

Extend the real benchmark main-loop harness from preflight into the blocked
local keyframe generation bridge:

```text
real script -> storyboard/content quality -> fixed asset reuse
  -> production graph -> evidence ledger -> human gate
  -> feedback candidate -> feedback overlay -> keyframe preflight
  -> blocked keyframe generation bridge
```

The goal is to prove that safe context, fixed-asset source evidence, human-gate
lineage, and feedback overlay evidence reach the generation bridge input while
remote image generation remains blocked.

## What Changed

- Added `tests/runtime_main_loop_e2e_support.py` as shared setup for the real
  `multi_scene_map_chase` E2E path.
- Refactored `tests/test_api_runtime_main_loop_e2e.py` to use the shared setup
  instead of carrying duplicated setup helpers.
- Added `tests/test_api_runtime_main_loop_keyframe_bridge_e2e.py`.
- Updated `agentflow.algorithms.generation_bridge` so
  `context_evidence.included_asset_source_evidence_refs` carries the safe fixed
  asset source-evidence digest.

## Red / Green

Red baseline:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py -q
# failed: KeyError 'included_asset_source_evidence_refs'
```

Green:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning
```

Focused adjacent set:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 5 passed, 1 warning
```

Full local verification:

```text
.\.venv\Scripts\python.exe -m pytest
# 772 passed, 520 deselected, 2 warnings
```

## Evidence Boundary

- Provider gates remained closed by environment.
- The keyframe job status is `blocked`.
- `provider_calls_started=false`.
- `candidate_previews=[]` and `reusable_image_assets=[]`.
- Bridge planned outputs stay `artifact_state=planned` and
  `media_bytes_available=false`.
- Feedback overlays remain context evidence only:
  `provider_prompt_includes_context_overlays=false`.

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
| `tests/runtime_main_loop_e2e_support.py` | keep | Shared setup removes duplication between T41 and T42 while staying under 300 lines. |
| `tests/test_api_runtime_main_loop_e2e.py` | keep/refactored | Same baseline assertions, smaller file, no behavior removed. |
| `tests/test_api_runtime_main_loop_keyframe_bridge_e2e.py` | keep | Focused T42 regression for blocked bridge evidence. |
| `agentflow.algorithms.generation_bridge` source-evidence digest | keep | Additive safe bridge evidence; no route, provider, or schema expansion. |
| Runtime routes, OpenAPI, Studio UI, provider adapters | unchanged | Not touched in this slice. |
| `docs/demo-docs-20260629/` | defer/do-not-touch | Existing local untracked docs remain out of scope. |

No generated media, provider raw output, secrets, customer material, real costs,
or private media bytes were added.

## Next Valid Action

Continue on the same branch while the branch remains below merge threshold.
Valid next slices:

- add a second real benchmark case stressing multi-character asset handoff;
- tighten bridge/request-plan evidence for a specific multi-shot continuity
  case;
- classify current-wave redundancy before the next threshold review.

Do not open provider smoke, video, high-cost generation, external download,
public claim, human creative acceptance, business validation, patent/legal
decision, or COS active-rule promotion without explicit authorization.
