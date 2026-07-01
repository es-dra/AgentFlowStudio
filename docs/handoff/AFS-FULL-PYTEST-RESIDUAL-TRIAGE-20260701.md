# AFS Full Pytest Residual Triage - 2026-07-01

## Execution Method

This T48 closeout uses Agentic Loop Engineering to resolve the proactive discovery residual from T47: full pytest had four environment/path-sensitive failures after the Studio main-path browser QA closeout. AgentFlow Studio remains the AI-native manga/video/image content production workbench; loop artifacts are execution support only.

## Managed Thread Register

| Lane | Owner / source thread | Status | Next action | Close condition |
|---|---|---|---|---|
| AFS T48 full pytest residual triage | Current AFS Full Goal Worker | Completed as provider-closed fixture/test debt triage on `codex/afs-post-main-loop-e2e-continuation-20260630`. | Commit/push this branch review package if final branch review stays green and below threshold. | Full pytest is green, maintenance has `failed=0`, branch review has no blockers, and only the known do-not-touch demo docs remain untracked. |
| AFS Redundancy Maintenance Lane | `019f1b8c-4e67-7840-93ca-5cd0b99b1d21`, converted from old read-only audit thread | Pending handoff; T48 did not create or edit its target audit file. | Lane owner should create `docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md`, run no-op verification, and produce low-risk cleanup prompts. | Audit exists with no-op verification and cleanup prompts; no code deletion, provider opening, generated media, business claim, or COS active-rule promotion. |
| CompanyOS projection lane | `019f1ba2-9956-7c80-9d18-c0d541b3142c` | Completed by its lane but not committed/pushed; projection integration follow-up remains open. | Lane owner should handle commit/push/integration verification in the CompanyOS/source repo context. | Projection changes are committed/pushed or explicitly deferred by that lane; AFS T48 does not mark it closed. |

## Scope

T48 converts the four T47 full pytest residuals into deterministic test conclusions without opening provider, image, video, high-cost, external download, or customer/business/legal gates.

## Residual Conclusions

- `.venv` basetemp maintenance failures were fixture isolation debt: two maintenance-audit tests inherited the parent repo ignore state when pytest basetemp lived under ignored `.venv`. The tests now initialize their own git repos before exercising git-state-sensitive audit behavior.
- `runtime_root_persisted` was a test assumption debt: Runtime correctly reports repo-local absolute roots as not persisted. The health test now asserts against `runtime_root_is_persisted(tmp_path)` instead of hard-coding `true`.
- `C:/Users/chenzy/.afs-codex` chmod denial was user-home fixture leakage: the Codex local missing-CLI test now isolates `AFS_CODEX_HOME` under pytest tmp and disables bootstrap so it reaches the missing-command error path deterministically.

## Changes

- Updated `tests/test_maintenance_audit.py` with a small `_init_git_repo` helper for the two affected audit fixtures.
- Updated `tests/test_api_runtime_service.py` to verify `runtime_root_persisted` against the production helper.
- Updated `tests/test_codex_local_provider_errors.py` to isolate the Codex local provider test from the workstation user-home runtime.

## Evidence

```text
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t48-residual tests\test_maintenance_audit.py::test_maintenance_audit_reports_expected_contract_shape tests\test_maintenance_audit.py::test_historical_docs_are_exempt_only_when_summary_exists tests\test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets tests\test_codex_local_provider_errors.py::test_codex_local_missing_cli_is_reported_as_model_gateway_error -q
# 4 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp .venv\pytest-t48-full -q
# 778 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

git diff --check
# passed
```

YAML/state parse is required after execution-state update before final closeout.

## Non-Claims

This is deterministic provider-closed test/fixture stabilization. It is not provider smoke, live provider call, generated media evidence, human creative acceptance, business validation, public claim, patent/legal decision, external download, deploy verification, server sync, Runtime health verification, or COS active-rule promotion.
