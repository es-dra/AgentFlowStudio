# AFS Web Workflow Controls 001

Status: implementation slice in progress.

Date: 2026-06-09

## Scope

This slice moves `apps/workbench` from a read-only Runtime Service shell toward
a usable content-production workbench. The UI still consumes Runtime Service
only and does not execute CLI internals or providers from the browser.

## Implemented

- Project Hub: create, open, import, and export project manifests.
- Stage Navigation: switch Workbench views through Projects, Create, Assets, Review, Style Memory, Jobs, and Settings rail items.
- Project Hub Templates: prefill project type, goal, and safe manifest import JSON.
- Asset Library: register safe source asset/reference summaries through Runtime Service.
- Source Presets: prefill brief, visual reference, and script outline summaries.
- Reference Library: render attached brief/reference/script safe summaries as product-facing cards.
- Draft Canvas: generate Hook / Proof / CTA scene cards from safe source summaries.
- Scene Planner: register safe scene/content cards through Runtime Service.
- Creation Workspace: render user-facing Create canvas from backend `creation_workspace`.
- Scene / Shot Inspector: edit prompt, reference summary, style direction, and retry intent for the selected scene card.
- Filmstrip: render the content-card production sequence.
- Run Controls: trigger the deterministic first asset check.
- Review Room: compare planned scene, first-check, and next-round candidates before recording decisions.
- Review: record raw feedback evidence and keep/revise/reject review decisions.
- Style Memory: render profile count, reusable preferences, latest profile ref, and next-pass usage in product language.
- Memory Workspace: combine review candidates, feedback controls, style profile reuse, and next-round controls from backend `memory_workspace`.
- Job Center: render runtime job progress, safe artifact refs, and blocked-action guidance.
- Job Center Polling: auto-refresh current-project runtime state through Runtime Service.
- Operations Workspace: combine runtime job queue, latest activity, provider preflight, provider controls, polling, and blocker counts from backend `operations_workspace`.
- Studio Workspace: render the Create view as one product-facing workbench that combines command strip, reference rail, production canvas, inspector, filmstrip, style memory, review queue, runtime summary, and safe artifact navigation from backend `studio_workspace`.
- Project Readiness: render current action, workflow gate statuses, and non-claim badges from backend state.
- Activity Timeline: render runtime activity counts, latest jobs, blocked actions, and safe primary artifact refs.
- Production Board: render source, draft, first check, review, style memory, next round, and provider gate as product-facing lanes.
- Command Hub: translate backend workflow actions into user-facing primary and stage commands.
- Project Hub Overview: render active project, safe counts, next command, recent jobs, and the manifest artifact ref.
- Vertical Flow Response: Runtime mutations now return a compact `flow` summary with target status, current action, next command, Studio status, provider status, and non-claims.
- Empty Workspace Start: when no project is loaded, the Workbench still exposes project create/open controls instead of a dead "open project" page.
- Cross-stage Command Navigation: Studio Workspace can navigate to Assets, Review, or Jobs for the current primary command instead of disabling cross-stage steps.
- Next Round: trigger two-round validation from the latest Round 1 job.
- Provider Preflight: create provider validation-plan evidence without live calls.
- Safe Artifact Panel: render artifact-specific report views with collapsed JSON Detail.
- Runtime-hosted Entry: Runtime Service serves the Workbench at `/workbench/`
  for browser QA and frontend/backend integration.
- Frontend state adapter: accepts backend `cards/card_id/primary_artifact_id` shape plus `project_readiness`, `production_board`, `creation_workspace`, `memory_workspace`, `operations_workspace`, `filmstrip`, `review_room`, `style_memory`, `job_center`, and `activity_timeline`.
- Frontend readiness adapter: normalizes `project_readiness` and maps backend workflow actions to existing UI action ids.
- UI module split: `dom.js`, `runtime-client.js`, `presets.js`, `input-sync.js`, `app-selection.js`, `app-actions.js`, `workbench-state.js`, `readiness-state.js`, `activity-state.js`, `production-board-state.js`, `project-hub-state.js`, `creation-workspace-state.js`, `memory-workspace-state.js`, `operations-workspace-state.js`, `render-actions.js`, `render-assets.js`, `render-artifact.js`, `render-jobs.js`, `render-readiness.js`, `render-activity.js`, `render-production-board.js`, `render-project-hub.js`, `render-creation-workspace.js`, `render-memory-workspace.js`, `render-operations-workspace.js`, `render.js`, `app.js`.
- View-specific controls: `renderActionPanel` accepts control groups so each stage can avoid showing every operation at once.

## Runtime Contract Added

- `POST /projects/{project_id}/source-assets`
- `POST /projects/{project_id}/content-cards`
- `POST /projects/{project_id}/canvas-draft`
- `POST /projects/{project_id}/scene-inspector`
- `POST /projects/{project_id}/review-decisions`
- `GET /projects/{project_id}/workbench-state` now includes `project_readiness`, `project_hub`, `command_hub`, `production_board`, `creation_workspace`, `memory_workspace`, `operations_workspace`, `studio_workspace`, `asset_library`, `filmstrip`, `review_room`, `style_memory`, `job_center`, and `activity_timeline`.
- Mutating Runtime responses on the Workbench main path include `flow`, a compact safe summary for frontend navigation and "next action" rendering.
- `GET /workbench/` serves the static Workbench shell from Runtime Service.

Write paths store safe summaries and safe review evidence only. They do not persist private local
paths, media bytes, signed URLs, provider raw responses, or secrets.

## Boundaries

- Browser does not call providers.
- Browser does not execute Python, CLI, or workflow internals.
- Browser does not scan local directories.
- Browser does not persist secrets, signed URLs, private local assets, or generated media bytes.
- Raw feedback remains evidence, not durable memory.
- Runtime success does not claim human acceptance or business validation.
- Provider preflight does not claim provider output is production-ready.

## Current Gaps

- Browser screenshot QA is still pending. Current execution environment did not
  expose an in-app Browser controller, Playwright, or Edge/Chrome headless
  binary.
- Provider-gated real model smoke is intentionally deferred until deterministic Web flow is stable.
- Browser click-through proof for the full vertical flow is still pending; current proof is API-level deterministic flow plus static frontend contract tests and HTTP/static resource smoke.

## Next Implementation Order

1. Add browser screenshot QA once a Browser or Playwright runtime is available.
2. Add provider-gated real model smoke only after the deterministic Web flow is
   stable and capability gates are explicitly authorized.

## Verification

Verification after this slice:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_actions.py tests\test_api_runtime_workbench_state.py tests\test_api_runtime_workbench_studio.py tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py -q
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

Result:

- Latest focused verification after Review Room / Job Center extension:
  `15 passed, 1 warning`.
- Latest focused verification after Reference Library / polling extension:
  `22 passed, 1 warning`.
- Latest focused verification after Project Hub template / module split extension:
  `22 passed, 1 warning`.
- Latest focused verification after Runtime-hosted Workbench entry:
  `23 passed, 1 warning`.
- Latest focused verification after Draft Canvas integration:
  `24 passed, 1 warning`.
- Latest focused verification after Project Readiness integration:
  `24 passed, 1 warning`.
- Latest focused verification after Stage Navigation integration:
  `25 passed, 1 warning`.
- Latest focused verification after Activity Timeline integration:
  Activity state/Web foundation `10 passed, 1 warning`; Web foundation after
  artifact-ref handler fix `9 passed`; focused Runtime/Web/API `26 passed, 1
  warning`.
- Latest focused verification after Production Board integration:
  Production Board state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API `26 passed, 1 warning`.
- Latest focused verification after Command Hub integration:
  Command Hub state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API/action suite `18 passed, 1 warning`.
- Latest focused verification after Project Hub overview integration:
  Project Hub state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API/action suite `18 passed, 1 warning`.
- Latest focused verification after Creation Workspace projection:
  Creation Workspace state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API/action suite `18 passed, 1 warning`.
- Creation Workspace HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/styles-creation-workspace.css`, and
  `/workbench/src/render-creation-workspace.js` returned `200`; a drafted
  temporary project returned `creation_workspace.status =
  ready_for_first_check`, `selected_card_id = draft-hook`, `canvas_cards = 4`,
  `filmstrip_items = 3`, and `primary_action = start_first_generation_check`.
- Latest focused verification after Memory Workspace projection:
  Memory Workspace state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API/action suite `18 passed, 1 warning`.
- Memory Workspace HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-memory-workspace.js`, and
  `/workbench/src/memory-workspace-state.js` returned `200`; deterministic
  smoke returned `memory_workspace.status = ready`, 2 candidates, 1 profile
  version, and enabled feedback controls.
- Latest focused verification after Operations Workspace projection:
  Operations Workspace state/Web foundation `11 passed, 1 warning`; focused
  Runtime/Web/API/action suite `18 passed, 1 warning`.
- Operations Workspace HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-operations-workspace.js`, and
  `/workbench/src/operations-workspace-state.js` returned `200`; deterministic
  smoke returned `operations_workspace.status = blocked`, 4 jobs, and provider
  action `resolve_provider_preflight`.
- Latest focused verification after Studio Workspace integration:
  Studio Workspace state/Web `3 passed, 1 warning`; focused Runtime/Web/API/Web
  suite `23 passed, 1 warning`.
- Latest focused verification after Vertical Flow slice:
  focused Runtime/Web/API/Web vertical-flow suite `31 passed, 1 warning`;
  full pytest `844 passed, 1 warning`; maintenance audit `failed=0,
  warning=0`; `git diff --check` passed.
- Vertical Flow HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render.js`, and
  `/workbench/src/render-studio-workspace.js` returned `200`; deterministic
  Runtime posts reached `draft_canvas` after project creation and source asset
  registration.
- Studio Workspace HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-studio-workspace.js`, and
  `/workbench/styles-studio-workspace.css` returned `200`; a temporary project
  returned `studio_workspace.status = needs_assets`, 2 canvas cards, and
  provider status `ready_not_run`.
- Project Hub HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/styles-project-hub.css`, and
  `/workbench/src/render-project-hub.js` returned `200`; a temporary project
  returned `project_hub.title = Project hub` and next command
  `add_reference -> register-source-asset`.
- Command Hub HTTP smoke on a temporary port: `/workbench/` and
  `/workbench/styles-command-hub.css` returned `200`; a temporary project
  returned `command_hub.primary_command = add_reference ->
  register-source-asset`.
- Production Board HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-production-board.js`, and
  `/workbench/styles-production-board.css` returned `200`; a temporary project
  returned `production_board.status = needs_assets` and 7 lanes.
- Full pytest after Production Board integration: `837 passed, 1 warning`.
- Activity Timeline HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-activity.js`, and `/workbench/styles-activity.css`
  returned `200`; a temporary project returned `activity_timeline.counts.total =
  1` and first action `draft_canvas`.
- Stage Navigation HTTP smoke on a temporary port: `/workbench/` and
  `/workbench/src/render.js` returned `200`; the served renderer contained
  `activeView`, `viewActionGroups`, and `data-view`.
- Project Readiness HTTP smoke on a temporary port: `/workbench/`,
  `/workbench/src/render-readiness.js`, and `/workbench/styles-readiness.css`
  returned `200`; a temporary project returned `project_readiness.status =
  needs_assets` and `workspace.primary_action = add_reference`.
- Draft Canvas HTTP smoke on a temporary port: `draft_canvas succeeded`, 3
  generated cards, 3 filmstrip items, and `/workbench/` returned `200`.
- Runtime HTTP smoke on a temporary port: `/health`, `/workbench/`, and
  `/workbench/src/app.js` returned `200` with expected shell/module content.
- Broader focused Runtime/Web/API verification: `22 passed, 1 warning`.
- Earlier foundation verification: `21 passed, 1 warning`.
- CLI help/version passed.
- `maintenance_audit`: `failed=0, passed=6, warning=0`.
- Retention review: `delete_candidate_count=0`, `manual_review_required_count=0`.
- Full pytest: `837 passed, 1 warning`.
- `git diff --check` passed with CRLF normalization warnings only.
