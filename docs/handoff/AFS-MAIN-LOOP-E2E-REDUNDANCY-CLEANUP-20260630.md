# AFS Main Loop E2E Redundancy Cleanup - 2026-06-30

中文摘要：本交接记录 AFS-T44 的 provider-closed 维护切片。本轮没有新增生成能力，
而是把 T41-T43 当前分支里重复的 Runtime E2E 测试编排收进共享 helper，保留真实
基准剧本、fixed asset、feedback overlay、human-gate/source-evidence 和 blocked
keyframe bridge 的证据链。

## 范围

- 分支：`codex/afs-goal-mode-main-loop-e2e-20260630`
- 任务：AFS-T44 当前波次冗余分类与清理
- 产品线：AFS 本地 MVP 主闭环，provider 默认关闭
- 写入范围：
  - `tests/runtime_main_loop_e2e_support.py`
  - `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py`
  - 项目记录和 handoff index

## 清理分类

- 保留：T41-T43 的行为断言、真实 benchmark case、source-evidence 检查、
  blocked provider evidence、unsafe-marker 断言，以及 no-media 非声明边界。
- 迁移：重复的 storyboard breakdown、feedback candidate promotion、
  feedback context overlay creation 和 keyframe preflight 编排，统一进入可参数化
  共享 helper。
- 删除：多角色 bridge 回归里已经被替代的 per-test `_storyboard_breakdown` 和
  `_feedback_overlay` helper。
- 暂缓/不触碰：`docs/demo-docs-20260629/` 仍是既有未跟踪目录，本轮不 stage、
  不清理、不改写。

## 结果

- `tests/runtime_main_loop_e2e_support.py` 现在提供 `storyboard_breakdown`、
  `create_feedback_context_overlay` 和 `keyframe_preflight`。
- 共享 support 保持在项目理想行数线以内：299 行。
- `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py` 降到 178 行，
  仍然证明两个 fixed character asset 会进入 blocked bridge source evidence。
- 本轮净效果是减少当前波次测试重复，不扩大 Runtime/OpenAPI/Studio/API/provider
  面。

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py
# 3 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 5 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 773 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

## 非声明边界

- 没有 provider smoke。
- 没有 live provider call。
- 没有 generated media。
- 没有 Runtime route 或 OpenAPI path expansion。
- 没有 Studio UI change。
- 没有人类创意验收声明。
- 没有 business validation、public claim、patent/legal decision 或 COS active
  rule promotion。

## 下一步

继续运行 maintenance audit、diff check、YAML/state parse 和 branch integration
review。若所有 gate 继续为绿灯且分支未达到 merge-review threshold，则提交并 push
当前分支；若达到预期阈值，则按 standing integration authorization 处理，不把预期
gate 记为 blocker。
