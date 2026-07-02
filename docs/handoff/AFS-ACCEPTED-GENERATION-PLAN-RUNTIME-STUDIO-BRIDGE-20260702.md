# AFS Accepted Generation Plan Runtime/Studio Bridge - 2026-07-02

## Status

`runtime_studio_bridge_ready_for_evaluator`

Lane C moves the T58 `accepted_generation_plan_packet` from deterministic
algorithm evidence into a provider-closed Runtime/Studio review bridge. The
default unconfirmed package remains blocked. The accepted packet is surfaced
only when the operator explicitly requests the `confirmed_local_fixture` mode,
which applies the same local accepted contract conditions used by the T58
deterministic fixture mutation.

This is a plan-review surface only. It does not trigger generation, call a
provider, claim generated-media QA, claim product readiness, or validate human
creative/business acceptance.

## Branch And Boundary

Worktree:

```text
C:\Users\chenzy\.codex\worktrees\4f30\AgentFlowStudio
```

Branch:

```text
codex/afs-accepted-generation-plan-runtime-studio-bridge-20260702
```

Base:

```text
2491cfff534362ff2c9d7dafed5faccc0c93a656
```

Protected surfaces not touched:

- `docs/demo-docs-20260629/`
- provider config, secrets, raw provider responses, generated media bytes
- server/deploy/runtime process state
- CompanyOS source KB or active-rule promotion surfaces

## Write Scope

- `apps/api/runtime_accepted_generation_plan.py`
- `apps/api/runtime_accepted_generation_plan_fixture.py`
- `apps/api/runtime_service.py`
- `apps/studio/src/panels/accepted-generation-plan-panel.js`
- `apps/studio/src/panels/dock.js`
- `apps/studio/src/runtime-client.js`
- `apps/studio/styles/studio-portal.css`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_api_runtime_accepted_generation_plan_packet.py`
- `tests/test_web_studio_accepted_generation_plan_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`

## Implementation Summary

- Added a Runtime endpoint:
  `POST /projects/{project_id}/accepted-generation-plan-packets/preview`.
- The endpoint writes a safe JSON preview artifact and run trace under the
  Runtime root, with provider gates closed and no external downloads.
- Default request body is `fixture_mode=default_unconfirmed`, which returns
  `packet_state=blocked_pending_generation_plan_prerequisites` and
  `accepted=false`.
- Accepted surfacing requires explicit
  `fixture_mode=confirmed_local_fixture`, which applies local fixture contract
  closure for branch-specific fixed assets and residual questions.
- Operator-visible evidence includes state, provenance, residual blockers,
  residual closure refs, and explicit non-claim boundaries.
- Studio adds only one dock button, one Runtime client method, and one compact
  review modal. The modal loads the default blocked package first and provides a
  separate explicit control for the confirmed local fixture.

## Verification

Expected red:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-api-red tests\test_api_runtime_accepted_generation_plan_packet.py -q
# 3 failed: new route returned 404 before implementation
```

Focused API/Studio static:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-focused-2 tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_web_studio_accepted_generation_plan_static.py -q
# 5 passed, 1 warning
```

OpenAPI snapshot:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-openapi-check-1 tests\test_api_runtime_openapi_snapshot.py -q
# 1 failed before snapshot regeneration

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -c "from pathlib import Path; from apps.api.openapi_export import export_openapi_schema; export_openapi_schema(Path('docs/openapi/afs-runtime-service.openapi.json'))"
# regenerated committed OpenAPI snapshot

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-openapi-check-2 tests\test_api_runtime_openapi_snapshot.py -q
# 1 passed
```

Studio JS:

```text
npm.cmd run check:studio-js
# JS syntax check passed: 135 files
```

Impacted deterministic/contract bundle:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-impacted-1 tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_openapi_snapshot.py tests\test_web_studio_accepted_generation_plan_static.py tests\test_branch_workflow_accepted_generation_plan_packet.py tests\test_branch_workflow_confirmation_evidence_contract.py tests\test_branch_workflow_generation_planning_gate.py tests\test_branch_workflow_package_contract.py tests\test_interactive_manga_branch_package_contract.py tests\test_shared_object_evidence_contract_fixture.py tests\test_algorithm_library_contracts.py -q
# 75 passed, 1 warning
```

Runtime service and hygiene:

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp %TEMP%\afs-lane-c-service-1 tests\test_api_runtime_service.py -q
# 12 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

git diff --check
# passed
```

Not run:

- Full pytest, because this lane is a narrow Runtime/Studio bridge and the
  impacted contract bundle plus service/static checks passed.
- Browser smoke, because the Studio change is a static dock button/modal review
  surface and `npm.cmd run check:studio-js` plus static tests covered the
  behavior contract.

## Residual Risks

- The accepted packet is still local fixture evidence, not a real operator
  creative acceptance event.
- The Studio surface is static-check verified only; no browser screenshot or
  interactive smoke was run in this lane.
- The route creates an inspectable Runtime preview artifact, but does not
  integrate a long-term storage lifecycle beyond existing Runtime artifact/job
  registration.
- Full pytest was not run in this lane.

## Non-Claims

This lane does not claim provider smoke, live provider calls, external
download, generated media, generated-media quality, human creative acceptance,
business validation, product readiness, public/legal/patent readiness,
deploy/server sync, live Runtime health, CompanyOS projection, durable-memory
promotion, or COS active-rule promotion.

## Closeout Packet

```text
upward_feedback_delivery: pending_until_thread_closeout
worker_local_subagents_used: no
integration_state: runtime_studio_bridge_ready_for_evaluator
decision_needed: evaluator review before any integration, provider, or broader UI claim
latest_artifact: docs/handoff/AFS-ACCEPTED-GENERATION-PLAN-RUNTIME-STUDIO-BRIDGE-20260702.md
```
