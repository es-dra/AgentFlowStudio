# AFS Web Foundation 001

Status: first implementation slice complete.

## Scope

This handoff records the first concrete Web Workbench foundation after the
landing-prep planning slice.

Implemented surfaces:

- `GET /projects/{project_id}/workbench-state` Runtime Service endpoint.
- Backend workbench-state builder and canvas card/event projection modules.
- Safe provider preflight summary surfaced through job UI summary.
- Local Runtime Service CORS for localhost and direct file-origin workbench use.
- New frontend app shell under `apps/workbench`.
- Runtime client, state normalizer, DOM renderer, and product styling.
- Focused tests for Runtime Service state projection and frontend boundaries.

## Product Direction

The default workbench screen is a product workspace, not an architecture diagram.
It should feel close to existing canvas production tools:

- left navigation and project controls;
- central creation canvas;
- selected card inspector;
- job/event lane;
- provider preflight panel;
- advanced diagnostics collapsed by default.

AFS-specific evidence, memory, harness, and trace details are still preserved, but
they are not the default user mental model.

## Backend Contract

Frontend should prefer:

```text
GET /projects/{project_id}/workbench-state
```

The response is frontend-facing and includes:

- navigation labels;
- canvas cards;
- project events;
- provider gate summary;
- advanced evidence policy and non-claims.

The browser should not reconstruct this state from private runtime files or CLI
internals.

## Frontend Boundary

The current `apps/workbench` foundation:

- uses Runtime Service only;
- keeps browser state in memory;
- does not call providers from the browser;
- does not persist secrets or private media;
- does not execute Python or CLI internals;
- does not scan directories;
- does not claim human acceptance, business validation, or durable memory.

## Verification

Focused checks completed in this slice:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_workbench_state.py tests\test_cli_command_registry_boundaries.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py -q
node --check apps\workbench\src\runtime-client.js
node --check apps\workbench\src\workbench-state.js
node --check apps\workbench\src\render.js
node --check apps\workbench\src\app.js
```

Latest focused result before broader verification:

- Runtime/API/Web focused: `24 passed, 1 warning`.
- Web foundation focused: `5 passed`.
- Retention review: `manual_review_required_count=0` after classifying
  `apps/workbench` as current production spine.

## Next Slice

Recommended next implementation order:

1. Add project create/open/import/export controls to `apps/workbench`.
2. Wire Round 1 asset-test request forms to Runtime Service.
3. Render real asset-test and two-round artifacts behind safe artifact refs.
4. Add raw feedback submission.
5. Add Round 2 validation action from the selected Round 1 job.
6. Add browser QA screenshots and responsive checks.
7. Only then consider provider-gated real model smoke.
