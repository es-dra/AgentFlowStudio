# AFS-KLING-PREFLIGHT-001 Handoff

中文摘要：本切片把 Studio 项目持久化、刷新后图片复显、ProviderDescriptor v0.2、Kling I2V registry adapter、Runtime video API 和 Studio 显式首帧入口落到同一条 MVP 前置链路。真实 Kling key 没有进入 tracked 文件、trace、manifest 或 API 响应。

中文状态：工程链路已经完成到可本地验证的 preflight 层。项目列表、新建项目、项目级本地缓存、图片 safe preview 复显、Runtime 图片资产列表、视频节点显式首帧、video gate、fake async submit/poll/preview 都有测试覆盖。用户提供的外部 `.secrets` provider 配置已通过安全 preflight，确认存在 `kling_i2v`、AK/SK presence 和 JWT self-check。真实 Kling live submit 尚未执行，原因是当前 shell 的 `AFS_ALLOW_REMOTE_VIDEO` 仍为关闭状态，且本切片没有把 provider smoke 升级为人工验收。

中文边界：本次没有声明人工验收、商业验证或视频质量有效性。fake video 只证明异步 contract，不能当作 Kling provider smoke。所有视频媒体字节仍只能通过 Runtime preview 端点读取，API 响应不返回本地路径、provider URL、授权头或原始响应。

## Completed

- Added `GET /projects` with `studio_state.meta` summary.
- Added `GET /projects/{project_id}/image-assets` public metadata list.
- Allowed Studio state to persist safe relative `previewUrl` values for Runtime preview endpoints only.
- Added project-scoped localStorage cache and topbar project selector/new-project action.
- Hydrates image previews from `previewUrl` or `params.uploads[-1].preview_url` after refresh.
- Syncs Runtime image assets and fixed visual assets into the drawer after project load.
- Split context resolver into subgraph, assets, and text modules while keeping `runtime_context_resolver` as the public facade.
- Moved provider retry dispatch into `apps/api/runtime_provider_dispatch.py`.
- Extended `ProviderDescriptor` to v0.2 video fields.
- Added `KlingVideoAdapter` registry target for `kling_i2v` using existing Kling runtime/smoke modules.
- Added Runtime video routes for submit, poll, cancel, and candidate preview.
- Added Studio video node flow: upload image, explicitly set first/last frame, submit Kling I2V.
- Added `tools/kling_provider_preflight.py` safe readiness checker.
- Added `docs/provider_adapter_v02_video_addendum.md`.

## Verification

```text
tests/test_api_runtime_studio_state_persistence.py: 4 passed
tests/test_provider_adapter_registry.py: 18 passed
tests/test_api_runtime_video_generations.py: 4 passed
Resolver/keyframe/visual asset focused set: 18 passed
Keyframe focused set: 11 passed
Combined focused set: 63 passed, 1 warning
Full pytest: 868 passed, 2 warnings
Studio JS node --check for all apps/studio/src JS files: passed
Project browser QA on 127.0.0.1:8791/studio/: passed
Focused Studio persistence/static rerun after browser fix: 16 passed, 1 warning
tools/maintenance_audit.py: failed=0, warning=2
git diff --check: passed with CRLF warnings only
```

Browser QA covered opening Studio, project selector render, new project creation, URL query sync, `localStorage.afs_studio_active_project_id`, reload persistence, and selector state after reload.

## Current Live State

`tools/kling_provider_preflight.py` can run against the external secret config without leaking secrets:

```text
AFS_PROVIDER_CONFIG=<external .secrets providers.local.json>
status: ready
service_id: kling_i2v
descriptor_schema_version: provider_descriptor.v0.2
prompt_profile: video_i2v_v1
credential_presence: access_key_present=true, secret_key_present=true
jwt_self_check: available=true, token_segments=3
gate: AFS_ALLOW_REMOTE_VIDEO enabled=false
secrets_printed=false
```

The repo-local ignored `configs/providers.local.json` still only exposes MiniMax services; use the external secret config via `AFS_PROVIDER_CONFIG` for Kling live work unless a local ignored copy is intentionally created outside tracked files.

## Boundaries

- No live Kling submit was run.
- `AFS_ALLOW_REMOTE_VIDEO` remains a capability-specific gate.
- The Runtime video safe manifest does not store provider raw response, authorization headers, signed provider URLs, local absolute paths, or media bytes.
- Fake async video is a contract path only, not provider smoke or creative-quality validation.
- The current `KlingVideoAdapter` reuses the existing smoke/runtime path as the first registry target; before long-running live acceptance, the next hardening step should make submit/poll fully nonblocking for real Kling tasks instead of relying on the smoke wrapper behavior.

## Next Live Steps

1. Start Runtime with `AFS_PROVIDER_CONFIG` pointing at the external secret config and `AFS_ALLOW_REMOTE_VIDEO=true`.
2. Open Studio, upload a first-frame image on a video node, set it as first frame, then submit.
3. Poll until the Runtime job reaches `succeeded` or a recoverable failure state.
4. Record human scoring separately; provider smoke is not human acceptance.
