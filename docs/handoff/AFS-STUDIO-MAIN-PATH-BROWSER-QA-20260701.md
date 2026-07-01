# AFS Studio Main Path Browser QA - 2026-07-01

## Execution Method

This T47 closeout records the development method as Agentic Loop Engineering. The project book, execution spec, task ledger, and state file are loop artifacts, not the product identity. AgentFlow Studio remains the AI-native manga/video/image content production workbench.

## Managed Thread Register

Agentic Loop Engineering is running as a proactive discovery loop, so handoff records must track adjacent managed lanes, not only the current worker's task.

| Lane | Owner / source thread | Status | Next action | Close condition |
|---|---|---|---|---|
| AFS T47 main-path browser QA | Current AFS Full Goal Worker | Completed and pushed on `codex/afs-post-main-loop-e2e-continuation-20260630`; final head `6198e715`. | Do not add more T47 functionality; select the next provider-closed item only after checking whether the redundancy maintenance lane has been handed off. | Branch review remains `blocker_count=0`, below threshold, with only `docs/demo-docs-20260629/` as do-not-touch untracked state. |
| AFS Redundancy Maintenance Lane | `019f1b8c-4e67-7840-93ca-5cd0b99b1d21`, converted from old read-only audit thread | Pending handoff; current T47 thread must not create or edit its target file while active. | Lane owner should create `docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md`, run no-op verification, and produce the first low-risk cleanup prompts. | Audit exists with no-op verification and cleanup prompts; no code deletion, provider opening, generated media, business claim, or COS active-rule promotion. |
| CompanyOS projection lane | `019f1ba2-9956-7c80-9d18-c0d541b3142c` | Completed by its lane but not committed/pushed; projection integration follow-up remains open. | Lane owner should handle commit/push/integration verification in the CompanyOS/source repo context. | Projection changes are committed/pushed or explicitly deferred by that lane; do not treat it as closed from AFS T47. |

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

Full pytest was also executed after the T47 code and record commits:

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t47-full -q
# 774 passed, 520 deselected, 2 warnings, 4 failed
```

Failure classification:

- `tests/test_maintenance_audit.py` two failures were basetemp-path artifacts from running full pytest under ignored `.venv`; both targeted maintenance tests passed under a normal workspace basetemp.
- `tests/test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets` failed because repo-local basetemp makes `runtime_root_persisted=false`; T47 did not touch `apps/api/runtime_info.py` or this health contract.
- `tests/test_codex_local_provider_errors.py::test_codex_local_missing_cli_is_reported_as_model_gateway_error` failed before provider dispatch because local `C:/Users/chenzy/.afs-codex` chmod is denied on this workstation.

The full pytest result is therefore recorded as environment/path-sensitive residual risk, not as a T47 provider-closed Studio main-path regression.

## Cleanup

- Current-wave QA tool files were split under the 300-line maintenance threshold.
- `.tmp/pytest-t47-*` is generated basetemp from this run. Deletion first hit Windows access denial; the temporary directories were later moved to ignored `.venv/cleanup-pending/` and are not staged.
- `docs/demo-docs-20260629/` remains do-not-touch, untracked, and unstaged.

## Non-Claims

This is local browser/runtime structure verification only. It is not provider smoke, live provider call, generated media evidence, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, or COS active-rule promotion.
