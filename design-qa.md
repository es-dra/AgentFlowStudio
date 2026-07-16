# AFS Unified Project Studio — Owner-feedback Design QA

## Supersession and acceptance gate

The earlier `design-qa.md` PASS at PR head `7405a5ef6c3349e8c95914bee570ca76f1d57827` is superseded by Owner live-test feedback. It incorrectly treated the legacy full-screen Canvas replacement and the separate `production-control` product entry as acceptable. This QA starts from those P0/P1 findings and passes only after the same-shell Canvas continuity, frontend production-control retirement, hierarchy, density, responsive, and interaction-feedback requirements are reverified.

## Target and evidence

- Accepted hierarchy direction (north star, not a pixel mandate): `C:\Users\chenzy\.codex\generated_images\019f6bfb-d905-7543-a92f-a09ba8a569d5\exec-b883435d-bd8e-40e1-9004-af1ee92773d5.png`
- Concept / final Storyboard comparison: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\15-concept-final-storyboard-comparison.png`
- Owner-failing Canvas / fixed Canvas comparison: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\16-owner-before-after-canvas-comparison.png`
- Final Storyboard, 1440 × 1024: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\09-final-storyboard-desktop-1440x1024.png`
- Final Canvas in the persistent shell, 1440 × 1024: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\11-final-canvas-same-shell-settled-1440x1024.png`
- Contextual project status / Cockpit: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\13-project-cockpit-contextual-settled-1440x1024.png`
- Canvas recovery feedback: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\14-canvas-recovery-feedback-1440x1024.png`
- Mobile Storyboard, 390 × 844: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\04-storyboard-mobile-390x844.png`
- Mobile review/version drawer: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\05-mobile-review-version-drawer-390x844.png`
- Mobile Canvas policy: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-evidence\08-mobile-canvas-policy-visible-top-390x844.png`

The local QA project was `雨夜追光 · 第一集`. The verified Canvas state retained scene 02 / shot 02 (`雨巷` / `人物回望`) and its AI Director context.

## Owner findings — before / after

| Severity | Before at the superseded head | Implemented fix | Evidence |
|---|---|---|---|
| P0 | `openCanvasWorkspace -> productShell.showCanvas()` enabled `.canvas-mode`, hid `product-shell-root`, and exposed the legacy `studio-editor-shell` as a separate full-screen app. | `main.js` parks the existing Canvas engine and `product-shell.js` mounts it into `.canvas-workspace-stage` inside the persistent Studio shell. The project/episode/stage header, Storyboard/Canvas switch, scene/shot selection, version/recovery context, and collapsible AI Director stay present. The Canvas engine was adapted, not rewritten. | `16-owner-before-after-canvas-comparison.png`, final Canvas screenshot, and Storyboard → Canvas → Storyboard browser journey. |
| P0/P1 | `创作中枢` / `制作总览` / `/studio/production-control/` remained a third top-level product surface. | The frontend route files and topbar entry were retired. Useful status, save state, attention, and next-action capability now live in the project Cockpit and contextual AI Director. Internal runtime-client/backend contracts remain intact. | Contextual Cockpit screenshot, caller scan, static tests, and matrix below. |
| P1 | Large empty black regions, tiny low-contrast text, repetitive border/card framing, and weak interaction feedback. | Body copy is 12–14 px, canvas/stage allocation is denser, asset grouping and selection hierarchy are stronger, borders/noise are reduced, and hover/pressed/focus/selected/save/recovery states are explicit and restrained. | Desktop/mobile screenshots, visible keyboard focus, recovery live message, CSS state scan, zero-overflow checks. |

No actionable P0, P1, or P2 finding remains in this bounded frontend lane.

## Focused Canvas shell-continuity comparison

The original Owner-failing screenshot showed Canvas replacing the full product surface: there was no shared project header, no Storyboard/Canvas switch, no scene/shot rail from the unified shell, and no contextual Director aligned to the selected shot.

The fixed screenshot proves one continuous shell:

- the same project, episode, stage, scene 02, and shot 02 remain selected;
- Storyboard and Canvas are adjacent tabs in the same header and switch without page navigation or root-shell replacement;
- the existing Canvas node/edge/prompt engine is mounted in the shared center stage;
- the persistent scene rail and the AI Director remain visible and collapsible;
- version recovery feedback renders inside Canvas without leaving the workspace;
- `.canvas-mode` no longer hides `product-shell-root`; the legacy editor root is a parked/mounted engine surface only.

## Production-control caller / route / test audit

The audit used `rg -n --hidden --glob '!design-qa.md' --glob '!node_modules' "production-control|制作总览|创作中枢" apps/studio tests` after deletion.

- Removed frontend callers/routes: `apps/studio/src/studio-topbar.js` no longer exposes `/studio/production-control/`; the standalone `apps/studio/production-control/{index.html,app.mjs,styles.css}` surface is deleted.
- Remaining frontend contract only: `apps/studio/src/runtime-client.js` retains `production-control` request methods because backend/internal orchestration contracts and their tests still use them. They are not exposed as a top-level product.
- Remaining tests are backend/contract coverage such as `tests/test_api_runtime_production_control_vertical_slice.py`, `tests/test_api_runtime_creator_production_saga.py`, and `tests/test_production_control_contract.py`.
- Frontend deletion parity is asserted by `tests/test_web_studio_static.py`: the directory has no files, the topbar route/function is absent, project status/Cockpit/Director capability exists, and runtime-client contract methods remain.

## KEEP | REFINE | MERGE | RETIRE matrix

| Class | Actual files / components | Decision | Caller/test and deletion-parity route |
|---|---|---|---|
| KEEP | `apps/studio/src/runtime-client.js`; backend/internal production-control API and tests (unchanged) | Keep the internal contract needed by orchestration and existing backend consumers without exposing another product shell. | Runtime-client methods remain; backend/contract tests continue to own API semantics. No backend file changed. |
| KEEP | Existing Canvas engine modules and `#studio-editor-shell` | Reuse the established node/edge/prompt/persistence engine. | Mounted into `.canvas-workspace-stage`; focused browser journey proves selection and engine continuity. |
| REFINE | `apps/studio/src/product-shell.js`, `apps/studio/styles/product-shell.css`, `apps/studio/src/i18n.js`, `apps/studio/src/review-delivery-workspace.js` | Strengthen hierarchy, density, responsive behavior, project-status naming, save/recovery feedback, and contextual return labels. | Desktop/mobile screenshots, focus/overflow/console checks, focused frontend tests. |
| MERGE | Project Cockpit/status/next action and AI Director inside `product-shell.js` | Merge useful orchestration/status capability into project context instead of a competing page. | `13-project-cockpit-contextual-settled-1440x1024.png`; static Cockpit/Director assertions. |
| RETIRE | `apps/studio/production-control/index.html`, `app.mjs`, `styles.css`; production-control topbar link/function in `studio-topbar.js` | Delete the redundant user-facing third product and route entry. | Exact post-delete caller scan plus frontend deletion-parity test; backend/internal contract retained. |

## Visual maturity, interaction, accessibility, and responsive findings

- Typography uses the existing Inter / PingFang SC / Microsoft YaHei stack with 12–14 px body copy, stronger headings, and readable Chinese line height.
- Desktop uses a stable scene rail, flexible Storyboard/Canvas stage, and contextual Director; both required desktop views report zero horizontal overflow.
- Selected scene/shot/tab states are explicit. Hover and pressed states are encoded in the shared control/card rules; keyboard focus was exercised and produced a visible 2 px solid outline.
- Save state maps to saving/saved/error/retry UI from the existing Studio state. Saved success was visible in the final header; recovery was exercised live in Canvas. Loading/saving/error were not artificially induced against the local-only runtime, so those remain implementation/static-test evidence rather than claimed live failure-path evidence.
- Mobile 390 × 844 keeps project context, Storyboard, review/version access, and Director policy with zero horizontal overflow. Canvas editing remains desktop-only and returns a clear fixed policy message instead of loading a cramped editor.
- Semantic buttons/tabs, `aria-current`, `aria-selected`, `aria-pressed`, focus-visible styling, live messaging, and reduced-motion handling remain present.
- Final page console audit: 44 informational request entries, 0 errors/warnings.

## Intentional concept deviations as product-quality improvements

- No generated imagery was copied or fabricated for empty shot assets; empty states stay truthful.
- The legacy Canvas inspector is collapsed and the decorative sprite layer is hidden when embedded so the selected asset remains the focus.
- Status and next action use progressive disclosure in the project Cockpit; they are not a persistent dashboard or separate product.
- Director references and versions remain contextual tabs/drawers instead of simultaneous panels.
- Canvas editing is deliberately desktop-only at 390 px, while project/review context remains available.

## Provider and runtime safety evidence

- Preview: local-only `127.0.0.1:4187` (non-protected port), with `AFS_AUTH_ENABLED=false` and every remote LLM/ASR/image/video/vision/external-download gate false.
- `/health` reported local-only readiness and closed provider gates.
- Provider/model/media calls made: 0.
- Protected ports 8790/8791/8793 and deployed/runtime checkouts were not touched.

## Verification

- `npm run check:studio-js` — passed, 174 files.
- `python -m pytest tests\test_web_studio_product_shell_browser.py tests\test_web_studio_static.py -q` — passed, 19 tests.
- `python -m pytest tests\test_web_studio_product_shell_browser.py tests\test_web_studio_modal_auth_semantics_static.py tests\test_web_studio_static.py tests\test_web_studio_session_boundary_browser.py tests\test_web_episode_workspace_productization.py tests\test_web_creator_authoring_vertical_slice.py tests\test_architecture_creator_authoring_fitness.py -q` — passed, 51 tests.
- `git diff --check` — passed.
- Browser journeys — Storyboard, same-shell Canvas and return, project Cockpit, Canvas recovery, mobile project/review policy, focus, overflow, and console checks passed at required viewports.

## Residual P3 / nonclaims

- P3: real generated-media crop/contrast QA remains untested because provider/media calls were intentionally zero and the local project had empty media.
- Live loading/saving/error/retry failure paths were not forced; implementation and focused static tests cover them, while saved success and recovery were exercised live.
- This is not provider smoke, generated-media QA, human acceptance, business/public/legal/SaaS/Alpha readiness, deployment, release, or durable AOS promotion.

final result: passed
