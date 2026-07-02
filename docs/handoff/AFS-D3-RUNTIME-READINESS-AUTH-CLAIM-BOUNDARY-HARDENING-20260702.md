# AFS D3 Runtime Readiness/Auth Claim Boundary Hardening - 2026-07-02

## Scope

Lane D3 worker scope: Runtime Readiness/Auth/Claim Boundary Hardening for the
CEO v3 `AFS Pre-Human-Creative Acceptance Completion & Hardening Gate`.

Source finding: Lane C finding 2 and traceability claim-boundary rows
PB-P1-01/PB-P1-11.

## Changed

- Split `/health` service health from exposure/auth/readiness claims.
- Added safe `/health.service_health`, `/health.exposure`, and
  `/health.readiness` fields.
- Wired Runtime bind host into `create_runtime_app()` from CLI `--host` and
  `AFS_RUNTIME_SERVICE_HOST`.
- Updated public-edge preflight so a public 200 edge with Runtime auth disabled
  becomes `public_edge_auth_not_ready`, not `ready_for_public_auth`.
- Added three-end and internal HTTP preflight readiness/non-claim fields so
  runtime three-end alignment evidence, loaded-code freshness non-claims,
  service health, public-edge auth, and human/product acceptance remain
  separate.
- Regenerated `docs/openapi/afs-runtime-service.openapi.json`.

## Verification

```text
python -m pytest -q tests/test_api_runtime_service.py tests/test_api_runtime_auth.py tests/test_afs_public_edge_preflight.py tests/test_afs_three_end_status.py tests/test_afs_internal_beta_acceptance.py tests/test_afs_internal_beta_preflight_public_edge.py tests/test_afs_internal_beta_preflight_three_end.py tests/test_api_runtime_openapi_snapshot.py
# 49 passed
```

## Non-Claims

- Runtime loaded-code freshness remains unclaimed unless service PID/timestamp
  changed after authorized restart/reload plus local/public health evidence;
  current three-end fields are alignment evidence only.
- No provider smoke.
- No generated-media QA.
- No human creative acceptance.
- No product, business, public, legal, or patent readiness.
- No CompanyOS/COS promotion.
- No provider calls, secret reads, invite-code disclosure, or durable-memory
  writes.

## Evaluator Notes

`/health.status=ready` remains service/process health only. Acceptance consumers
should inspect the new readiness and exposure fields instead of treating health
as public/human/product readiness.
