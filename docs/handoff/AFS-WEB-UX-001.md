# AFS-WEB-UX-001 Handoff

Status: `DONE`

Date: 2026-05-27

Branch: `codex/afs-web-ux-pass`

Worktree:
`C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ux-pass`

## Scope

Improved the local Web workbench for Local Alpha 0.2 acceptance without adding
SaaS, browser persistence, provider configuration, remote provider calls, or
automatic local directory scanning.

## Changes

- Added a Production Mode `Local Alpha 0.2 验收路径` panel that shows the
  operator path from bridge health to plan generation, local run, review
  refresh, and Review Mode artifact inspection.
- Added a dynamic next-action chip and detail text so blockers, bridge state,
  plan state, run state, and review state tell the user what to do next.
- Tightened bridge workflow profile guidance:
  - demo workflows now point users to refresh review after a successful local
    demo run;
  - product workflows now tell users to fix local media/dependency blockers
    before generating a plan.
- Documented that source files are UTF-8 and that some Windows terminals may
  show terminal mojibake even when browser-rendered Chinese copy is correct.
- Extended static tests to assert readable Chinese copy, the acceptance path,
  local-only bridge behavior, and the no-browser-persistence boundary.

## Verification

Required verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
# 42 passed

node --check apps/web/app.js apps/web/app-elements.js apps/web/feedback-wiring.js apps/web/feedback-event.js apps/web/production-mode.js apps/web/production-render.js apps/web/production-workflows.js apps/web/artifact-values.js apps/web/video-preview.js apps/web/artifact-contracts.js apps/web/artifact-ledgers.js apps/web/artifact-workspace.js apps/web/render-helpers.js apps/web/ui-copy.js
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall apps/web_bridge apps/cli tests
# passed

git diff --check
# passed with Windows LF/CRLF warnings only
```

Browser smoke:

- Started `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787`.
- Started `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m http.server 8769 -d apps/web --bind 127.0.0.1`.
- Opened `http://127.0.0.1:8769/index.html`.
- Confirmed Review Mode renders readable Chinese copy.
- Switched to Production Mode and confirmed `bridge ready`, the
  `Local Alpha 0.2 验收路径` panel, and no browser console errors.
- The first local re-smoke found a real small-screen interaction bug: the
  sticky topbar could cover Production Mode buttons, so clicks hit the top stat
  cards instead of workflow controls. `apps/web/styles.css` now disables sticky
  topbar behavior at the responsive breakpoint, and a static regression check
  records that boundary.
- Selected `mock_text_to_slices`.
- Used temp output:
  `C:\Users\chenzy\AppData\Local\Temp\afs-web-ux-smoke-main\mock_text_to_slices`.
- Generated `workflow_plan.json`, ran workflow to `success`, listed run
  artifacts, and refreshed review to `passed`.
- Removed the temp smoke output directory after verification.
- Smoke screenshot saved outside the repo at
  `C:\Users\chenzy\AppData\Local\Temp\afs-web-ux-pass-smoke-main.png`.

## Boundaries

- Review Mode remains explicit-file-only and local-only.
- Production Mode still connects only to `http://127.0.0.1:8787`.
- No `localStorage`, IndexedDB, cookies, upload, SaaS, provider-secret, or
  browser persistence surface was added.
- No remote LLM, ASR, image, video provider, or external download was called.
- Browser smoke, if run, should use a temp output directory outside
  `data/processed` to avoid committing or modifying generated repo artifacts.

## Risks

- `apps/web/index.html` remains above the 300-line guideline because it is the
  existing static shell. New behavior was kept in focused JS/CSS modules.
- The terminal mojibake issue is partly an environment display problem, not a
  browser/source encoding problem; the README records the review workaround.
