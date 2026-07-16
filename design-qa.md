# AFS Unified Project Studio — Owner-feedback Design QA V3

## Supersession and gate

The PASS recorded for PR head `10e25c8b346b39467320c65767d47b58feb44039` is superseded by the independent evaluator FAIL. That evaluation found stale Canvas selection after a scene change, a decorative Cockpit next action, sparse Storyboard density, Director conversation leakage, incorrect retry-button semantics, and two CI failures. This V3 result is PASS only after those findings are fixed, focused and full tests pass, real browser journeys pass, and the final PR head includes `master@d40daeb5fc04a3d4e0d2c4ef6803223533a5e99c`.

## Evidence roots

- Accepted hierarchy reference, used as direction rather than a pixel mandate: `C:\Users\chenzy\.codex\generated_images\019f6bfb-d905-7543-a92f-a09ba8a569d5\exec-b883435d-bd8e-40e1-9004-af1ee92773d5.png`
- New evidence root: `C:\Users\chenzy\AppData\Local\Temp\afs-pr166-owner-fix-v3-evidence`
- Canvas evaluator-before / V3-after comparison: `comparison-canvas-before-after.png`
- Sparse Storyboard evaluator-before / V3-after comparison: `comparison-sparse-before-after.png`
- Desktop Storyboard, 1440x1024: `01-desktop-storyboard-1440x1024.png`
- Canvas after an in-place scene change, 1440x1024: `02-desktop-canvas-scene-sync-1440x1024.png`
- Director context partition after changing selection: `03-desktop-director-context-partition-1440x1024.png`
- Cockpit before next action: `04-desktop-cockpit-before-next-action-1440x1024.png`
- Cockpit next-action result: `05-desktop-cockpit-next-action-result-1440x1024.png`
- Mobile Storyboard, 390x844: `06-mobile-storyboard-390x844.png`
- Mobile review/version context, 390x844: `07-mobile-review-390x844.png`
- Mobile Canvas policy, 390x844: `08-mobile-canvas-policy-390x844.png`

## Evaluator findings — before / after

| Finding | Evaluator evidence | V3 fix and result |
|---|---|---|
| P1 Canvas selection continuity | Scene 02 / 雨巷 was selected in the shell and Director while the embedded Canvas retained the Lin Wan fixed-asset selection. | `selectContext()` is now the canonical scene/shot transition. It synchronizes the Canvas engine before render, updates the shell and Director context key, and clears Canvas selection when the selected shot has no corresponding node. Browser result for 雨巷: shell key and Director key both `pr166-evaluator-ui:1:0:雨巷开场`, Canvas target `empty-shot`, no stale asset selection. |
| P1 production-control merge parity | Cockpit next action only closed the panel and displayed decorative copy. | `findNextProductionTarget()` selects the next blocked/draft production object. The action changes scene/shot selection, synchronizes Canvas, focuses the target workspace, opens the scoped Director suggestion, and supplies an actionable proposal. Browser result moved from scene 03 / 老宅 to scene 02 / 雨巷 and exposed `当前下一步 · 已定位`. |
| P1 sparse black space | One- and two-shot scenes left most of the center stage unused. | Sparse Storyboard scenes use adaptive full-height, asset-forward cards. The before/after comparison shows the same two shots using the available production stage without new permanent panels or dashboard noise. |
| P2 Director leakage | One global conversation/proposal array remained visible after selection changes. | `createDirectorContextStore()` partitions conversations, proposal state, and next-action labels by project/scene/shot context key. A note entered for 雨巷 was absent in 老宅 and restored only in its originating context. |
| P2 retry semantics | A retryable save `<button>` was overwritten with `role=status`. | Save status is now a separate polite live region. Retry remains a native `type=button` with an explicit retry label and click action. |
| CI maintainability | `main.js` was 541 lines. | Product-shell DOM/bootstrap wiring moved to `studio-product-bootstrap.js`; `main.js` is 495 lines and keeps the existing Canvas mount/reuse contract. |
| CI retention | Root `design-qa.md` produced one manual-review item. | The exact root path is classified as a current temporary `verification_surface` with an explicit retirement lifecycle. The rule is exact-path only; the broader retention policy is unchanged. |
| P3 mobile rail | The horizontal rail scrollbar was visually heavy. | The rail remains keyboard/touch-scrollable but its decorative native scrollbar is hidden. Page-level horizontal overflow remains zero. |

## Canvas same-shell continuity comparison

The evaluator-before side shows the shell and Director on 雨巷 while a fixed Lin Wan asset remains selected in Canvas. The V3-after side keeps the same persistent project header, Storyboard/Canvas switch, scene rail, version/recovery footer, and collapsible Director, but removes the stale Canvas selection. The existing Canvas engine remains mounted inside `.canvas-workspace-stage`; it was not rewritten. Switching Canvas → Storyboard kept the same scene/shot and Director context and parked the engine under `#studio-canvas-parking` without hiding `#product-shell-root`.

## Production-control caller / route / test audit

- The standalone frontend directory and `/studio/production-control/` route remain retired; the topbar has no production-control entry.
- `apps/studio/src/runtime-client.js` retains internal production-control methods because backend/contract callers still own those contracts. No backend/API/runtime contract was changed.
- Frontend parity is supplied by the project Cockpit, canonical selection/navigation path, and contextual Director proposal. It does not recreate a third product or page.
- `tests/test_web_studio_static.py` asserts route/entry retirement, retained runtime-client contracts, and the real next-action path.
- `tests/test_web_studio_product_shell_browser.py` covers canonical Canvas synchronization, context-keyed Director state, actionable next-target selection, retry semantics, and sparse density.

## KEEP | REFINE | MERGE | RETIRE matrix

| Class | Files / components | Decision and parity evidence |
|---|---|---|
| KEEP | `apps/studio/src/runtime-client.js`; unchanged backend/internal production-control contracts | Keep internal callers and contract tests. No user-facing route or top-level entry is restored. |
| KEEP | Existing Canvas engine and `#studio-editor-shell` | Reuse it as the mounted editing engine inside the unified product shell. Browser evidence proves in-place scene change and switch-back behavior. |
| REFINE | `apps/studio/src/main.js`, `studio-product-bootstrap.js`, `product-shell-context.js`, `product-shell.js`, `product-shell.css` | Establish one selection/context source, split bootstrap responsibilities, increase sparse-state density, preserve native action semantics, and reduce the mobile scrollbar. |
| MERGE | Cockpit next action + contextual AI Director | Move from status copy to an actual production-object selection/focus action and a context-scoped proposal. |
| RETIRE | `apps/studio/production-control/*`; topbar route/entry | Keep the third product retired. Deletion parity is asserted in focused frontend tests; `/studio/production-control/` remains absent. |

## Visual, interaction, responsive, and accessibility QA

- Desktop Storyboard and Canvas both measured `scrollWidth=1440` at `innerWidth=1440`; no horizontal overflow.
- Mobile Storyboard, review, and Canvas-policy journeys measured `scrollWidth=390` at `innerWidth=390`; no page overflow.
- Selected scene/shot/tab states, native pressed state, focus transfer, focus-visible CSS, loading/saving/success/status regions, retry action, recovery action, and reduced-motion rules are present. Saved success and target focus were exercised live; failure/retry remains focused static-test evidence rather than an artificially induced runtime failure.
- Mobile-first load does not mount `#studio-editor-shell`. Selecting Canvas retains Storyboard/project/review context and announces: `移动端保留项目上下文与审核；画布编辑请在桌面打开。`
- Final in-app Browser console audit returned 0 warnings and 0 errors.

## Intentional concept deviations as product-quality improvements

- Empty media remains truthful; no generated or fabricated placeholder asset was added.
- Sparse scenes enlarge the production objects themselves instead of adding new cards, panels, or a generic dashboard.
- Context/status details stay progressively disclosed through the Cockpit and Director tabs.
- Canvas remains desktop editing at 390 px while project and review context stay available.

## Provider and runtime safety

- Browser QA used local-only `127.0.0.1:4188`, never protected ports 8790/8791/8793.
- The tested preview reported LLM, ASR, image, video, vision, and external-download gates all false.
- Provider/model/media calls: 0. No provider or media endpoint was invoked.
- No deployed runtime, service, `/opt`, `/test`, or production checkout was mutated.

## Verification result

- `npm run check:studio-js` — PASS, 176 JavaScript files.
- Focused Studio and retention tests — PASS, 38 tests before the final base refresh.
- Retention summary — PASS, `manual_review_required_count=0`.
- `git diff --check` — PASS before final base refresh.
- Full suite and post-refresh checks are recorded in the PR fix packet for the exact pushed head.

## Residual risks and nonclaims

- Generated-media crop/contrast QA remains untested because provider/media calls intentionally remained zero.
- Live error/retry failure was not forced; semantic structure and action wiring are covered by focused tests.
- This is not provider smoke, generated-media QA, human acceptance, business/public/legal/SaaS/Alpha readiness, deployment, release, merge, or durable AOS promotion.

Final result: PASS for the bounded frontend/design-QA lane, conditional on the exact pushed head retaining the verification results above and including `master@d40daeb5fc04a3d4e0d2c4ef6803223533a5e99c`.
