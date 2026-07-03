# AFS Runtime Idempotent Submit Redispatch Durable Handoff - 2026-07-03

## Identity

- bottom_up_feedback_id: `BU-AFS-V02-IMP-P1-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE-20260703-001`
- top_down_dispatch_id: `TD-AFS-V02-IMP-P1-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE-20260703-001`
- source_thread_id: `019f25c8-37c9-7e30-8c57-279e40a3a1fc`
- lane: `IMP-P1-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE`
- task_class: Deep bounded backend implementation
- close_state: `backend_idempotent_submit_redispatched_durable_ready_for_eval`
- branch: `codex/runtime-idempotent-submit-redispatch-durable-20260703`
- base: `master` / `677577a96f88d1067569c6b47db073a48da0748a`

## Scope

Implemented only Runtime submit idempotency for existing provider-gated submit
surfaces:

- `POST /projects/{project_id}/keyframe-generations`
- `POST /projects/{project_id}/video-generations`
- `POST /projects/{project_id}/generation-comparisons`

No provider gates were opened. No live provider call, generated media, video QA,
auth bypass, secret handling, deploy, restart, merge, push, OpenAPI mutation,
CompanyOS/COS mutation, readiness claim, human acceptance claim, or business /
public / legal claim occurred.

## Dirty Ownership Ledger

Startup status before edits:

```text
git status --short --branch
## HEAD (no branch)

HEAD:   677577a96f88d1067569c6b47db073a48da0748a
master: 677577a96f88d1067569c6b47db073a48da0748a
```

No user/third-party uncommitted changes were present. A durable branch was
created before edits:

```text
codex/runtime-idempotent-submit-redispatch-durable-20260703
```

## Implementation

- Added `apps/api/runtime_submit_idempotency.py` as a small file-backed submit
  ledger helper.
- Stable request id namespace is scoped by `project_id/action/stable_request_id`.
- Stable request id prefers `X-Client-Request-ID`; when absent, it falls back to
  a request fingerprint key.
- Request fingerprint canonicalizes Pydantic request JSON and intentionally
  excludes volatile `generated_at`.
- Reservation uses atomic directory creation, then atomic JSON writes through the
  existing `write_json()` lock/replace path.
- Exact duplicate completed requests replay the stored public response, preserving
  the same response body and job identity.
- Same stable request id with changed payload returns 409
  `idempotency_conflict` before job creation or submit/build dispatch.
- Conflict envelope carries `provider_calls_started=false` both top-level and in
  `details`.
- In-scope exceptions before a public response abort the newly-created
  reservation to avoid poisoning retries.

## Changed Files

- `apps/api/runtime_submit_idempotency.py`
- `apps/api/runtime_keyframe_routes.py`
- `apps/api/runtime_video_routes.py`
- `apps/api/runtime_generation_comparisons.py`
- `tests/test_api_runtime_idempotent_submit.py`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE-20260703.md`

## Focused Test Coverage

Added `tests/test_api_runtime_idempotent_submit.py` covering:

- keyframe duplicate same `X-Client-Request-ID` replay returns the same response
  and same `job_id`;
- keyframe changed payload with same stable request id returns 409 conflict with
  `provider_calls_started=false`;
- video duplicate replay and changed-payload conflict, provider gate closed;
- generation-comparison duplicate replay and changed-payload conflict;
- monkeypatched fail-fast submit/build functions prove replay/conflict do not
  redispatch;
- completed ledger files carry `fingerprint`, `response_sha256`, `job_id`, and
  `provider_calls_started=false`.

## Verification

Passed:

```text
python3 -m py_compile apps/api/runtime_submit_idempotency.py apps/api/runtime_keyframe_routes.py apps/api/runtime_video_routes.py apps/api/runtime_generation_comparisons.py tests/test_api_runtime_idempotent_submit.py
git diff --check
```

Blocked in this checkout:

```text
python3 -m pytest tests/test_api_runtime_idempotent_submit.py -q
# /usr/bin/python3: No module named pytest

python --version
# /bin/bash: python: command not found

.venv/bin/python -m pytest --version
# .venv/bin/python: No such file or directory

python3 -m pip --version
# /usr/bin/python3: No module named pip

python3 -c "import fastapi, pydantic; import starlette.testclient"
# ModuleNotFoundError: No module named 'fastapi'

python3 - <<'PY'
# helper behavior smoke attempted
# ModuleNotFoundError: No module named 'pydantic'
PY
```

Adjacent suites were not executable for the same missing dependency reason:

- `tests/test_api_runtime_provider_submit_preflight.py`
- `tests/test_api_runtime_video_generations.py`
- `tests/test_api_runtime_generation_comparison.py`
- `tests/test_api_runtime_generation_manifest_safety.py`

## Atomicity Judgment

The implementation is suitable for the current local Runtime model:

- reservation is an atomic filesystem `mkdir()` under
  `submit_idempotency/{project_id}/{action}/{stable_request_id}`;
- ledger and response persistence use existing atomic `write_json()` behavior;
- conflict is detected before job id allocation and before provider-capable
  submit/build dispatch;
- completed duplicates replay exactly the stored public response.

Residual risk:

- this is not a distributed lock for multi-host/shared-storage Runtime
  deployments;
- a same-request duplicate that arrives while the first request is still pending
  returns a safe 409 `idempotency_request_in_progress` rather than the eventual
  response;
- existing route files remain oversized, especially
  `apps/api/runtime_keyframe_routes.py`; this task intentionally did not split
  route modules to preserve the bounded idempotency scope.

## v0.3.1 / v0.4 / v0.5 / v0.5.1 Fields

- v0.3.1 provider gate: closed; no live image/video provider call.
- v0.4 runtime contract: idempotent submit ledger added for keyframe, video, and
  generation-comparison submit surfaces.
- v0.5 Studio boundary: no Studio mutation; Runtime Service remains the only
  frontend backend boundary.
- v0.5.1 evaluation state: ready for evaluator code review with compile/diff
  evidence; pytest execution blocked by missing local Python dependencies.

## Non-Claims

This handoff does not claim:

- integration readiness beyond evaluator review;
- provider smoke;
- generated-media QA;
- human creative acceptance;
- product, business, public, legal, or patent readiness;
- deploy/server/restart/runtime loaded-code freshness;
- CompanyOS/COS active-rule promotion;
- durable memory promotion.

## Archive Policy

- archive_policy: `agent_created_archive_when_useless`
- owner_manual_archive_excluded: `no`
- archive_after_ack_delivery_confirmed: `true`
