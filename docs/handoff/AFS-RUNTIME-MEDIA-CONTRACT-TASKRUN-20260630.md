# AFS 第三波 TaskRun Packet - Runtime Media Contract - 2026-06-30

## Task

Task ID: `AFS-T2b Runtime Media Contract`

本轮目标是在全量目标导向开发前，稳定 Runtime Service 与 `/studio/` 之间的媒体资产合同，
尤其是第二波暂缓的 `image-assets*` 边界。任务分类为 `Standard` 维护/合同任务。

本轮不是全量开发，不扩展生成能力，不打开 provider gate，不提交、不推送、不部署。

## Branch / Head / Status

- AFS repo: `D:\Projects\AgentFlowStudio`
- Branch: `master`
- HEAD: `ed292f6b752c9150e9a4b9a85fccdcfef5135b14`
- Tracking: `master...origin/master`
- GitHub/server sync: not performed in this TaskRun.
- Evidence state: `structure_verified`

## 中文维护摘要

本轮只处理 Runtime 与 Studio 之间已经实际使用的 `image-assets*` 媒体边界，不扩展生成能力，不把 provider 链路接入前端，也不把字节型接口匆忙提升为公共 OpenAPI。审计结论是：这些接口已经是 Studio-facing 的 Runtime 私有合同，必须被测试和记录治理；但由于上传请求包含浏览器侧 `data_base64`，预览路由会返回图片字节，且后续还需要单独决定公开下载、缓存、生命周期和鉴权语义，本轮继续保持 `include_in_schema=False` 更稳妥。

本轮新增的合同测试把当前最小边界固定下来：上传、列表、删除只能返回安全 JSON 元数据和明确的非声明字段；预览字节只能通过 Runtime preview route 返回，并带有 `content-type` 与 `Cache-Control: no-store`；OpenAPI snapshot 仍只代表当前公共控制面，`image-assets*` 不进入公共路径列表。这样做的目的不是隐藏真实依赖，而是在无人值守开发前先让“私有但已被 Studio 依赖”的接口有可回归的合同，避免后续前端实际依赖和文档/测试治理继续漂移。

风险边界也已重新核对：Studio 当前没有发现绕过 Runtime 直接接触 CLI/provider 的路径；持久化 state 只接受安全 Runtime preview refs；上传 payload 中的本地文件名会在 Runtime 侧收敛为 basename；JSON 响应不回显 `data_base64`、本地绝对路径、provider raw、signed URL 或媒体字节。本轮不清理历史不明目录，不处理服务器同步，不触碰 provider 配置，不把任何反馈自动晋升为 COS active rule。

## Dirty Ownership Ledger

| 分类 | 路径 / 表面 | 归属判断 |
|---|---|---|
| 既有第一/第二波记录 | `DEVLOG.md` | 保留既有内容，本轮只追加第三波记录。 |
| 既有第一/第二波记录 | `docs/handoff/INDEX.md` | 保留既有索引，本轮只追加第三波入口。 |
| 既有第一波记录 | `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md` | 不改写。 |
| 既有第二波记录 | `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md` | 不改写。 |
| 既有第二波成果 | `docs/openapi/afs-runtime-service.openapi.json` | 本轮未修改；仍为 49 paths，且不包含 `image-assets*`。 |
| 既有第二波成果 | `tests/test_api_runtime_openapi_snapshot.py` | 本轮未修改；继续防 OpenAPI snapshot 漂移。 |
| 本轮拥有 | `tests/test_api_runtime_media_contract.py` | 新增 Studio-facing private media contract 测试。 |
| 本轮拥有 | `tests/test_api_runtime_studio_state_persistence.py` | 修正既有结构化错误断言，符合当前 Runtime error contract。 |
| 本轮拥有 | `docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md` | 本文。 |
| 本轮拥有 | `AFS-Goal-Driven-Execution-State-v0.1.yaml` | 仅更新第三波任务状态和 next valid action。 |
| 既有未跟踪 | `docs/demo-docs-20260629/` | 本轮不读取、不清理、不提交。 |
| 既有 source-KB 脏状态 | `D:\Learning materials\Learning_notes` 其他修改 | 不 stage、不清理、不晋升。 |

## Read Scope

- `C:\Users\chenzy\.codex\skills\project-development-workflow\SKILL.md`
- `project-development-workflow` references: startup scan, verification, memory, architecture modules
- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md`
- `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_api_runtime_openapi_snapshot.py`
- `pyproject.toml`
- `apps/api/runtime_service.py`
- `apps/api/runtime_image_assets.py`
- `apps/api/runtime_models.py`
- `apps/api/runtime_auth_routes.py`
- `apps/api/runtime_studio_state_preview.py`
- `apps/api/runtime_studio_state_sanitizer.py`
- `apps/studio/src/runtime-client.js`
- `apps/studio/src/runtime-media-source.js`
- `apps/studio/src/runtime-asset-sync.js`
- `apps/studio/src/store-state.js`
- Studio upload, recovery, drawer, preview, and media render files found by `rg`

## Write Scope

- `tests/test_api_runtime_media_contract.py`
- `tests/test_api_runtime_studio_state_persistence.py`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md`
- `AFS-Goal-Driven-Execution-State-v0.1.yaml`

`docs/openapi/afs-runtime-service.openapi.json` was not changed in this TaskRun.

## image-assets* Current Facts

Studio currently uses `image-assets*` in four ways:

- Upload: `runtime.uploadImageAsset(payload)` sends `node_id`, `filename`, `mime_type`,
  `data_base64`, `role`, and `generated_at` to
  `POST /projects/{project_id}/image-assets`.
- List/recovery/sync: `runtime.listImageAssets()` reads
  `GET /projects/{project_id}/image-assets` for asset drawer sync and timed-out
  keyframe/image recovery.
- Preview/render/download: Studio stores and renders only Runtime preview refs such as
  `/projects/{project_id}/image-assets/{asset_id}/preview`. Protected Runtime media is
  fetched at render/download boundaries by `runtime-media-source.js` with the current
  auth token when needed.
- Delete: `runtime.deleteImageAsset(assetId)` calls
  `DELETE /projects/{project_id}/image-assets/{asset_id}` and clears Studio references.

Runtime currently provides:

- PNG/JPEG upload with 8 MB max and MIME/byte signature validation.
- Metadata file persisted under Runtime root, plus an artifact ref for metadata.
- Public JSON metadata: `asset_id`, `source_node_id`, `role`, sanitized basename
  `filename`, `mime_type`, `byte_count`, `sha256`, dimensions, `aspect_ratio`, and
  safe `preview_url`.
- Preview `FileResponse` with `content-type` from verified suffix and
  `Cache-Control: no-store`.
- Delete with runtime-root containment check and JSON flags
  `media_bytes_returned=false`, `provider_raw_response_stored=false`.
- Auth/project-owner protection through Runtime auth middleware when auth is enabled.

## Contract Judgment

`image-assets*` is already a Studio-facing Runtime contract. It should not remain an
unowned incidental endpoint.

For this stage, it should remain a private Studio Runtime media contract, not a public
OpenAPI contract. Reason:

- Upload request includes `data_base64`; that is a browser-to-local-Runtime transport
  detail, not a public API shape to expose broadly before media lifecycle is finalized.
- Preview endpoints intentionally return media bytes. Public OpenAPI currently tracks JSON
  control-plane contracts, while media byte routes need a separate public media contract
  decision.
- Existing Runtime behavior is same-origin/local/internal-beta oriented and protected by
  Runtime auth middleware when auth is enabled.
- Exposing these paths in OpenAPI now would expand public surface without first deciding
  upload lifecycle, byte retention, preview authorization, and download semantics.

The stable contract is therefore recorded and tested in
`tests/test_api_runtime_media_contract.py` plus this handoff. Promotion to public OpenAPI
should happen only in a later dedicated media API slice.

## Stable Private Contract

Input boundary:

- `POST /projects/{project_id}/image-assets`
- Required payload: `filename`, `mime_type`, `data_base64`, `generated_at`
- Optional payload: `node_id`, `role`
- Accepted media: PNG/JPEG only
- Max upload: 8 MB
- `filename` is reduced to a basename; no local path is returned.

JSON output boundary:

- Upload returns `asset`, `artifact`, `media_bytes_returned=false`,
  `provider_raw_response_stored=false`.
- List returns `{project_id, assets}` with the same public asset projection.
- Delete returns `{project_id, asset_id, deleted=true, media_bytes_returned=false,
  provider_raw_response_stored=false}`.
- JSON must not contain `data_base64`, original image bytes, local absolute paths,
  Runtime artifact paths, signed URLs, provider raw responses, or provider secrets.

Preview boundary:

- Preview refs are relative Runtime routes only.
- Valid preview refs match `/projects/{project_id}/image-assets/{asset_id}/preview`.
- Preview returns media bytes only through `FileResponse`.
- Preview must use verified `content-type` and `Cache-Control: no-store`.
- Studio state persistence only accepts safe Runtime preview routes and rejects signed
  URLs, external URLs, local paths, or cross-project preview refs.

OpenAPI boundary:

- `image-assets*` remains excluded from `docs/openapi/afs-runtime-service.openapi.json`.
- The OpenAPI path count remains `49`.
- Second-wave snapshot parity test continues to guard OpenAPI drift.

## Risk Review

No current evidence was found that the frontend receives provider raw responses, local
absolute paths, secrets, signed URLs, or generated media bytes in JSON.

Known safe mechanisms:

- Runtime public image asset metadata omits local filesystem path and raw bytes.
- Upload/list/delete JSON explicitly reports `media_bytes_returned=false` and
  `provider_raw_response_stored=false`.
- Preview bytes are only served by Runtime preview route, not embedded in JSON.
- Runtime auth middleware protects `/projects/*` media routes when auth is enabled.
- Studio media rendering centralizes authorized media fetches in `runtime-media-source.js`.
- Studio state sanitizer allows only Runtime preview refs for persistence.

## Changes Made

- Added `tests/test_api_runtime_media_contract.py`.
  - Confirms `image-assets*` stays out of public OpenAPI.
  - Confirms upload/list/delete JSON safe fields.
  - Confirms `data_base64`, local paths, Runtime artifact paths, and signed URL markers
    are not returned.
  - Confirms preview route content-type, `no-store`, and byte-return boundary.
- Updated `tests/test_api_runtime_studio_state_persistence.py`.
  - Replaced a stale string-detail assertion with the current structured Runtime error
    contract check for unsafe preview URL rejection.

No Runtime behavior, Studio behavior, or OpenAPI snapshot was changed.

## Deferred Items

- Public OpenAPI promotion for `image-assets*`, if needed, should be a dedicated media API
  contract slice with explicit request/response schemas and byte-route documentation.
- Decide whether uploaded display `filename` should remain stable public metadata or be
  replaced by a stricter `display_name` / `safe_label` projection.
- Add a higher-level browser smoke only when UI behavior changes; this TaskRun changed
  tests/records only.
- Full three-end sync should wait for an explicit commit/push/deploy task.

## Provider Gate State

- LLM: closed
- image: closed
- video: closed
- vision: closed
- ASR: closed
- external download: closed

No provider gate was opened and no live provider call was started.

## Verification

Completed:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_media_contract.py tests\test_api_runtime_auth.py::test_auth_enabled_projects_are_owner_scoped tests\test_api_runtime_studio_state_persistence.py::test_image_asset_list_returns_public_metadata_only tests\test_api_runtime_studio_state_persistence.py::test_studio_state_rejects_unsafe_preview_url tests\test_api_runtime_creative_agent_keyframes.py::test_uploaded_image_asset_can_be_deleted_from_project_runtime tests\test_web_studio_frontend_wave.py::test_runtime_media_urls_are_normalized_only_at_render_boundaries tests\test_web_studio_frontend_wave.py::test_runtime_media_source_caches_authorized_project_media_between_rerenders tests\test_web_studio_static.py::test_studio_keeps_flow_native_canvas_controls -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_media_contract.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed; CLI help rendered

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; warnings remain:
# legacy_frozen_surface=10, human_doc_chinese_coverage=22, secret_like_fragments=9 high_confidence_count=0, oversized_files=59
# The third-wave handoff is no longer flagged by human_doc_chinese_coverage after the Chinese maintenance summary.

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## Cleanup Review

- Keep: private Studio Runtime media contract tests.
- Keep: structured error assertion repair.
- Keep: third-wave TaskRun packet, DEVLOG, and handoff index updates.
- Defer: public OpenAPI promotion of byte-bearing `image-assets*` routes.
- Defer: pre-existing `docs/demo-docs-20260629/`.
- Defer: pre-existing source-KB dirty state outside execution state file.

## Next Valid Task

Recommended next task: `AFS-T3 Goal-Mode Readiness Gate` or equivalent, to decide whether
to commit/push/deploy the first three waves and then enter full Codex goal-driven execution
with a clean sync baseline.

Do not start broad unattended development until the current local dirty wave is either
committed/synced or explicitly accepted as the baseline dirty ledger for the next wave.
