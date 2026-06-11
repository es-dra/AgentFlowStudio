# AFS MiniMax 文本增强与关键帧接入交接

日期：2026-06-12
负责人角色：Runtime/API Integrator + Provider Gate Steward
分支：`codex/afs-minimax-text-image-integration`

## 范围

本交接记录内部 Studio MVP 之后的第一条真实 provider smoke 路径：

- MiniMax-M3 用于节点提示词优化后的二次增强。
- MiniMax `image-01` 用于图片/关键帧生成。
- Studio 只保留当前 MVP 需要的模型选项。
- 提供安全的本地配置模板，密钥只通过环境变量读取。

不做视频生成、音频生成、账号系统、支付、媒体分发、provider 原始响应持久化，也不声明人工创作质量验收。

## Runtime 契约

`POST /projects/{project_id}/prompt-optimizations`

- 本地 deterministic 创作智能体始终先产出 canonical prompt。
- 只有请求选择 MiniMax 文本增强模型，且 `AFS_ALLOW_REMOTE_LLM=true` 时，才调用 MiniMax-M3。
- Runtime 只保存安全过滤后的增强 prompt 和安全状态摘要。
- 不保存、不返回 provider raw、reasoning、Authorization、本地路径、signed URL 或媒体字节。

`POST /projects/{project_id}/keyframe-generations`

- 只有 `AFS_ALLOW_REMOTE_IMAGE=true` 时，才允许 MiniMax image provider 发起真实请求。
- gate 关闭时只返回 blocked safe manifest，不发网络请求。
- gate 开启时使用 `image-01`、`response_format=base64`、`prompt_optimizer=false`，并支持可选 `seed`。
- API 只返回 job/artifact 摘要，不返回图片字节或本地绝对路径。

## 配置方式

提交到仓库的安全模板：

- `configs/models.example.yaml`
- `configs/providers.example.json`

本地文件被 Git 忽略：

- `configs/models.yaml`
- `configs/providers.local.json`

本地 live smoke 需要设置：

```powershell
$env:MINIMAX_API_KEY="<local-test-key>"
$env:AFS_MODEL_CONFIG="$PWD\configs\models.yaml"
$env:AFS_PROVIDER_CONFIG="$PWD\configs\providers.local.json"
$env:AFS_ALLOW_REMOTE_LLM="true"
$env:AFS_ALLOW_REMOTE_IMAGE="true"
```

本地配置文件和 provider key 不能提交。

## Studio 表现

Studio 模型选择器缩减为当前 MVP 面：

- 文本：本地创作智能体、MiniMax-M3 增强。
- 图片：MiniMax `image-01`。
- 视频和音频：本地预览，暂不接 provider。

只有图片节点选择远程图片模型时，“发送”才调用 keyframe generation。非图片节点继续走本地预览。

## 人工对比方案

第一轮做五个用例：

1. 同一人物连续两张关键帧，检查角色一致性。
2. 同一空间不同动作，检查场景连续性。
3. 低调室内光，检查主光、辅光、轮廓光控制。
4. 导演台二维布局导出机位、人物和灯光关系。
5. 用户偏好更夸张，但专业约束要求克制的冲突用例。

每个用例生成三组：

- A：原始 prompt 直接生成关键帧。
- B：本地 deterministic 创作智能体优化后生成关键帧。
- C：MiniMax-M3 增强后的创作智能体 prompt 生成关键帧。

每张图按 1 到 5 分记录：

- 意图覆盖
- 人物一致性
- 场景连续性
- 构图/机位
- 灯光可信度
- 关键帧可控性
- 画面缺陷
- 安全/泄露风险
- 是否可进入下一轮

决策规则：

- B 相对 A 在至少 3/5 用例提升，说明本地创作智能体作为基线有价值。
- C 相对 B 在至少 3/5 用例提升且无泄露，MiniMax-M3 增强保留为可选路径。
- 角色和场景连续性没有过关前，不打开视频 gate。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_openai_compatible_provider.py tests\test_model_config.py tests\test_minimax_image_smoke.py tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_web_studio_static.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state.py tests\test_api_runtime_service.py -q
Get-ChildItem apps\studio\src -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

## 声明边界

- gate 关闭验证只是工程验证。
- gate 开启运行只是 provider smoke。
- provider smoke 不等于人工验收、商业验证、视频可控性验证或 durable memory 晋升。

## 2026-06-12 Token Plan / Plus Update

- MiniMax Plus uses a Token Plan subscription key. This key is not interchangeable
  with a pay-as-you-go REST API key for the image endpoint.
- Local Plus image smoke now uses the official `mmx` CLI backend with
  `execution_backend=mmx_cli` and region `cn`.
- The REST MiniMax image adapter remains available for future pay-as-you-go API
  keys, but `configs/providers.example.json` and the local ignored provider
  config now point image generation at `mmx_cli`.
- Runtime smoke succeeded on `http://127.0.0.1:8793` through
  `POST /projects/live-smoke/keyframe-generations`; one real `image-01`
  candidate was saved under ignored runtime artifacts.
- The subscription key was not written into tracked config, manifest, API
  response, or project documentation.

## 2026-06-12 Studio Preview / Chinese Prompt Update

- Runtime keyframe candidate previews now include safe `width`, `height`, and
  `aspect_ratio` metadata. Studio uses those real artifact dimensions to resize
  image nodes after successful generation.
- Studio image preview cards no longer inherit the generic 180px result max
  height, so portrait keyframes render as full portrait images instead of cropped
  horizontal strips.
- MiniMax-M3 enhancement now asks for Chinese user-facing sections. English or
  templated LLM output is discarded and replaced with a deterministic Chinese
  fallback prompt for the user surface.
- Local Runtime was restarted at `http://127.0.0.1:8793/studio/` with both
  `AFS_ALLOW_REMOTE_LLM=true` and `AFS_ALLOW_REMOTE_IMAGE=true` in the child
  process environment.

Latest verification:

```text
tests/test_api_runtime_prompt_memory_loop.py
tests/test_api_runtime_creative_agent_keyframes.py
tests/test_web_studio_static.py
tests/test_minimax_image_smoke.py
tests/test_minimax_image_smoke_backends.py
Result: 25 passed, 1 Starlette/httpx warning

apps/studio JS node --check: passed
git diff --check: passed with Windows CRLF notices only
Live MiniMax-M3 probe: provider_calls_started=true; user prompt starts with Chinese 意图：; Intent: absent
Live MiniMax image-01 smoke: succeeded; preview URL present; content-type image/jpeg; dimensions 720x1280
```

Observed quality risk:

- The latest live keyframe was valid and vertical, but the generated picture
  still contained visible text-like artifacts/watermark risk. Treat this as a
  manual comparison scoring item, not as resolved creative quality.

## 2026-06-12 Connected Reference Image Update

- Studio now supports explicit image upload on every node, not only image/video
  nodes. Uploads are stored in ignored Runtime assets and surfaced to the canvas
  as safe preview URLs.
- Downstream keyframe requests automatically collect uploaded image asset ids
  from the current node and directly connected upstream nodes. Upstream prompt
  snippets are included as `connected_reference_nodes`, so front/side/back view
  notes can guide the creative agent and provider prompt.
- Runtime resolves uploaded image asset refs into local provider-only paths and
  passes the first resolved reference to MiniMax image generation as a subject
  reference. The API response and safe artifacts keep only asset ids, hashes,
  dimensions, and reference counts.
- `mmx` CLI backend now receives `--subject-ref type=character,image=...` when a
  connected reference image is available.
- Successful generated keyframe candidates are now registered as reusable image
  assets and attached back to their Studio node. A downstream connected node can
  therefore use the upstream generated character image as a MiniMax subject
  reference without exposing local paths or media bytes to the browser.
- Studio state persistence now retains safe `uploads` and `previewAspectRatio`
  fields, so the reference chain survives reloads.

Latest focused verification:

```text
tests/test_api_runtime_prompt_memory_loop.py
tests/test_api_runtime_creative_agent_keyframes.py
tests/test_minimax_image_smoke.py
tests/test_minimax_image_smoke_backends.py
tests/test_web_studio_static.py
tests/test_model_config.py
tests/test_openai_compatible_provider.py
tests/test_api_runtime_studio_state.py
Result: 42 passed, 1 Starlette/httpx warning

apps/studio JS node --check: passed
git diff --check: passed with Windows CRLF notices only
Runtime upload smoke: asset id present; preview URL present; media_bytes_returned=false
```

Known boundary:

- Multi-view uploads are collected and traced, but the current MiniMax CLI
  provider call uses the first resolved reference image as the actual subject
  reference. Treat true multi-reference ranking/selection as the next controlled
  experiment.
