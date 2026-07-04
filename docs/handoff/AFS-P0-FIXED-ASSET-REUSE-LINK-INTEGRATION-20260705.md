# AFS P0 Fixed Asset Reuse Link Integration

Dispatch:
`TD-AFS-V02-IMPL-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705-001`

Expected BU:
`BU-AFS-V02-IMPL-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705-001`

Branch: `codex/p0-fixed-asset-reuse-link-integration-20260705`

Base / pre-HEAD: `cfffa487cd3d3dce085e3157ce3852496f5f9a69`

## Summary

This bounded provider-closed implementation connects Runtime
`asset_auto_binding_graph` evidence to Studio visible reuse state.

Implemented:

- Studio script breakdown now persists Runtime `asset_auto_binding_graph` on the
  source storyboard breakdown surface and on created storyboard shot nodes.
- Graph-bound fixed assets now become Studio node reference stacks on storyboard
  shot and asset-card draft nodes without converting asset-card drafts into
  fixed assets.
- Storyboard keyframe creation now maps graph-bound fixed assets into keyframe
  `visualAssets`, `keyframeLayer.fixed_visual_asset_ids`, and prompt context.
- `assetReuseLocalContract()` now recognizes storyboard-nested binding graphs,
  so actual Studio storyboard paths report `graph_bound_count`.
- Fixed visual asset promotion now exposes and requires explicit
  `link_existing`, `replace`, or `create_new` intent when a graph-bound fixed
  asset or same type+label fixed asset exists.
- Runtime visual asset promotion now accepts explicit reuse intent fields,
  fails closed for duplicate fixed labels without intent, supports
  `link_existing`, validates `replace`, and returns structured duplicate
  warnings.
- Studio state sanitization now preserves safe `assetAutoBindingGraph`,
  `asset_auto_binding_graph`, `nodeReferenceStack`, and `node_reference_stack`
  params plus storyboard-breakdown nested binding graph fields.
- Runtime OpenAPI snapshot was regenerated for the new promote request fields.

## Validation

Passed:

```bash
npm run check:studio-js
```

Result: `JS syntax check passed: 143 files`

```bash
python3 -m py_compile apps/api/runtime_models.py apps/api/runtime_visual_assets.py apps/api/runtime_studio_state_asset_binding.py apps/api/runtime_studio_state_storyboard.py apps/api/runtime_studio_state_param_values.py apps/api/runtime_studio_state_params.py agentflow/algorithms/fixed_asset_memory/__init__.py tests/test_api_runtime_visual_assets.py tests/test_web_studio_visual_asset_promotion_gate_static.py tests/test_web_studio_asset_reuse_contract.py tests/test_api_runtime_studio_state_persistence.py
```

Result: passed.

```bash
/home/afs-ops/AgentFlowStudio/.venv/bin/python -m pytest tests/test_web_studio_asset_reuse_contract.py tests/test_web_studio_visual_asset_promotion_gate_static.py tests/test_api_runtime_visual_assets.py tests/test_api_runtime_studio_state_persistence.py tests/test_api_runtime_production_graph_contract.py tests/test_asset_auto_binding_contract.py tests/test_node_reference_stack_contract.py tests/test_web_studio_reference_upload_contract.py tests/test_web_studio_production_graph_reuse_static.py tests/test_web_studio_prompt_script_static.py tests/test_web_studio_keyframe_production_graph_trace.py -q
```

Result: `54 passed`; final combined focused rerun with OpenAPI/promotion gate checks was `57 passed`.

```bash
/home/afs-ops/AgentFlowStudio/.venv/bin/python -m pytest tests/test_api_runtime_openapi_snapshot.py tests/test_api_runtime_visual_asset_promotion_gate.py -q
```

Result: `3 passed`.

```bash
node --input-type=module -e "<direct graph-bound reuse intent assertion>"
```

Result:
`{"graph_bound_requires_intent":true,"candidate":"fixed_map","intents":["link_existing","replace","create_new"]}`

```bash
git diff --check
```

Result: passed.

## Non-Claims

- No provider behavior change.
- No provider call or gate enablement.
- No Runtime or Studio server run.
- No browser/live `/studio/` QA.
- No deploy, restart, source sync, fetch, pull, push, merge, rebase, reset, or
  clean.
- No generated-media QA, human acceptance, business validation, public/legal
  readiness, durable memory promotion, COS/CompanyOS/source-KB mutation, archive
  execution, or self-archive.
- This does not claim duplicate prevention in live `/studio/`; it is local
  Runtime/Studio contract implementation awaiting independent evaluator review.

## Residual Risks

- UI selector behavior is covered by static/direct tests but not by authorized
  browser interaction QA.
- Runtime duplicate enforcement is route-level/local contract only; live Studio
  acceptance still needs evaluator/browser/runtime verification.
- Graph-bound matching uses safe graph asset ids and type/label fallback; future
  broader graph schemas may need expanded sanitization.

## Next Action

CEO ACK/register/routes this implementation BU. CTO dispatches independent
evaluator, recovery, blocker, or other authorized next step. Worker takes no
further action unless explicitly routed.
