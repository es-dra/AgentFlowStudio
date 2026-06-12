# AFS-STUDIO-MVP-USABILITY-P0 Handoff

Date: 2026-06-13
Branch: `codex/afs-studio-mvp-usability-p0`

## Summary

This slice closes the first human-testing usability issues found in Studio:

- The prompt optimizer no longer presents local deterministic fallback as a valid user-facing optimization result.
- Studio optimization requests now require remote LLM enhancement and fail visibly if the LLM provider/gate path is unavailable.
- Local Windows user env was configured for this machine with `AFS_ALLOW_REMOTE_IMAGE=true`, `AFS_ALLOW_REMOTE_LLM=true`, and `AFS_PROVIDER_CONFIG=D:\Projects\AgentFlowStudio\configs\providers.local.json`.
- Failed keyframe results can be persisted without the Studio state sanitizer rejecting transient runtime bundle details.
- Image-node retry now uses the actual generation path, and image nodes expose a direct canvas action to mark the current uploaded/generated image as a character or scene asset.

## Changed Files

- `apps/api/runtime_prompt_memory.py`
- `apps/api/runtime_studio_state.py`
- `apps/studio/src/optimizer.js`
- `apps/studio/src/optimizer-contract.js`
- `apps/studio/src/runtime-client.js`
- `apps/studio/src/node-actions.js`
- `apps/studio/src/panels/node-menu.js`
- `apps/studio/src/canvas-input.js`
- `apps/studio/src/presets/models.js`
- `tests/test_api_runtime_prompt_memory_loop.py`
- `tests/test_api_runtime_studio_state_persistence.py`
- `tests/test_web_studio_static.py`

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py::test_studio_prompt_optimizer_requires_remote_llm_when_requested tests\test_api_runtime_prompt_memory_loop.py::test_studio_prompt_optimizer_does_not_fallback_when_remote_llm_output_is_rejected tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_static.py::test_studio_model_picker_only_exposes_current_mvp_models -q
# 4 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_static.py -q
# 21 passed, 1 warning

node --check apps\studio\src\optimizer.js
node --check apps\studio\src\optimizer-contract.js
node --check apps\studio\src\runtime-client.js
node --check apps\studio\src\node-actions.js
node --check apps\studio\src\panels\node-menu.js
node --check apps\studio\src\canvas-input.js
node --check apps\studio\src\presets\models.js
# passed

.\.venv\Scripts\python.exe -m pytest -q
# 844 passed, 1 warning
```

## Boundaries

- No live provider call was made while implementing this slice.
- Runtime verification is not human acceptance.
- Video, ASR, and external-download gates remain unopened.

## Next Human Test

Use the already running Studio at `http://127.0.0.1:8790/studio/` after the runtime service is restarted on this branch. Test:

1. Upload or generate an image node.
2. Use the single prompt optimization action.
3. Replace or append the optimized prompt.
4. Generate an image.
5. Mark the image node as a character or scene asset.
6. Confirm the fixed asset is visible in the canvas asset list and can be connected into a later generation.
