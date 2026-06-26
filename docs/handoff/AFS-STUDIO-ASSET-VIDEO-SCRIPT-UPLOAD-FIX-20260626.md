# AFS Studio Asset Video and Script Upload Fix - 2026-06-26

## Summary

This patch closes two residual internal-test entrypoint bugs in Studio:

- Script-node floating upload now uses the script import path, so supported
  script files no longer go through image upload and fail with a 422.
- Fixed visual assets selected from the asset library can now drive video
  generation as first-frame references by resolving their public
  `image_asset_refs[0]`.

## Changed Scope

- `apps/studio/src/canvas-node-action-handler.js`
- `apps/studio/src/panels/drawer-asset-actions.js`
- `apps/studio/src/panels/drawer-assets.js`
- `apps/studio/src/video-node-flow.js`
- `tests/test_web_studio_prompt_script_static.py`
- `tests/test_web_studio_assets_generation_static.py`

## Behavior

- `text` and `script` nodes both route `data-action="upload"` to
  `importScriptFileIntoTextNode`.
- `markAssetReference` and `attachAssetToSelection` keep fixed visual assets in
  `params.visualAssets`; when the target node is a video node, they also set
  `params.firstFrameImageAssetId` from the fixed asset's first image reference
  and add a `first_frame` upload ref.
- Drawer `设为首帧` / `设为尾帧` actions now work for both raw image assets and
  fixed visual assets that carry image references.
- `ensureVideoFirstFrameAsset` now recovers first-frame state from a video
  node's existing `visualAssets`, or from upstream nodes' fixed visual assets,
  before failing with the normal missing-first-frame message.

## Verification

```text
npm run check:studio-js
# JS syntax check passed: 122 files

.venv/bin/python -m pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py tests/test_api_runtime_context_resolver.py tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py tests/test_api_runtime_auth.py -q
# 84 passed

git diff --check
# passed
```

## Boundaries

- No Runtime API contract was changed.
- No provider gate was opened.
- No live image/video/LLM/ASR/vision/external-download provider call was
  started for this patch.
- No provider raw response, signed URL, secret, session token, invite code,
  generated media byte, local private asset byte, or private Company OS source
  material was written to the repository.

## Remaining Notes

- Video revision is still an experimental path guarded by
  `AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION`; this patch does not turn localized
  video revision into a general available feature.
- The old `afs-codex-image-worker.service` may still be active on the server
  until a privileged operator disables it; Studio's current product-facing
  generation path remains `image_relay`.
