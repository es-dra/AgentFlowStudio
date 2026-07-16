# AFS Unified Project Studio — Design QA

## Comparison target

- Source visual truth: `C:\Users\chenzy\.codex\generated_images\019f6bfb-d905-7543-a92f-a09ba8a569d5\exec-b883435d-bd8e-40e1-9004-af1ee92773d5.png`
- Desktop implementation: `C:\Users\chenzy\AppData\Local\Temp\afs-alpha-unified-studio-ui-evidence\09-final-storyboard-desktop-1440x1024.png`
- Mobile implementation: `C:\Users\chenzy\AppData\Local\Temp\afs-alpha-unified-studio-ui-evidence\06-storyboard-mobile-390x844.png`
- Mobile review drawer: `C:\Users\chenzy\AppData\Local\Temp\afs-alpha-unified-studio-ui-evidence\07-mobile-review-version-drawer-390x844.png`
- Canvas continuity: `C:\Users\chenzy\AppData\Local\Temp\afs-alpha-unified-studio-ui-evidence\05-canvas-same-project-desktop.png`
- Desktop viewport/state: 1440 x 1024, authenticated-local project, Storyboard default, scene 01 / shot 01 selected, Director suggestion tab open.
- Mobile viewport/state: 390 x 844, same project and selection, Storyboard default; review/version details opened only through the mobile review action.

The source image is a product-direction north star, not a requirement to keep every element simultaneously visible. The comparison judges the unified information architecture, hierarchy, density discipline, same-source Storyboard/Canvas relationship, and contextual Director. Intentional progressive-disclosure omissions are treated as product-quality improvements when they preserve those truths.

## Findings

- No actionable P0, P1, or P2 findings remain.
- Fonts and typography: the implementation uses the existing Inter / PingFang SC / Microsoft YaHei stack with restrained 10–22 px hierarchy, compact labels, readable Chinese line height, and no clipped primary copy at either required viewport.
- Spacing and layout rhythm: the final desktop fills the 1440 x 1024 frame with a stable 220 px scene rail, flexible Storyboard, and 312 px contextual Director. Mobile becomes one scrollable shot column with horizontal scene context and no horizontal page overflow.
- Colors and tokens: the existing AFS blue-black palette is retained and tightened around one accent, with green/orange reserved for confirmed/attention states. No flashy gradients or decorative card stacking were introduced.
- Image quality and asset fidelity: the tested project has no generated shot media, so cards render an explicit “等待镜头画面” empty state rather than fake artwork or placeholders that imply completed assets. Real safe preview URLs remain supported through the existing Studio state model. The source concept’s cinematic assets were not copied into product code and no media generation call was made.
- Copy and content: visible text is Chinese-first, selection-scoped, and free of raw IDs, internal runtime terms, trial noise, or provider details. The Director states that suggestions are scoped and are not executed automatically.
- Icons: the established Studio icon system is reused; controls expose accessible names and consistent stroke treatment.
- States and interactions: project/scene/shot selection, Storyboard/Canvas switching, Director collapse/open, conversation, reference and version tabs, proposal-to-draft, review, recovery preview, loading/empty/error, focus, and mobile review policy were exercised.
- Accessibility: semantic buttons/tabs/navigation, visible focus rings, `aria-current`, `aria-selected`, `aria-pressed`, live status messaging, reduced-motion support, and 390 px no-overflow behavior are present.

## Full-view comparison evidence

The source concept and final desktop capture were opened together at original resolution. Both preserve:

- one project/episode/stage header;
- Storyboard as the default work surface with Canvas as the adjacent alternate view;
- a scene rail, selected-shot workspace, and contextual Director in one shell;
- restrained dark production language and state-specific color;
- an explicit relationship between current selection, suggestions, references, version, and recovery.

Intentional improvements over the concept:

- global share, notification, cost, detailed readiness, provenance, recovery, and version controls are not permanently exposed;
- project status and next action live in one collapsible cockpit strip instead of a separate dashboard;
- Director references and versions are tabbed, and the Director itself is collapsible;
- only the selected scene is expanded; adjacent scenes stay in the scene rail;
- mobile keeps project context and review available while making Canvas editing a clear desktop-only policy.

## Focused-region comparison evidence

Separate crops were not needed because the original-resolution source and implementation captures keep the header, scene rail, shot cards, and Director text legible at 1:1. These regions were inspected directly:

- header: project / episode / stage / Storyboard-Canvas relationship;
- scene rail: selected scene, shot count, attention state, episode progress;
- shot cards: selected state, duration, copy hierarchy, empty-media truthfulness;
- Director: selection title, suggestion/reference/version tabs, scoped proposal, conversation input;
- footer: script context and version/recovery disclosure.

## Comparison history

1. P1 — the first desktop grid left the lower half of the viewport unused because a hidden mobile navigation row still consumed the final grid track. Fixed by using two rows by default and adding the cockpit row only while expanded. Post-fix evidence: `02-storyboard-desktop-1440x1024.png`, superseded by final `09-final-storyboard-desktop-1440x1024.png`.
2. P2 — the first fallback plan showed 2 / 10 shots and an uneven `00:7.5` duration, weakening project-state clarity. Fixed by aligning fallback shot slots to the 15-shot project readback and normalizing duration formatting. Post-fix evidence: `09-final-storyboard-desktop-1440x1024.png` shows 2 / 15 and normalized scene durations.
3. P2 — the prior root shell exposed unrelated product navigation and a four-card overview beside a separate Canvas shell. Fixed by replacing that root surface with the Storyboard-first unified shell and changing the Canvas return control to “故事板”. Post-fix evidence: desktop Storyboard and `05-canvas-same-project-desktop.png`.

## KEEP | REFINE | MERGE | RETIRE implementation matrix

| Class | Actual files / components | Action | Verification / parity route |
|---|---|---|---|
| KEEP | `apps/studio/src/canvas-view.js`, canvas input/edge/node modules, drawer, inspector, prompt bar, persistence and recovery modules | Canvas engine, interactions, safe state, assets, generation guards, review/recovery capital remain unchanged. | Desktop Storyboard -> Canvas -> Storyboard browser journey; existing 50-test focused frontend gate. |
| REFINE | `apps/studio/src/studio-topbar.js`, `apps/studio/styles/product-shell.css` | Canvas return is now Storyboard; typography, spacing, responsive layout, focus, semantic state color, and mobile policy are tightened. | 1440 x 1024 and 390 x 844 captures; zero horizontal overflow; no browser console errors. |
| MERGE | `apps/studio/src/product-shell.js`, `apps/studio/src/main.js` | Project/episode/stage context, scene/shot selection, Storyboard, Canvas entry, review/version/recovery, and contextual Director now use the same Studio state and one root shell. | Scene/shot selection, Director conversation/proposal, review/recovery, project context, and Canvas continuity journeys. |
| RETIRE | Previous root product sidebar, separate overview navigation, stage rail, and four-card dashboard inside `product-shell.js` | Removed from the root Studio path after their project status/next-action value was merged into the collapsible cockpit and their navigation value moved into contextual controls. | Static source scan, JS syntax check, 50 focused tests, and browser parity. Separate routed `episode-workspace` and `production-control` surfaces were not deleted because they retain independent callers/tests outside this bounded root-shell change. |

## Browser and console evidence

- Provider gates from `http://127.0.0.1:8877/health`: LLM=false, image=false, video=false, ASR=false, vision=false, external download=false.
- Provider/model/media calls made by this lane: 0.
- Desktop primary interactions: project context, scene selection, shot selection, Storyboard/Canvas switch, Canvas return, Director collapse/open, conversation, proposal-to-draft, review, version, recovery preview.
- Mobile primary interactions: project/stage disclosure, Storyboard list, review/version drawer, Director close, Canvas policy, 390 x 844 overflow check.
- Browser console errors after final desktop load: 0.
- Horizontal overflow: 0 px at desktop and mobile required viewports.

## Verification

- `npm run check:studio-js` — passed, 175 files.
- `python -m pytest tests\test_web_studio_product_shell_browser.py tests\test_web_studio_modal_auth_semantics_static.py tests\test_web_studio_static.py tests\test_web_studio_session_boundary_browser.py tests\test_web_episode_workspace_productization.py tests\test_web_creator_authoring_vertical_slice.py tests\test_architecture_creator_authoring_fitness.py -q` — passed, 50 tests.
- `git diff --check` — passed.

## Follow-up polish

- P3: when a real project contains approved media previews, perform a second visual pass on cinematic crop choices and image-specific contrast; this cannot be evaluated from an empty-media project without inventing assets.

final result: passed
