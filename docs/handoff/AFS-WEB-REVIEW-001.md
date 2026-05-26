# AFS-WEB-REVIEW-001 Handoff

Status: `DONE`

Date: 2026-05-27

Branch: `codex/afs-web-review-loop`

Worktree:
`C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-review-loop`

## Scope

Local Alpha 0.3 Web operator loop: workflow selection, plan generation,
supervised run, artifact inspection, review refresh, and feedback capture.

## Changes

- Upgraded the Production Mode acceptance path from Local Alpha 0.2 wording to
  a Local Alpha 0.3 operator loop.
- Added an operator-loop status box that surfaces workflow selection, plan,
  run, artifact inspection, review refresh, and feedback capture state.
- Added a run feedback capture state that updates only in memory after the
  operator generates/copies `run_feedback_event` JSON.
- Extended run-level feedback JSON with `review_status`, `review_report`, and
  `quality_report` refs after review refresh.
- Added a controller-side regression check for the state path where run polling
  refreshes `productionState.run` after review refresh; feedback JSON now falls
  back to `productionState.review` so review evidence is not lost.
- Kept Review Mode explicit-file-only and Production Mode bridge-backed only.

## Verification

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
# 44 passed

node --check apps/web/app.js
node --check apps/web/app-elements.js
node --check apps/web/feedback-wiring.js
node --check apps/web/feedback-event.js
node --check apps/web/production-mode.js
node --check apps/web/production-render.js
node --check apps/web/production-workflows.js
node --check apps/web/artifact-values.js
node --check apps/web/video-preview.js
node --check apps/web/artifact-contracts.js
node --check apps/web/artifact-ledgers.js
node --check apps/web/artifact-workspace.js
node --check apps/web/render-helpers.js
node --check apps/web/ui-copy.js
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall apps\web_bridge apps\cli tests
# passed

git diff --check
# passed with Windows LF/CRLF warnings only
```

## Browser Smoke

Local servers:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m http.server 8769 -d apps/web --bind 127.0.0.1
```

Desktop smoke:

- Opened `http://127.0.0.1:8769/index.html`.
- Switched to Production Mode.
- Selected the mock demo workflow.
- Used temp output under
  `C:\Users\chenzy\AppData\Local\Temp\afs-web-review-loop-smoke\`.
- Generated `workflow_plan.json`.
- Ran `mock_text_to_slices` to `success`.
- Confirmed artifact inspection listed 11 run files.
- Refreshed review to `passed`.
- Generated run feedback JSON with `review_report` and `quality_report` refs.
- Confirmed no browser console errors.
- Controller re-smoke confirmed `run_feedback_event` includes
  `review_status=passed`, `review_report`, and `quality_report`.
- Screenshot:
  `C:\Users\chenzy\AppData\Local\Temp\afs-web-review-loop-smoke\desktop-operator-loop.png`

Narrow smoke:

- Set viewport to 390 x 844.
- Confirmed Production Mode path, readiness, form, and operator-loop status fit
  within the viewport with no horizontal overflow.
- Generated a mock demo plan from the narrow viewport.
- Ran `mock_text_to_slices` to `success`.
- Refreshed review to `passed`.
- Generated run feedback JSON with `review_report` and `quality_report` refs.
- Confirmed no browser console errors.
- Controller re-smoke confirmed no horizontal overflow and complete review refs
  at 390 x 844.
- Screenshot:
  `C:\Users\chenzy\AppData\Local\Temp\afs-web-review-loop-smoke\narrow-full-operator-loop.png`

## Boundaries

- No browser persistence was added: no `localStorage`, IndexedDB, cookies, or
  file-system write picker.
- No upload, SaaS, cloud backend, provider config, or remote provider call was
  added.
- Browser feedback capture is copy/export only. It does not write
  `feedback.jsonl`.
- Smoke screenshots, if saved, belong outside the repository.

## Risks

- Human/product acceptance remains separate from structure and runtime
  verification.
- The Web UI still does not implement true step-level pause/resume or
  rerun-from-step.
- In the first browser automation attempt, the default in-app browser viewport
  could not click the plan button until an explicit desktop viewport was set.
  Narrow responsive layout itself passed at 390 px.
