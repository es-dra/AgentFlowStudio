# AFS Asset Card Image Relay Restore - 2026-06-29

## Scope

Restored the image generation path used by `origin/master`, where Studio image,
keyframe, and asset-card image jobs default to the external `image_relay`
provider service instead of the server-local `codex_image` handoff worker.

## Root Cause

The local `zhaowei` branch still defaulted keyframe and asset-card image
generation to `codex_image`. In the failing Studio flow, asset-card image jobs
therefore entered the Codex handoff/worker path and surfaced the generic safe
failure:

```text
remote_image_provider_not_ready
Image provider configuration is not ready.
```

The GitHub reference branch uses `image_relay` for this path.

## Changes

- `apps/studio/src/presets/models.js`
  - Restored `IMAGE_RELAY_SERVICE_ID = "image_relay"` as the default image
    provider service.
- `apps/api/runtime_models.py`
  - Restored `image_relay` as the default for keyframe generation and
    comparison requests.
- `apps/api/runtime_keyframes.py`
  - Resolves `image_relay` first, falling back to legacy `codex_image` only
    when `image_relay` is absent.
  - Routes OpenAI Images relay requests with reference images through edit mode.
- `apps/api/runtime_generation_preflight.py`
  - Uses the same service alias and OpenAI Images reference-slot behavior during
    preflight.
- `agentflow_studio/model_gateway/company_secrets.py`
  - Projects older API-relay `codex_image` provider config into `image_relay`.
- `configs/providers.example.json`
  - Documents `image_relay`, `image_relay_pool`,
    `AFS_IMAGE_RELAY_BASE_URL`, and `AFS_IMAGE_RELAY_API_KEY`.

## Verification

```powershell
python -m pytest tests\test_provider_adapter_registry.py tests\test_api_runtime_keyframe_reference_assets.py -q
python -m pytest tests\test_web_studio_assets_generation_static.py -q
python -m pytest tests\test_codex_image_handoff.py tests\test_codex_runtime_env.py -q
git diff --check
```

Results:

```text
36 passed
25 passed
23 passed
git diff --check passed
```

## Deployment Notes

Server Runtime still needs the image gate and relay env:

```bash
AFS_ALLOW_REMOTE_IMAGE=true
AFS_IMAGE_RELAY_BASE_URL=...
AFS_IMAGE_RELAY_API_KEY=...
```

If the server config still contains `codex_image` but its provider is
`api_relay`, Runtime will project it into `image_relay`. If the server config
contains only `codex_handoff` for `codex_image`, asset-card image generation
will not use the known-good relay path until the provider config is updated.

Boundary: no live provider call, secret read, media byte, signed URL, video
generation, ASR, external download, or private Company OS source content was
used or written.
