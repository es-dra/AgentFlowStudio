# AFS 第十三波 TaskRun - Keyframe Local Generation Bridge - 2026-06-30

## 任务

Task ID：`AFS-T8 Generation Path`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`71060697c7e5d9ddd95e19d1f49a900245d0b655`

本轮目标是在 provider gate 关闭的前提下，为图片/关键帧生成路径补一个 fake/local deterministic bridge。

该 bridge 只证明 Runtime 已形成可审计的生成请求链路：model context、request plan、safe manifest、provider gate 和 planned candidate ids。它不生成媒体、不调用 provider、不冒充生成成功。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/generation_bridge/__init__.py` | 本轮 T8 合同实现 | 保留，单职责构建 gate-closed keyframe local bridge。 |
| `agentflow/algorithms/__init__.py` | 本轮算法注册 | 保留，将 `generation_bridge` 纳入算法模块清单。 |
| `apps/api/runtime_keyframes.py` | 本轮 Runtime additive integration | 保留，在 provider 未启动时写入 bridge artifact。 |
| `apps/api/runtime_keyframe_routes.py` | 本轮 response additive field | 保留，keyframe submit response 暴露 `generation_bridge`。 |
| `apps/api/runtime_artifacts.py` | 本轮 artifact 注册 | 保留，仅当 bridge 文件存在时注册，兼容旧 run。 |
| `tests/test_api_runtime_keyframe_generation_bridge.py` | 本轮 focused regression | 保留，覆盖算法注册、gate-closed Runtime payload、artifact 读取和 unsafe marker。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 合同判断

当前 keyframe generation 在 image provider gate 关闭时本来会返回 `status=blocked`，并写入 request plan、candidate summary、safe manifest。

本轮补齐的合同是：

- `status` 仍为 `blocked`。
- `provider_calls_started=false`。
- `safe_manifest.local_generation_bridge_ready=true`。
- 新增 artifact `keyframe_generation_bridge.json`。
- bridge 内只记录安全引用、上下文计数、planned candidate ids、provider gate 和 non-claims。

bridge 不是：

- provider smoke。
- 真实图片生成。
- candidate preview。
- fixed asset memory。
- human acceptance。
- business validation。
- durable memory promotion。

## 本轮改动

- 新增 `agentflow.algorithms.generation_bridge`。
- 新增 `build_keyframe_generation_bridge(...)`，输出：
  - `artifact_type=agentflow_generation_bridge`
  - `bridge_stage=keyframe_local_deterministic_bridge`
  - `summary.generation_state=blocked_before_provider`
  - `planned_outputs[]`，使用 deterministic `planned_candidate_001` 等 id。
  - `provider_evidence`，记录 gate、blocks、no raw/no media/no private link。
  - `request_evidence`，记录 model/request/safe manifest artifact refs。
- Runtime keyframe submit 在 `provider_calls_started=false` 时写入并返回 bridge。
- `runtime_artifacts.keyframe_generation_artifacts(...)` 只在 bridge 文件存在时注册该 artifact，避免旧 keyframe run 或 async poll 路径因缺文件失败。
- bridge artifact 写入逻辑位于 `apps/api/runtime_keyframe_generation_bridge.py`，避免把新合同主体继续堆进既有 oversized 的 `runtime_keyframes.py`。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_keyframe_generation_bridge.py
# 预期失败：缺少 generation_bridge 算法模块和 Runtime payload。
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_generation_manifest_safety.py
# 4 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py::test_generate_context_uses_connected_fixed_assets_and_lock_overrides tests\test_api_runtime_context_resolver.py::test_generate_context_uses_label_matched_fixed_assets_without_edges tests\test_api_runtime_context_resolver.py::test_context_bundle_reproducibility_metadata_is_deterministic tests\test_api_runtime_asset_card_drafts.py::test_asset_card_draft_gate_closed_blocks_before_provider_and_stays_safe
# 4 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 701 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings remain existing categories: legacy_frozen_surface,
# human_doc_chinese_coverage, secret_like_fragments, oversized_files.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T8
```

## 证据状态

当前本轮 focused evidence state：

```text
structure_verified_keyframe_local_generation_bridge
```

这不是 provider smoke，不是 generated media evidence，不是 human acceptance，不是 fixed asset promotion，不是 business validation，不是部署验证，也不是服务器三端同步。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| `generation_bridge` 算法包 | keep | 单职责 deterministic bridge，避免把 T8 合同塞进 provider adapter。 |
| Runtime keyframe additive bridge | keep | 只在 provider 未启动时写 bridge，不改变 provider dispatch 行为。 |
| `apps/api/runtime_keyframe_generation_bridge.py` | keep | 将 bridge 写入从既有 oversized keyframe 模块中拆出。 |
| conditional artifact registration | keep | 兼容旧 run 和 async poll 路径。 |
| focused bridge test | keep | 覆盖 T8 最小合同，未加到已有 oversized tests。 |
| provider, Studio UI, OpenAPI | unchanged | 本轮不触达。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、secret、客户材料、真实成本或私有素材字节。

## 下一步

推荐下一任务：

```text
AFS-T10 Human Gate for Asset and Keyframe Confirmation
```

原因：T8 的 gate-closed generation bridge 已把 keyframe request 链路接上。下一步应让资产卡候选、生成计划和后续结果进入明确的人类确认状态机，而不是继续只增加生成侧 artifact。
