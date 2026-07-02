# AFS Runtime Log/Artifact Leakage Hardening - 2026-07-02

## Scope

- Lane: D4, AFS Pre-Human-Creative Acceptance Completion & Hardening Gate.
- Traceability: PB-P1-10 / PB-P1-11; Lane C findings 3 and 4.
- Branch: `codex/afs-d4-runtime-log-artifact-hardening-20260702`.
- Worktree: `C:\Users\chenzy\Documents\Codex\2026-07-02\afs-d4-runtime-log-artifact-hardening`.
- Base: `f00fbc6c1404a4c3b812056a0f142626edb75ea8`.

## Changed

- Added `apps/api/runtime_log_safety.py` as the shared Runtime logging sanitizer.
- Routed request/audit/business logging and file logging through the same sensitive-key policy.
- Made `log_business_event()` accept client payload fields named `event_type` without crashing `/studio/client-events`.
- Redacted or omitted nested sensitive keys, local/private paths, URLs, raw payloads, media bytes, and provider prompt text from process/client logs.
- Added artifact project ownership metadata derived from `projects/`, `runs/`, and `feedback/` artifact paths.
- Enforced auth-scoped artifact reads using path/index-derived project ownership before falling back to payload `project_id` fields.
- Preserved unauthenticated local `/artifacts/{artifact_id}` reads for existing local Runtime workflows.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_runtime_log_artifact_hardening.py tests\test_api_runtime_auth.py tests\test_api_runtime_service.py tests\test_api_runtime_media_contract.py tests\test_runtime_generation_logging_static.py -q
# 29 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 871 passed, 520 deselected, 2 warnings

git diff --check
# passed
```

Red evidence before implementation:

```text
python -m pytest tests\test_runtime_log_artifact_hardening.py -q
# 3 failed, 1 passed
# failures covered client-event logging crash, nested log leakage, and cross-project artifact read
```

## Boundaries

- No provider calls.
- No credentials or secrets used.
- No external downloads.
- No server operations or deploy.
- No destructive cleanup.
- No generated-media QA or human creative acceptance claimed.
- No Runtime loaded-code freshness, product/business/public/legal readiness, CompanyOS projection, durable-memory promotion, or COS active-rule promotion claimed.

## Residual Risks

- Artifact project ownership is strongest for artifacts stored under `projects/`, `runs/`, or `feedback/`. Global artifacts without a derivable project path still rely on payload fields or remain auth-readable when no project can be inferred.
- RuntimeStore and runtime_service remain over the 300-line maintenance warning threshold; this lane avoided broader file splitting to keep the security patch low-risk.
- Auth-disabled local artifact reads remain intentionally broad for local compatibility.

## Integration State

- `implementation_ready_for_evaluator`.
- Suggested evaluator route: inspect sanitizer behavior and artifact auth tests, then run the focused suite plus full pytest from the Python 3.12 venv.
