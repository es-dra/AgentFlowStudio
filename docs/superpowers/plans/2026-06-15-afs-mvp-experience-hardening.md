# AFS MVP Experience Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 2026-06-15 third-party Studio feedback into a low-risk MVP hardening slice that improves internal-test reliability, makes fixed-asset carry visible, and records human quality feedback without claiming video localized editing is productized.

**Architecture:** Keep Runtime Service as the only frontend backend boundary. Add safe health/status projection in Runtime, then reuse existing Studio state, context bundle, asset detail, video poll/cancel, and `/feedback` contracts to improve the user surface. No provider calls are required for implementation or verification.

**Tech Stack:** Python 3.12/FastAPI Runtime Service, vanilla JS Studio under `apps/studio/`, pytest static/API coverage, Node `--check`, existing safe manifest and provider gate conventions.

---

## Operating Boundaries

- Branch/worktree: `codex/afs-mvp-experience-hardening-20260615` at `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-mvp-experience-hardening-20260615`.
- Source feedback: `D:\Projects\AgentFlowStudio\AFS_Studio_评估与体验建议.md` is currently untracked in the main checkout. Do not copy it wholesale into repo history unless the user explicitly asks.
- Pre-existing untracked script: `D:\Projects\AgentFlowStudio\tools\run_studio_all_gates.ps1` is not part of the clean worktree and must not be blindly adopted because it opens ASR.
- Provider gates: remain closed during implementation and automated tests. Any launch script must keep ASR off by default and must not print secrets.
- Claim boundary: this slice can improve internal-test readiness. It cannot claim human acceptance, business validation, or guaranteed video localized editing.

## Reference Borrowing Summary

**Task:** Improve `/studio/` internal-test reliability and make the asset-memory loop visibly trustworthy.

**Referenced:**
- Figma/FigJam: borrow the idea of canvas tidy/visible organization, but defer heavy layout automation to a later UI slice.
- ComfyUI: borrow node-graph clarity and compact node-state visibility, not its full workflow model.
- Krea/Runway: borrow visible generation state and explicit video edit boundaries, not real-time generation or provider-specific editing claims.
- Existing AFS: reuse `lastContextBundle`, `visualAssets`, asset detail popover, `pollVideo`, `cancelVideo`, and `/feedback`.

**Decision:** Implement P0/P1 reliability and trust surfaces first: health self-check, safe launch script, carry-chain visibility, unified reference inspection, generation status/cancel boundary, and structured quality scoring.

**Deliberately not adopting:** no new frontend framework, no new graph library, no live provider test by default, no ASR gate, no claim that Kling I2V can do deterministic frame-level edits.

## File Map

- Modify: `apps/api/runtime_studio_static.py`
  - Add a safe Studio static status helper that checks root, index, and key entry files without exposing absolute local paths.
- Modify: `apps/api/runtime_info.py`
  - Add `studio_static` and `provider_gates` safe projections to `/health`; include booleans only and safe labels.
- Modify: `apps/api/runtime_service.py`
  - Pass Studio static status into health payload.
- Modify: `tests/test_api_runtime_service.py`
  - Add coverage for mounted/missing Studio static status and provider gate isolation.
- Create: `tools/run_studio_internal_test.ps1`
  - Safe local internal-test launcher; opens LLM/image/video only when requested, keeps ASR closed by default, avoids printing secrets.
- Test: likely `tests/test_studio_internal_launcher.py`
  - Text-level safety contract for the launcher: ASR default off, no secret echoing, repo-root guard, port 8790 default.
- Modify: `apps/studio/src/canvas-view.js`
  - Add always-visible compact carry-chain strip for nodes with `visualAssets` or `lastContextBundle.included_assets`.
- Create or Modify: `apps/studio/src/asset-reference-summary.js`
  - Centralize safe asset summary normalization for canvas badge, result bundle, and reference inspector.
- Modify: `apps/studio/src/node-result-view.js`
  - Reuse centralized asset summary labels and keep post-generation context detail consistent with node carry strip.
- Modify: `apps/studio/src/optimizer.js` and/or `apps/studio/src/node-actions.js`
  - Consolidate visible "mentioned fixed asset but not connected" behavior into one inspector function; keep fail-closed before paid submit.
- Modify: `apps/studio/styles/*.css`
  - Add compact carry-chain, generation progress, scoring strip, and tooltip styles without enlarging default nodes.
- Modify: `apps/studio/src/node-actions.js`, `apps/studio/src/canvas-view.js`, `apps/studio/src/node-result-view.js`
  - Improve generating/video poll/cancel status text and explicit local-cancel billing boundary.
- Modify: `apps/studio/src/runtime-client.js`
  - Expose `recordFeedback` if not already present.
- Create or Modify: `apps/studio/src/quality-feedback.js`
  - Small UI component that records structured raw feedback via `/feedback` for identity similarity, wardrobe consistency, scene continuity, watermark/text, target-change success, and drift notes.
- Modify: `tests/test_web_studio_static.py`
  - Add static markers for carry chain, inspector reuse, safe launch/status text, and scoring UI.
- Modify: `TASK_TRACKER.md`, `BACKLOG.md`, `DEVLOG.md`, `docs/handoff/INDEX.md`
  - Record implementation scope, verification, and remaining non-goals.
- Create: `docs/handoff/AFS-MVP-EXPERIENCE-HARDENING-20260615.md`
  - Safe handoff with before/after, verification, and remaining risk.

## Chunk 1: Runtime Self-Check And Safe Launcher

### Task 1.1: Add Studio Static Status To Runtime Health

**Files:**
- Modify: `apps/api/runtime_studio_static.py`
- Modify: `apps/api/runtime_info.py`
- Modify: `apps/api/runtime_service.py`
- Test: `tests/test_api_runtime_service.py`

- [ ] **Step 1: Write failing tests**
  - Add assertions that `/health` contains:
    - `studio_static.mounted`
    - `studio_static.root_exists`
    - `studio_static.index_exists`
    - `studio_static.entry_js_exists`
    - `studio_static.status` in `ready|missing|incomplete`
    - no `D:\`, `C:\`, `api_key`, `token`, or `signed_url`.
  - Add a missing-root app case using a temp path and assert `status == "missing"` without absolute path leakage.

- [ ] **Step 2: Run focused test and confirm red**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets -q`
  - Expected: fail because health lacks `studio_static`.

- [ ] **Step 3: Implement safe status helper**
  - Add a helper that accepts `studio_root: Path` and returns booleans plus a safe status code.
  - Do not include local absolute paths in the response.
  - Keep `configure_studio_static()` behavior compatible, but make missing/incomplete state observable through health.

- [ ] **Step 4: Run focused tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py -q`
  - Expected: pass.

### Task 1.2: Add Provider Gate Projection To Health

**Files:**
- Modify: `apps/api/runtime_info.py`
- Test: `tests/test_api_runtime_service.py`

- [ ] **Step 1: Write failing gate tests**
  - With no env vars set, assert all `provider_gates` values are false.
  - With only LLM/image/video set, assert ASR and external download remain false.
  - Assert serialized health has no provider config path or secret-like values.

- [ ] **Step 2: Implement gate projection**
  - Add a helper that reads only env-gate booleans:
    - `llm`, `image`, `video`, `asr`, `external_download`.
  - Never include `AFS_PROVIDER_CONFIG` value.

- [ ] **Step 3: Run focused tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py -q`
  - Expected: pass.

### Task 1.3: Create Safe Internal-Test Launcher

**Files:**
- Create: `tools/run_studio_internal_test.ps1`
- Test: `tests/test_studio_internal_launcher.py`

- [ ] **Step 1: Write text-level launcher safety test**
  - Assert the script sets `AFS_ALLOW_REMOTE_ASR` to false or removes it by default.
  - Assert LLM/image/video are opt-in switches or clearly controlled parameters.
  - Assert it does not print the provider config contents.
  - Assert default host/port are `127.0.0.1:8790`.

- [ ] **Step 2: Implement launcher**
  - Parameters:
    - `-AllowLLM`
    - `-AllowImage`
    - `-AllowVideo`
    - `-ProviderConfig`
    - `-Port`
  - Default all remote provider gates false.
  - Default ASR false and do not expose an ASR switch in this MVP launcher.
  - Verify it is run from repo root or resolves repo root from script path.
  - Print gate booleans and whether provider config exists, not the provider config path contents.

- [ ] **Step 3: Run launcher tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_studio_internal_launcher.py -q`
  - Expected: pass.

## Chunk 2: Carry-Chain Visibility And Reference Consistency

### Task 2.1: Centralize Asset Summary Normalization

**Files:**
- Create: `apps/studio/src/asset-reference-summary.js`
- Modify: `apps/studio/src/canvas-view.js`
- Modify: `apps/studio/src/node-result-view.js`
- Test: `tests/test_web_studio_static.py`

- [ ] **Step 1: Add static tests for new module and imports**
  - Assert `asset-reference-summary.js` exists.
  - Assert `canvas-view.js` and `node-result-view.js` import from it.
  - Assert labels for character, scene, excluded, retired, superseded, and subject-reference are centralized.

- [ ] **Step 2: Implement normalization helpers**
  - Export:
    - `assetIdFromRef(ref)`
    - `assetLabel(ref)`
    - `assetTypeLabel(ref)`
    - `assetCarryState(ref)`
    - `assetsFromNode(node)`
    - `assetsFromBundle(bundle)`
  - Helpers must tolerate missing fields and return safe display strings only.

- [ ] **Step 3: Replace duplicate label logic**
  - Use helpers in `canvas-view.js` and `node-result-view.js`.
  - Keep existing behavior for result bundle details.

- [ ] **Step 4: Run static tests and JS checks**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py -q`
  - Run: `node --check` across `apps/studio/**/*.js`.

### Task 2.2: Add Always-Visible Carry Chain Strip

**Files:**
- Modify: `apps/studio/src/canvas-view.js`
- Modify: `apps/studio/styles/*.css`
- Test: `tests/test_web_studio_static.py`

- [ ] **Step 1: Add static markers**
  - Assert `carry-chain-strip`, `carry-chain-chip`, and `data-action="asset-detail"` exist.
  - Assert strip uses `lastContextBundle` when available and falls back to `visualAssets`.

- [ ] **Step 2: Implement compact strip**
  - Show up to 4 assets under the title or at the top of the body.
  - Include icon/color distinction for character vs scene.
  - Add invalid state for retired/excluded/superseded.
  - Clicking a chip opens existing asset detail popover.
  - Keep it compact so node dimensions do not jump badly.

- [ ] **Step 3: Run static tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py -q`

### Task 2.3: Unify Mentioned-But-Unconnected Asset Inspector

**Files:**
- Create or modify: `apps/studio/src/asset-reference-inspector.js`
- Modify: `apps/studio/src/optimizer.js`
- Modify: `apps/studio/src/node-actions.js`
- Test: `tests/test_web_studio_static.py`

- [ ] **Step 1: Add static tests**
  - Assert one exported inspector function is used by optimizer and generation preflight.
  - Assert markers for `connect-named-asset`, `named_asset_not_connected`, and fail-closed submit remain.

- [ ] **Step 2: Extract common inspector**
  - Normalize warnings from preflight/context bundle into one list of actions.
  - Keep optimizer UI non-blocking.
  - Keep generation preflight blocking before paid submit.

- [ ] **Step 3: Run static tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py -q`

## Chunk 3: Generation Status, Cancel Boundary, And Feedback Scoring

### Task 3.1: Improve Video Progress And Cancel Boundary Messaging

**Files:**
- Modify: `apps/studio/src/canvas-view.js`
- Modify: `apps/studio/src/node-actions.js`
- Modify: `apps/studio/src/node-result-view.js`
- Modify: `apps/studio/styles/*.css`
- Test: `tests/test_web_studio_static.py`

- [ ] **Step 1: Add static tests**
  - Assert video generating UI includes submitted/running/cancelled-local-only wording.
  - Assert UI text says local cancel does not guarantee provider billing cancellation.
  - Assert poll action remains available for running video jobs.

- [ ] **Step 2: Implement state text**
  - Use existing `lastVideoJobId`, response status, and `cancelVideo`.
  - Do not invent precise provider progress. Use status-based progress only.

- [ ] **Step 3: Run focused static tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py tests\test_api_runtime_video_generations.py -q`

### Task 3.2: Add Structured Quality Feedback UI

**Files:**
- Create: `apps/studio/src/quality-feedback.js`
- Modify: `apps/studio/src/runtime-client.js`
- Modify: `apps/studio/src/node-result-view.js`
- Modify: `apps/studio/styles/*.css`
- Test: `tests/test_web_studio_static.py`
- Test: maybe extend `tests/test_api_runtime_service.py`

- [ ] **Step 1: Add static/API tests**
  - Assert runtime client exposes `recordFeedback`.
  - Assert quality feedback fields exist:
    - `identity_similarity`
    - `wardrobe_consistency`
    - `scene_continuity`
    - `text_or_watermark`
    - `target_change_success`
    - `drift_notes`
  - Assert feedback copy says this is raw evidence, not memory promotion.

- [ ] **Step 2: Implement `recordFeedback` client**
  - POST to `/feedback` with project id, feedback object, and generated timestamp.
  - Do not include media bytes, provider raw response, local paths, or signed URLs.

- [ ] **Step 3: Implement compact scoring strip**
  - Render near completed image/video results.
  - Use small buttons/segmented controls, not a large card inside a card.
  - Store result locally in node params only as safe summary, then POST raw evidence.
  - If POST fails, show non-blocking error text.

- [ ] **Step 4: Run focused tests**
  - Run: `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`
  - Run Studio JS `node --check`.

## Chunk 4: Documentation, Browser Smoke, And Closeout

### Task 4.1: Update Project Records

**Files:**
- Modify: `TASK_TRACKER.md`
- Modify: `BACKLOG.md`
- Modify: `DEVLOG.md`
- Modify: `docs/handoff/INDEX.md`
- Create: `docs/handoff/AFS-MVP-EXPERIENCE-HARDENING-20260615.md`

- [ ] **Step 1: Record the scope**
  - Add a current-work row for `AFS-MVP-EXPERIENCE-HARDENING-20260615`.
  - Mark completed items and keep video localized editing as a future capability.

- [ ] **Step 2: Record verification**
  - Record focused tests, JS checks, browser smoke, maintenance audit, and `git diff --check`.

### Task 4.2: Browser Smoke Without Provider Calls

**Files:**
- Evidence root outside repo: `D:\Projects\AgentFlowStudio-evidence\20260615-afs-mvp-experience-hardening\`

- [ ] **Step 1: Start Runtime with provider gates closed**
  - Use safe launcher or CLI directly.
  - Confirm `/health` reports Studio ready and ASR false.

- [ ] **Step 2: Use Browser/Playwright smoke**
  - Open `/studio/`.
  - Confirm no console errors.
  - Confirm empty state appears.
  - Create or load a small project.
  - Confirm carry-chain UI is present on nodes with fixed assets or safe fallback state.
  - Confirm quality feedback UI appears for a completed mock/state result if feasible without provider.

- [ ] **Step 3: Save safe evidence**
  - Screenshot without address bar/devtools/network.
  - Summary JSON outside repo only.

### Task 4.3: Final Verification

- [ ] Run focused tests:
  - `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_web_studio_static.py tests\test_api_runtime_video_generations.py tests\test_api_runtime_video_revisions.py -q`
- [ ] Run full default tests if the focused set is green:
  - `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q`
- [ ] Run legacy tests if time permits or if shared contracts changed:
  - `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -m legacy -q`
- [ ] Run Studio JS check:
  - `node --check` for all `apps/studio/**/*.js`.
- [ ] Run maintenance audit:
  - `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py`
- [ ] Run whitespace check:
  - `git diff --check`

## Claude Checkpoints

1. **Plan review before implementation**
   - Input: sanitized plan, current claim boundaries, no secrets, no provider config paths.
   - Ask Claude to check scope, gate policy, and whether P0/P1 ordering is coherent.
   - 2026-06-15 result: approved overall with tightening requests.
     - Adopted: define exact `/health.provider_gates` and `/health.studio_static` schemas before implementation.
     - Adopted: hard-check ASR off in the launcher unless a separate future task explicitly scopes ASR.
     - Adopted: make the asset reference inspector pure; optimizer and generation paths consume the same derived actions.
     - Adopted: show video local-cancel billing warning both before confirmation and after local cancellation.
     - Adopted: bound carry-chain display to a small visible list and avoid storing large bundle copies in UI-only state.
     - Not adopted by default: persistent live-gate preferences. Provider gates remain explicit per launch; a future ignored local profile can be considered only after user approval.
2. **Optional root-cause review if implementation finds a P0/P1 failure**
   - Input: failing test, sanitized diff summary, proposed fix.
3. **Closeout review before commit/push**
   - Input: diff summary, tests, remaining boundaries.

## Exact Safety Schemas

`/health.studio_static`:

```json
{
  "mounted": true,
  "root_exists": true,
  "index_exists": true,
  "entry_js_exists": true,
  "status": "ready"
}
```

Allowed status values: `ready`, `missing`, `incomplete`.

`/health.provider_gates`:

```json
{
  "llm": false,
  "image": false,
  "video": false,
  "asr": false,
  "external_download": false
}
```

The response must never include `AFS_PROVIDER_CONFIG`, provider config path, secret values, local absolute paths, provider raw output, signed URLs, or media bytes.

`quality_feedback` raw evidence payload:

```json
{
  "kind": "studio_quality_feedback",
  "node_id": "safe-node-id",
  "job_id": "safe-job-id-or-empty",
  "artifact_id": "safe-artifact-id-or-empty",
  "scores": {
    "identity_similarity": "unset|bad|ok|good",
    "wardrobe_consistency": "unset|bad|ok|good",
    "scene_continuity": "unset|bad|ok|good",
    "text_or_watermark": "unset|present|absent",
    "target_change_success": "unset|bad|ok|good"
  },
  "drift_notes": "short user note, capped client-side"
}
```

This payload is raw evidence only and must not trigger memory promotion.

## Expected Done State

- `/health` can tell an internal tester or agent whether Studio static is mounted and whether gates are open, without leaking local paths or secrets.
- A safe launcher exists for internal testing and does not open ASR by default.
- Studio nodes visibly show which fixed assets are carried or excluded.
- Mentioned-but-unconnected fixed assets are handled consistently across optimize and generation submit surfaces.
- Video generation status is clearer and local cancel billing boundary is visible.
- Human quality scoring can be captured as raw evidence through `/feedback`.
- Documentation records the slice and preserves the claim boundary: internal-test hardening only, not human acceptance or localized video productization.
