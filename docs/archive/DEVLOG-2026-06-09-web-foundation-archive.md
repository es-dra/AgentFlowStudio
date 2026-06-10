# DEVLOG Archive - 2026-06-09 Web Foundation

This archive preserves early Web Workbench log sections moved out of `DEVLOG.md` to keep the active development log below the maintenance-audit line limit.

## 2026-06-09 - Web Vertical Flow 001

- Started `AFS-WEB-VERTICAL-FLOW-001`: deterministic Workbench path from empty project toward `ready_for_next_round`.
- Added API-level vertical flow coverage for create project -> source summaries -> Draft Canvas -> inspector -> first deterministic check -> review decision -> two-round validation -> provider preflight readiness.
- Added compact `flow` summaries to Runtime mutation responses so the frontend can show target status, current action, next command, Studio status, provider status, and non-claims without re-inferring the workflow.
- Improved Workbench startup and navigation: empty workspace now exposes project create/open controls; Studio cross-stage commands navigate to the matching view; Project Hub no longer renders an empty-action Pending button.
- Added browser-level Workbench smoke: Runtime Service starts on a temporary port, Chromium clicks create -> source summary -> draft -> first check -> Review decision -> next round, and reaches `ready_for_next_round`.
- Tightened the main review action toward candidate-bound `record-review-decision`; generic `record-feedback` remains an auxiliary runtime control.
- Fixed Production Board layout after screenshot QA exposed right-column clipping; command/board surfaces now span the workbench width and board lanes wrap.
- Boundaries preserved: no live provider call, no secret, no signed URL, no private media bytes, no provider raw response, no durable-memory or human-acceptance claim.

## 2026-06-09 - Web Foundation 001

- Added Runtime Service workbench-state projection for frontend-facing project/canvas/events/provider status.
- Kept provider execution backend-gated and surfaced only safe UI summary for provider preflight state.
- Added `apps/workbench` as the new Runtime Service-backed product frontend foundation, separate from transitional `apps/web`.

## 2026-06-09 - Web Provider Smoke Readiness Prep

- Added `docs/handoff/AFS-WEB-PROVIDER-SMOKE-READINESS-001.md` to separate Web RC human acceptance from later capability-gated provider smoke.
- Registered the handoff in `docs/handoff/INDEX.md` and updated `AFS-PROVIDER-GATED-REAL-SMOKE-001` in `TASK_TRACKER.md`.
- Ran readiness-only provider gate without `--run-provider-validation`; it wrote ignored evidence under `data/processed/runs/web_rc_provider_gate_readiness/` with `status=blocked` and `provider_calls_started=false`.
- Boundaries unchanged: provider not executed; no secret, local private material, provider raw response, signed URL, generated media byte, COS active rule, human acceptance claim, business validation claim, or durable memory promotion.
- Implemented runtime client, workbench-state normalizer, DOM renderer, canvas workspace shell, inspector, jobs lane, provider gate panel, and collapsed advanced diagnostics.
- Added local Runtime Service CORS for localhost and direct file-origin workbench use.
- Classified `apps/workbench` in retention policy as current production spine.
- Added focused frontend boundary tests to prevent browser persistence, old bridge/CLI coupling, private local data references, and oversized new frontend files.
- Added implementation handoff: `docs/handoff/AFS-WEB-FOUNDATION-001.md`.

Boundaries:

- No live provider call was started.
- No secret, signed URL, private media, provider raw response, or generated media bytes were written.
- This is not human acceptance, business validation, or durable memory.
- `apps/workbench` is still a foundation; project-create/run/feedback actions are the next slice.

## 2026-06-09 - Web Workflow Controls 001

- Advanced `apps/workbench` from a read-only state shell to Runtime Service workflow controls.
- Added project create/open/import/export actions, deterministic Round 1 asset-test trigger, raw feedback recording, Round 2 validation trigger, provider preflight trigger, and safe artifact loading.
- Split frontend rendering into smaller modules: `dom.js`, `render-actions.js`, and `render-artifact.js`.
- Updated the frontend state adapter to consume backend `cards/card_id/primary_artifact_id` workbench-state payloads.
- Added workflow-control assertions to `tests/test_web_workbench_foundation.py`.
- Added handoff: `docs/handoff/AFS-WEB-WORKFLOW-CONTROLS-001.md`.
- Added Runtime Service static hosting for the Workbench at `/workbench/`, so frontend/backend integration can start from the same service origin instead of a file-only shell.
- Added deterministic Draft Canvas flow: Runtime Service now turns safe brief/reference/script summaries into Hook / Proof / CTA canvas cards, and Workbench exposes this as a one-click Scene Planner action.

Boundaries:

- No live provider call was started.
- Browser-side workflow execution was not introduced; all execution still goes through Runtime Service.
- No secret, signed URL, private media, provider raw response, or generated media bytes were written.
- HTTP smoke for `/workbench/` passed through a temporary Runtime Service; Draft Canvas HTTP smoke created 3 canvas cards and a 3-item filmstrip; browser screenshot QA was still pending in that environment.

## 2026-06-09 - Workbench Projection Slices

- Added backend-driven `creation_workspace` and `memory_workspace` projections for Create and Review/Style Memory views.
- Split Create and Memory frontend state/render modules, removed obsolete `render-review.js`, and reduced `workbench-state.js` below the 300-line threshold.
- Runtime HTTP smoke passed for the new static modules and deterministic projection states; no live provider, secret, signed URL, private media, provider raw response, or generated media bytes were written.

## 2026-06-09 - Workbench Operations Workspace Slice

- Added backend-driven `operations_workspace` projection, combining job queue, latest activity, provider preflight, provider controls, polling, and blocker counts into one Runtime Service-safe contract.
- Added frontend Operations Workspace state/render modules and moved Job Center normalization out of `workbench-state.js`, reducing the total adapter to 184 lines.
- Replaced the Jobs view's parallel Job Center / Activity / Provider Gate panels with one Operations Workspace product surface.
- Boundaries preserved: no provider calls, no secrets, no private paths, no signed URLs, no media bytes, no provider raw responses, no human acceptance/business validation/durable-memory claim.
- Focused verification: state/Web foundation `11 passed, 1 warning`; Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Operations Workspace HTTP smoke passed.

## 2026-06-10 - LibTV History Assets Panel QA

- Completed the first browser QA closure for the Create bottom-toolbar `历史资产` panel.
- Fixed the history asset card summary style so long safe summaries wrap inside cards instead of reporting text overflow.
- Browser evidence recorded `panelVisible=true`, `cardCount=6`, `gridVisible=true`, `consoleErrorCount=0`, `overflowCount=0`, `forbiddenMatches=[]`, `providerStartedClaimVisible=false`, and `internalIdLeakVisible=false`.
- Evidence: `data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix.png` and `data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix-metrics.json`.
- Boundaries unchanged: no live provider call, no secret/private media/provider raw response/signed URL/generated media byte committed, and no human acceptance/business validation/durable memory claim.
