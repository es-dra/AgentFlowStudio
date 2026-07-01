# AFS Studio Main-Path Delivery Readiness Gate - 2026-07-01

## Execution Method

This T50 slice uses Agentic Loop Engineering to verify the provider-closed Studio/Runtime main path as an internal delivery readiness gate. AgentFlow Studio remains the AI-native manga/video/image content production workbench; this gate is a loop artifact and not the product identity.

## Verdict

`internal_provider_closed_tryout_ready`

This verdict means the current Studio/Runtime main path is ready for internal provider-closed tryout as a structure-verified workflow. It does not mean provider smoke is complete, generated-media quality is accepted, human creative acceptance is granted, business validation is complete, or any public/legal/patent/COS active-rule decision has been made.

## Scope

The readiness gate verifies the user main path:

1. real short-drama benchmark input: `multi_role_prop_exchange_chase`
2. local storyboard and content-quality report
3. asset-card candidate and fixed-asset confirmation path
4. Production Graph fixed-asset reuse evidence
5. Studio keyframe layer, keyframe preflight, request plan, and blocked bridge evidence
6. feedback overlay decision carried into the next blocked keyframe request

## Changes

- `tools/studio_main_path_browser_qa.py` now emits a delivery readiness section in its provider-closed browser report.
- `tools/studio_delivery_readiness_gate.py` holds the small readiness contract and verdict logic.
- `tools/studio_main_path_browser_qa_support.py` seeds the T49 real-script benchmark by default and exposes shot, content-quality, candidate, and Production Graph evidence counts.
- `tests/runtime_main_loop_e2e_support.py` accepts a benchmark case id so existing main-loop harnesses can reuse the same path without forking fixtures.
- `tests/test_studio_main_path_browser_qa_tool.py` covers the readiness verdict and the blocked-provider failure mode.

## Evidence

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t50-focused tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_e2e.py tests\test_storyboard_content_quality_benchmarks.py -q
# 9 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t50-impacted tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_e2e.py tests\test_api_runtime_multi_character_keyframe_bridge_e2e.py tests\test_storyboard_content_quality_benchmarks.py tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_visual_asset_promotion_gate_static.py -q
# 20 passed, 1 warning

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\t50-browser-runtime --report runs\t50_studio_main_path_delivery_readiness.json --screenshot runs\t50_studio_main_path_delivery_readiness.png
# passed; delivery_readiness.verdict=internal_provider_closed_tryout_ready; case_id=multi_role_prop_exchange_chase; provider_calls_started=false; console_error_count=0; response_error_count=0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; no new oversized-file warning after current-wave cleanup

git diff --check
# passed
```

## Readiness Separation

| Area | T50 result |
|---|---|
| Product readiness | `provider_closed_internal_tryout_path_ready` for internal structure-verified use |
| Quality evidence | real-script Studio/Runtime main-path evidence with all readiness checks passed |
| Governance evidence | provider gates closed, no unsafe markers in the checked path, non-claims preserved |
| Human/provider/business gates | still open future gates; none claimed by T50 |

## Managed Thread Register

| Lane | Status | Next action | Close condition |
|---|---|---|---|
| AFS T50 Studio main-path delivery readiness gate | Completed as provider-closed readiness gate on `codex/afs-post-main-loop-e2e-continuation-20260630`. | Commit/push if final branch review stays green and below threshold. | Browser report, focused/impacted tests, Studio JS, maintenance audit, diff check, and YAML parse are green. |
| AFS Redundancy Maintenance Lane | Archive deferred by Delivery Control Plane. | No T50 action; do not touch old conflicted worktree or rebuild branch. | Fresh rebuild only if the ledger becomes needed again. |
| CompanyOS/COS lanes | Governance/integration authorization items, not AFS product blockers. | No T50 action. | Owner-authorized integration or archive/defer outside this AFS lane. |

## Non-Claims

This is provider-closed Studio/Runtime delivery readiness evidence only. It is not provider smoke, live provider call, generated media evidence, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, server sync, Runtime health verification, or COS active-rule promotion.
