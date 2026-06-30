# AFS 第十四波 TaskRun - Runtime Human Gate Contract - 2026-06-30

## 任务

Task ID：`AFS-T10 Human Gate for Asset and Keyframe Confirmation`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`9a47869482faf7b8f1e1dbd4352681f1356aa532`

本轮目标是在不打开 provider gate、不生成媒体、不扩展 UI 状态机的前提下，为 asset-card candidate 和 keyframe local generation bridge 补一个可记录、可审计、可测试的 Runtime human gate contract。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/human_gate/__init__.py` | 本轮 T10 合同实现 | 保留，单职责构建安全 human gate decision event。 |
| `agentflow/algorithms/__init__.py` | 本轮算法注册 | 保留，将 `human_gate` 纳入算法模块清单。 |
| `apps/api/runtime_models.py` | 本轮 Runtime request schema | 保留，新增 `HumanGateDecisionRequest`，限制目标类型和决策枚举。 |
| `apps/api/runtime_human_gate.py` | 本轮 Runtime route | 保留，新增公开 `/projects/{project_id}/human-gate-decisions`。 |
| `apps/api/runtime_service.py` | 本轮 route registration | 保留，只增加 import 和 route 注册。 |
| `apps/studio/src/runtime-client.js` | 本轮 Studio client contract | 保留，新增 `recordHumanGateDecision(payload)` 和 request meta action。 |
| `docs/openapi/afs-runtime-service.openapi.json` | 本轮 public contract snapshot | 保留，由 exporter 生成；path 数从 49 增至 50。 |
| `tests/test_api_runtime_human_gate.py` | 本轮 focused regression | 保留，覆盖 asset candidate、keyframe bridge、unsafe note 拒绝。 |
| `tests/test_web_studio_assets_generation_static.py` | 本轮 Studio static contract guard | 保留，防止 Runtime route 与 Studio client 漂移。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 合同判断

T10 的 human gate 不是最终人类创意验收，也不是业务验收。它是 Runtime 与 Studio 之间的本地步骤 gate：

- 对 `asset_card_candidate`，只记录候选资产卡是否可进入下一步本地 drafting 或需要修订。
- 对 `keyframe_generation_bridge`，只记录 gate-closed generation bridge 是否可进入下一步请求准备或需要修订。
- `accepted_for_next_step` 不会自动 fixed asset promotion。
- `needs_revision` / `rejected` 会记录 `blocks_provider_step=true`。
- 所有决策都保持 `provider_calls_started=false`、`opens_provider_gate=false`、`promotes_fixed_asset=false`、`requires_separate_promotion=true`。

公开 Runtime contract：

```text
POST /projects/{project_id}/human-gate-decisions
```

请求最小字段：

- `target_type`: `asset_card_candidate` 或 `keyframe_generation_bridge`
- `target_id`
- `decision`: `accepted_for_next_step`、`needs_revision`、`rejected`
- `artifact_id`
- `node_id`
- `scope`
- `note`
- `reviewed_at`

输出 artifact：

```text
artifact_type=agentflow_runtime_human_gate_decision
role=runtime_human_gate_decision
```

## 安全边界

本轮 route 先对原始 request 做 unsafe payload reject，再构建 safe event。event 不保存：

- provider raw response。
- signed/private external link。
- local absolute path。
- media bytes。
- secret/token/cookie。

event 中的 `safety_boundary` 使用 `raw_provider_response_stored=false`、`external_private_link_stored=false`、`absolute_path_stored=false`、`media_bytes_stored=false`，避免把 `signed_url` 等 forbidden literal 写入 artifact。

## 本轮改动

- 新增 `agentflow.algorithms.human_gate`。
- 新增 `build_human_gate_decision(...)`，输出安全 human gate event、non-claims 和 promotion/provider 边界。
- 新增 Runtime route `register_runtime_human_gate_routes(...)`：
  - 写入 `runtime_human_gate_decision.json`。
  - 注册 artifact role `runtime_human_gate_decision`。
  - 写入 run trace。
  - 更新 project manifest `feedback_refs`。
- 新增 Studio Runtime client 方法 `recordHumanGateDecision(payload)`，但不新增 UI。
- 更新 OpenAPI snapshot，新增公开 path。
- 新增 focused tests 和 Studio static contract guard。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py -q
# 预期失败：3 failed，route 尚未注册，返回 404。
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py -q
# 预期失败：新增 public path 后 committed snapshot 漂移。

OpenAPI exporter
# before_paths=49
# after_paths=50
# added_paths=['/projects/{project_id}/human-gate-decisions']

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_human_gate.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_feedback.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_web_studio_assets_generation_static.py::test_mvp_experience_hardening_video_status_and_feedback_markers -q
# 10 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout verification:

```text
.\.venv\Scripts\python.exe -m pytest
# 704 passed, 520 deselected, 2 warnings

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
# secret_like_fragments remains at 9 after removing the initial unsafe-test literal.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T10
```

## 证据状态

当前本轮 evidence state：

```text
structure_verified_runtime_human_gate_contract
```

这不是 provider smoke，不是 generated media evidence，不是 human creative acceptance，不是 fixed asset promotion，不是 business validation，不是部署验证，也不是服务器三端同步。

## Cleanup Review

- 未清理 `docs/demo-docs-20260629/`。
- 未读取或提交 secret、provider key、signed URL、cookie、token、本地私有素材字节、provider raw response 或生成媒体字节。
- 没有打开 LLM/image/video/vision/ASR provider gate。
- 没有部署、没有服务器同步、没有 Runtime restart。
- 新增 Runtime 逻辑放在 `apps/api/runtime_human_gate.py`，没有继续把合同主体塞进 `runtime_service.py`。
- 公开 OpenAPI path 是本轮 contract 选择，不是隐式漂移；snapshot 已由 exporter 重建，并由 snapshot test 防漂移。

## Deferred Items

- Studio 还没有 human gate UI。下一步 UI 应复用 `recordHumanGateDecision(payload)`，不要绕过 Runtime。
- `asset_card_candidate` accepted 后是否进入 fixed visual asset promotion，需要单独 T11/T12 任务定义，不由 T10 自动处理。
- `keyframe_generation_bridge` accepted 后是否允许 provider smoke，仍需显式 provider gate 授权。
- 现有 `/feedback` route 仍在 `runtime_service.py` 内；本轮不拆旧逻辑，避免扩范围。

## 下一步

建议下一步任务：

```text
AFS-T11 Studio Human Gate UI Hook
```

目标是把 asset-card candidate / keyframe bridge 的人类 gate 决策接到 Studio 的最小确认入口，同时继续保持 provider gate closed、no fixed asset promotion without explicit route、no human/business validation claim。
