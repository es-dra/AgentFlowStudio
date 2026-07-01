# AFS Studio Main Path Browser QA - 2026-07-01

## Scope

AFS-T47 verifies that `/studio/` can naturally carry the Runtime main-loop evidence path in a provider-closed browser flow:

- real benchmark storyboard seed
- asset card plus fixed visual asset from human-gate evidence
- production graph summary and source-evidence refs
- keyframe request plan and blocked keyframe bridge evidence
- feedback overlay include decision and second blocked bridge

## Changes

- Added `tools/studio_main_path_browser_qa.py` and `tools/studio_main_path_browser_qa_support.py`.
- Added `tests/test_studio_main_path_browser_qa_tool.py` for seed contract, evidence assertion, screenshot path, and provider-closed static guard.
- Split safe Studio storyboard helpers into `apps/api/runtime_studio_state_storyboard.py`.
- Preserved safe production graph summaries, fixed-asset source evidence refs, and human-gate non-claim flags through Studio state persistence.
- Pruned `lastKeyframeSourceEvidenceTrace` from persisted Studio state so unsafe runtime trace internals remain transient.

## Evidence

```text
npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t47-focused tests\test_studio_main_path_browser_qa_tool.py tests\test_api_runtime_main_loop_keyframe_bridge_e2e.py tests\test_api_runtime_main_loop_e2e.py tests\test_web_studio_keyframe_production_graph_trace.py tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_api_runtime_studio_state_persistence.py tests\test_api_runtime_studio_state_modules.py -q
# 18 passed, 1 warning

.\.venv\Scripts\python.exe tools\studio_main_path_browser_qa.py --runtime-root .venv\t47-browser-runtime --report runs\t47_studio_main_path_browser_qa.json --screenshot runs\t47_studio_main_path_browser_qa.png
# passed; provider_calls_started=false; console_error_count=0; response_error_count=0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed

YAML parse for AFS-AI-Execution-Spec.yaml and AFS-Goal-Driven-Execution-State-v0.1.yaml
# passed
```

## Cleanup

- Current-wave QA tool files were split under the 300-line maintenance threshold.
- `.tmp/pytest-t47-*` is generated basetemp from this run. Deletion hit Windows access denial, so it remains local cleanup pending and is not staged.
- `docs/demo-docs-20260629/` remains do-not-touch, untracked, and unstaged.

## Non-Claims

This is local browser/runtime structure verification only. It is not provider smoke, live provider call, generated media evidence, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, or COS active-rule promotion.
