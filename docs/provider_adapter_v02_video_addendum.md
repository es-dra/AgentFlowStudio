# Provider Adapter v0.2 Video Addendum

中文摘要：本增量文档定义视频 provider 的 v0.2 能力描述符。它把 Kling 图生视频需要的首帧/尾帧槽位、异步轮询、时长、分辨率、成本提示和 prompt profile 写成公开 contract。真实密钥只能保存在 ignored 本地配置或环境变量中，不能进入仓库、trace、manifest、OpenAPI 或前端响应。Studio 只能通过 Runtime video API 调用视频能力，前端不能直接调用 CLI、smoke helper 或 provider SDK。

验收边界：`first_frame_image_asset_id` 是必填字段。Runtime 只能按项目内 image asset id 解析首帧，不能接受本地路径。`AFS_ALLOW_REMOTE_VIDEO` 是独立 gate；图片、LLM 或 ASR 授权都不代表视频授权。safe manifest 只能保存状态、候选 id、字节数和哈希等安全摘要，不保存 provider raw、授权头、signed URL、本地绝对路径或媒体字节。

This addendum extends `docs/provider_adapter_contract.md` for Kling I2V and
future async video providers. It does not change the v0.1 image or LLM contract.

## Descriptor Fields

`provider_descriptor.v0.2` adds:

- `frame_slots`: `first_frame` must be `required`; `last_frame` may be `optional`.
- `frame_modes`: supported frame modes, for example `first_frame` and `first_last_frame`.
- `supported_durations_sec`: positive provider duration values.
- `supported_resolutions`: public resolution labels such as `720p`.
- `async_poll_interval_sec`, `async_timeout_sec`, `async_max_polls`: async polling contract.
- `prompt_profile`: provider prompt profile. Kling I2V uses `video_i2v_v1`.
- `cost_estimate`: safe estimate metadata only; no secret, account term, or private commercial note.

## Kling I2V

`kling_i2v` is represented in `configs/providers.example.json` as a registry
adapter target. The example config uses env-var names only. Real AK/SK values
must stay in ignored local config or environment variables.

Legacy local configs that already contain `kling_i2v` but do not yet include a
descriptor may be read through the registry compatibility layer. The compatibility
path only derives conservative public descriptor metadata; it does not expose,
copy, or persist credentials.

## Prompt Profile

`video_i2v_v1` treats the first frame as the primary identity constraint. Text
should prioritize action, timing, camera movement, and continuity. Connected
visual assets may contribute signatures and key locks, but long feature cards
should not be injected into the video prompt.
