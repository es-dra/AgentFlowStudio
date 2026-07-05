# AFS Studio Reference Image Upload Diagnostics

Date: 2026-07-05
Branch: `zhaowei`
Scope: `/studio/` reference image upload/replace and Runtime image asset upload diagnostics

## Problem

The Web test report showed that right-clicking an image/keyframe node and using
"upload/replace reference image" reached Runtime, but failed with HTTP 422. The
frontend displayed:

```text
Runtime request failed (422): [object Object]
```

That made the failure unactionable: users could not tell whether the issue was
file type, image bytes, file size, target node state, or request contract.

## Root Cause

- `apps/studio/src/runtime-client.js` stringified object-shaped Runtime/FastAPI
  `detail` payloads directly with `String(...)`, producing `[object Object]`.
- FastAPI validation errors can also be arrays of objects, which had the same
  readability problem.
- `apps/api/runtime_image_assets.py` collapsed distinct upload validation
  failures into a generic `invalid_image_asset` 422 response.

## Fix

- Studio Runtime client now renders safe object details using `reason`, `error`,
  `detail_code`, and `field`.
- Studio Runtime client now renders FastAPI validation arrays as readable field
  messages, for example `field=data_base64: Field required`.
- Runtime image asset upload now returns actionable safe 422 codes:
  - `reference_image_upload_invalid_base64`
  - `reference_image_upload_empty`
  - `reference_image_upload_too_large`
  - `reference_image_file_type_mismatch`
  - `reference_image_file_type_not_allowed`
  - `reference_image_dimensions_required`

## Files

- `apps/studio/src/runtime-client.js`
- `apps/api/runtime_image_assets.py`
- `tests/test_api_runtime_studio_state_persistence.py`
- `tests/test_web_studio_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Verification

```text
python -m pytest tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_static.py -q -> 20 passed
python -m pytest tests\test_web_studio_static.py::test_runtime_error_detail_objects_are_rendered_without_object_object tests\test_web_studio_static.py::test_runtime_error_detail_object_and_validation_array_are_readable tests\test_api_runtime_studio_state_persistence.py::test_image_asset_upload_returns_actionable_safe_422_detail tests\test_api_runtime_studio_state_persistence.py::test_image_asset_upload_rejects_mime_mismatch_with_safe_reason -q -> 4 passed
npm.cmd run check:studio-js -> JS syntax check passed: 122 files
```

## Server Retest Points

- Upload a valid PNG/JPG from an image/keyframe node. It should bind as an image
  asset and show a preview.
- Try an unsupported or malformed file. The node should show a concrete reason,
  not `[object Object]`.
- If Runtime returns FastAPI request validation details, Studio should show a
  readable field message instead of object text.

## Boundary

- No Runtime provider gate was opened.
- No LLM/image/video/ASR provider call was made.
- No uploaded media bytes, local media paths, signed URLs, provider raw
  responses, or secrets are written to repo records.
