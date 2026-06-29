# AFS 第二波 TaskRun Packet - Runtime Contract - 2026-06-30

## Scope

本轮执行 `AFS-T2 Runtime Contract`。目标是审计并收敛 Runtime Service、OpenAPI
快照和 Studio client 的合同一致性，只做低风险、可验证的维护修复。

本轮不是全量开发线程，不新增产品能力，不打开 provider gate，不提交、不推送、不部署。
`AFS-T1 Product Scope` 仅作为只读防偏移上下文。

## Startup Scan

已按项目规则执行 startup scan，并读取：

- `AGENTS.md`
- `README.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/GFR_EXECUTION_PROJECTION.md`
- 2026-06-30 AFS project-book package
- `apps/api/runtime_service.py`
- `docs/openapi/afs-runtime-service.openapi.json`
- `apps/studio/` Runtime client and safe media boundary

任务分类：`Standard`，带 Runtime/OpenAPI 合同风险审计。

## Dirty Ownership Ledger

| 分类 | 路径 / 表面 | 归属判断 |
|---|---|---|
| 既有第一波记录 | `DEVLOG.md` | 保留第一波记录，本轮只追加第二波条目。 |
| 既有第一波记录 | `docs/handoff/INDEX.md` | 保留第一波索引，本轮只追加第二波入口。 |
| 既有第一波记录 | `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md` | 不改写。 |
| 既有未跟踪 | `docs/demo-docs-20260629/` | 本轮不读取、不清理、不提交。 |
| 本轮拥有 | `docs/openapi/afs-runtime-service.openapi.json` | 由项目现有 exporter 重新生成。 |
| 本轮拥有 | `tests/test_api_runtime_openapi_snapshot.py` | 新增 OpenAPI 快照一致性合同测试。 |
| 本轮拥有 | `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md` | 本文。 |
| 本轮拥有 | `AFS-Goal-Driven-Execution-State-v0.1.yaml` | 仅更新第二波状态和清理分类。 |
| 既有 source-KB 脏状态 | `D:\Learning materials\Learning_notes` 其他修改 | 不 stage、不清理、不晋升。 |

## Runtime Contract Findings

### Fixed

默认 Runtime app 现场 schema 与仓库 OpenAPI 快照不一致：

```text
before:
live_paths=49
snapshot_paths=34
missing_paths=15

after:
live_paths=49
snapshot_paths=49
schema_equal=True
missing_paths=0
stale_paths=0
```

缺失路径集中在：

- `/studio/client-events`
- `DELETE /projects/{project_id}`
- `/projects/{project_id}/storyboard-breakdowns`
- `/projects/{project_id}/shot-asset-plans`
- `/projects/{project_id}/sprite/chat`
- `/projects/{project_id}/sprite/memory*`
- `/community/requests*`

处理方式：

- 使用 `runtime-service-openapi-export` 重新生成 OpenAPI 快照。
- 新增 pytest 合同测试，要求默认 Runtime exporter 输出与已提交快照完全一致。

### Verified Safe

Studio 源码级 `fetch(` 只出现在两处：

- `apps/studio/src/runtime-client.js`
- `apps/studio/src/runtime-media-source.js`

`runtime-client.js` 统一通过 Runtime base URL 请求 JSON API；`runtime-media-source.js`
只对 Runtime origin 下的 `/projects/` 媒体预览补带授权头。未发现 Studio 源码直接调用
CLI、provider secret、signed URL、provider raw response、本地绝对路径或 provider
内部实现。

Studio state 持久化只保留受白名单约束的 Runtime preview route；非 Runtime preview
不会写回长期 Studio state。

### Deferred

`/projects/{project_id}/image-assets*` 是 Studio 正在使用的 Runtime endpoint，但当前
Runtime 代码明确 `include_in_schema=False`。这些接口承载用户显式选择的图片上传和
预览字节返回路径，现有响应已经避免返回本地路径、provider raw response 和 media bytes
in JSON。

本轮不把它顺手加入公开 OpenAPI，因为这会改变当前公共 API 暴露面。后续如果要把上传、
列表、删除、预览纳入正式 OpenAPI，应单独做一个 Runtime media contract slice，明确：

- base64 上传字段是否属于公开 OpenAPI 合同。
- preview `FileResponse` 的 auth、cache、content-type 和 byte boundary。
- Studio client、OpenAPI、auth tests、safe manifest 的共同合同。

## Files Changed

- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_api_runtime_openapi_snapshot.py`
- `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `AFS-Goal-Driven-Execution-State-v0.1.yaml`

## Verification

Completed:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_service_v02.py::test_runtime_service_v02_routes_are_hidden_by_default tests\test_api_runtime_storyboard_breakdown.py::test_storyboard_breakdown_is_exported_without_secret_surface tests\test_api_runtime_sprite.py::test_sprite_chat_falls_back_to_local_rules_when_llm_gate_closed tests\test_web_studio_prompt_script_static.py::test_storyboard_asset_identification_uses_runtime_plan_and_allows_manual_asset_nodes tests\test_web_studio_sprite_static.py::test_studio_sprite_widget_is_wired_to_runtime_chat -q
# 6 passed, 1 existing warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; status=warning; passed=3; warning=4
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22, all tracked
# secret_like_fragments=9, high_confidence_count=0
# oversized_files=59, tracked=57, untracked=2

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# current_task_id=AFS-T2
# cleanup_status=completed_for_second_wave_runtime_contract_records
# feedback_status=none_needed_for_second_wave
```

## Cleanup Review

- Keep: regenerated OpenAPI snapshot.
- Keep: OpenAPI snapshot parity test.
- Keep: second-wave TaskRun packet and index/devlog records.
- Defer: pre-existing `docs/demo-docs-20260629/`.
- Defer: pre-existing source-KB dirty state outside execution state file.
- Defer: image-assets OpenAPI exposure decision to a dedicated media contract slice.

## Evidence Boundary

- Provider gates remained closed.
- No live provider call, external download, video generation, ASR, commit, push, deploy, or server sync was performed.
- This is structure/contract verification, not Runtime health verification, provider smoke, human acceptance, business validation, or durable memory promotion.
