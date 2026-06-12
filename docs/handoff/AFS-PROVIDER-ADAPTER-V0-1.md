# AFS-PROVIDER-ADAPTER-V0-1 Handoff

Branch: `codex/afs-provider-adapter-v0-1`

## Scope

- Added provider adapter contract and registry.
- Standardized MiniMax image as the first Runtime-facing adapter.
- Removed direct `run_minimax_image_smoke` import from `apps/api/runtime_keyframes.py`.
- Moved Runtime prompt limit and reference image slots to provider descriptors.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_adapter_registry.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_context_resolver.py
.\.venv\Scripts\python.exe -m pytest tests/test_minimax_image_smoke.py tests/test_minimax_image_smoke_backends.py
.\.venv\Scripts\python.exe -m py_compile agentflow_studio/model_gateway/provider_adapter.py apps/api/runtime_keyframes.py apps/api/runtime_context_resolver.py apps/api/runtime_context_budget.py
```

Results:

- Adapter/keyframe/resolver focused set: 22 passed.
- MiniMax smoke regression: 9 passed.
- py_compile: passed.

## Provider Gate

No live provider gate was opened. Tests use mocked dispatch or gate-closed paths.

## Non-Goals

- Kling adapter is not implemented in this slice.
- CLI command names remain compatible; deeper CLI routing through registry can be done when needed.
- External provider gateway is still out of scope.
