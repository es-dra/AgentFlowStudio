# AFS Multi-Shot Request Plan Bridge Consistency - 2026-06-30

中文摘要：本交接记录 AFS-T45 的 provider-closed 一致性切片。本轮不新增生成能力，
只验证真实多角色基准路径中 request plan 的 context bundle 与 blocked generation
bridge evidence 保持同一组 fixed asset、source evidence 和 feedback overlay。

## 范围

- 分支：`codex/afs-goal-mode-main-loop-e2e-20260630`
- 任务：AFS-T45 request-plan/bridge consistency check
- 写入范围：
  - `tests/test_api_runtime_multi_character_keyframe_bridge_e2e.py`
  - 项目记录和 handoff index

## 变更

- 多角色 bridge 回归现在读取 `keyframe_request_plan` artifact。
- 测试验证 request plan context bundle 的 fixed asset ids 与 bridge
  `included_asset_source_evidence_refs` 的 asset ids 一致。
- 测试验证 request plan context bundle 的 source asset-card candidate ids 与
  bridge source evidence 一致。
- 测试验证 feedback overlay id 同时出现在 request plan context bundle 和 blocked
  bridge context evidence。
- request plan context bundle 也进入 unsafe marker 检查，继续禁止 provider raw、
  signed URL、base64 media bytes 和本地绝对路径泄漏。

## 验证

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py -q
# 1 passed, 1 warning

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
- 没有 Runtime route、OpenAPI path 或 Studio UI 扩展。
- 没有人类创意验收、business validation、public claim、patent/legal decision 或
  COS active rule promotion。

## 下一步

运行 maintenance audit、diff check、YAML/state parse 和 branch integration review。
若分支仍低于阈值，可继续 provider-closed 小切片；若达到预期阈值，则按 standing
integration authorization 处理。
