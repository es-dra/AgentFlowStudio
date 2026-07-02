# AFS I2 Hardening Integration Merge and Server Hash Sync - 2026-07-02

Status: `server_hash_sync_done_runtime_loaded_code_freshness_blocked_exact`

## Scope

I2 integrated evaluator-passed I1 branch
`codex/afs-pre-human-hardening-integration-20260702` into AFS `master` under
Owner non-stop authorization. This was an integration and ops-sync lane only:
no provider smoke rerun, no generated-media QA, no human creative acceptance,
no product readiness, no business/public/legal readiness, no CompanyOS
projection, no durable-memory promotion, and no COS active-rule promotion.

## Git Integration Evidence

- I1 branch head before merge:
  `eebb9180810825d286a736cabba854512bfff466`.
- Verified base/current `origin/master` before merge:
  `f00fbc6c1404a4c3b812056a0f142626edb75ea8`.
- `git merge-base HEAD origin/master` returned
  `f00fbc6c1404a4c3b812056a0f142626edb75ea8`.
- `git rev-list --count origin/master..HEAD` returned `7`.
- Local `master` fast-forwarded with
  `git merge --ff-only eebb9180810825d286a736cabba854512bfff466`.
- `git push origin master` advanced GitHub `master` from `f00fbc6c` to
  `eebb9180`.
- Direct remote check after push:
  `git ls-remote origin refs/heads/master` returned
  `eebb9180810825d286a736cabba854512bfff466`.

## Verification Evidence

Pre-push on the I1 worktree:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
# exported

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-i2-openapi tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed

npm.cmd run check:studio-js
# JS syntax check passed: 135 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-i2-full-prepush -q
# 892 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; warning-only findings

git diff --check
# passed
```

Post-push on integrated local `master`:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-i2-openapi-postpush tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed

npm.cmd run check:studio-js
# JS syntax check passed: 135 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-i2-full-postpush -q
# 892 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; warning-only findings

git diff --check
# passed
```

Warnings remained the known Starlette TestClient deprecation and duplicate
operation ID warning in legacy `runtime_v02.py`. Maintenance audit remained
warning-only; protected local `docs/demo-docs-20260629/` was not touched.

## Server Sync Evidence

Before sync, both server checkouts were at
`f00fbc6c1404a4c3b812056a0f142626edb75ea8`. I2 synced both with:

```text
git fetch origin
git merge-base --is-ancestor HEAD origin/master
git merge --ff-only origin/master
```

Server checkout results:

- `/home/afs-ops/AgentFlowStudio` fast-forwarded to
  `eebb9180810825d286a736cabba854512bfff466`.
- `/opt/afs/AgentFlowStudio` fast-forwarded to
  `eebb9180810825d286a736cabba854512bfff466`.
- `/home` ops-local untracked files were preserved:
  `docs/demo/` and `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`.
- `/opt` remained clean after sync.

This handoff is a docs-only follow-up record. The final I2 closeout should
fast-forward both server checkouts once more to the commit containing this
record, preserving the same no-reset/no-clean rule.

## Runtime Evidence

Read-only service evidence after code sync:

- `systemctl is-active afs-runtime.service` returned `active`.
- `MainPID=1962036`.
- `ExecMainStartTimestamp=Sun 2026-06-28 12:58:16 UTC`.
- `WorkingDirectory=/opt/afs/AgentFlowStudio`.
- Local `http://127.0.0.1:8790/health` returned `status=ready` and
  `studio_static.status=ready`.
- Public `https://afstudio.art/health` returned `status=ready` and
  `studio_static.status=ready`.

Runtime loaded-code freshness is not claimed because service-control was not
available. `sudo -n true` returned `sudo: a password is required`, so I2 did not
attempt restart/reload loops.

## Provider Smoke Decision

Provider smoke was not rerun. Existing E1 evidence remains external
pre-integration provider-route smoke evidence for one minimal CrazyRouter
`seedance_i2v` route only. It is not media QA, human acceptance, product
readiness, or post-integration loaded-code evidence.

## Residual Risks

- Runtime repo files are synced, but the active Python service was not restarted
  or reloaded, so loaded-code freshness remains blocked by service-control.
- The server health endpoint is ready, but it may still be served by the
  pre-sync process because PID/timestamps did not change.
- Provider gates remain a separate human/provider-cost gate.

## Non-Claims

No provider smoke rerun, generated media, generated-media QA, human creative
acceptance, product readiness, business validation, public/legal/patent
readiness, CompanyOS projection, durable-memory promotion, COS active-rule
promotion, or runtime loaded-code freshness is claimed.
