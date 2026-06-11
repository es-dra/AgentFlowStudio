# AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006

## Summary

This slice resets the user-facing Web UI toward a LibTV-style canvas product: dark creation portal, full-screen infinite canvas, bottom node dock, left canvas/assets drawer, floating add-node/tool/material/history panels, node-local controls, and prompt optimization only beside prompt inputs.

The prompt memory loop remains backend-only. The ordinary user UI does not expose memory confirmation pages, knowledge weights, provider internals, trace details, raw responses, local paths, signed URLs, or secrets.

## User-Facing Scope

- Home portal: dark creative entry with start creation, recent projects, inspiration cards, and template entries.
- Canvas: AFS mark, project/canvas header, dot-grid infinite surface, workflow nodes, connection layer, bottom dock, floating panels, left canvas/assets drawer.
- Node types: text, image, video, audio, script, video merge, director desk, upload, and generated-history selection.
- Prompt optimization: each prompt input has an `优化` trigger; the anchored popover shows original text, optimized prompt sections, replace/append/copy/apply actions, and product copy only.
- Director desk: lightweight canvas node opens a professional editor-style layout with reference frame, top-down stage, camera, subject, Key/Fill/Back/Practical lights, camera parameters, and output actions.

## Removed From Ordinary UI

The normal user path no longer surfaces:

- `项目记忆`
- `生成能力门`
- `任务中心`
- `诊断`
- `Provider`
- `Runtime`
- `CommandHub`
- memory candidates / confirmation / rejection
- knowledge weights / trace / provider raw response

Debug and older engineering surfaces may remain in code for compatibility, but they are not connected to the product shell path.

## Fixes During Browser QA

- Replaced an obsolete canvas-header QA contract that still waited for the old `.libtv-topbar` and editable canvas menu.
- Fixed bottom dock/add-node panel positioning so menus are visible from the full-screen canvas.
- Converted prompt optimizer from a large side panel into an anchored popover and fixed close behavior.
- Removed backend assembly trace text from optimized prompt output; users now see clean Chinese professional prompt sections.
- Removed visible "generation capability not started" copy from the optimizer path.
- Added Director Desk v2 canvas node labels and required light/output controls.
- Fixed toolbox active state and panel positioning.
- Tightened mobile dock label rendering and node card sizing so visible controls are not squeezed by old fixed-height rules.

## Canvas Interaction Upgrade

- Added real canvas pan on empty-surface drag so the user can move the world instead of being trapped by the visible viewport.
- Added double-click creation: double-clicking empty canvas opens the add-node menu at the pointer and creates a floating node at that world coordinate.
- Added per-node position persistence, drag handles, damping, and 12px grid snap.
- Added dynamic SVG Bezier edges, pending drag edges, target hit detection, and connected-edge animation.
- Added long-press marquee selection on empty canvas; selected nodes are persisted in `selectedNodeIds` and visually highlighted.
- Added group drag after marquee selection: dragging any selected node moves the selected group together with the same damped 12px snap.
- Added visible node ports through `styles-studio-node-ports.css`: left amber input ports, right teal output ports, output-to-input Bezier anchoring, success-ripple edge styling, and persistent directional edge flow.
- Added connection target magnet feedback: pending Bezier edges lock to the target node center, target nodes show a temporary highlight, and the edge switches to `target-locked` styling before connection success.
- Added a visible multi-select frame and floating batch toolbar after marquee selection.
- Added batch actions for duplicate, align row, align column, clear selection, and safe delete of custom nodes while preserving default workflow nodes.
- Added selected-node relationship focus: upstream nodes/edges, downstream nodes/edges, bridge roles, and dimmed unrelated branches are computed from actual canvas edges.
- Raised node action hit targets above the prompt control card so selecting a node does not block neighboring node actions.
- Added a MAP mini-navigator: mini-map node marks, current viewport rectangle, fit workflow, center selected, and 100% reset.
- Added drawer-node centering so the left canvas node list can locate a node instead of only selecting it.
- Normalized canvas transform origin to top-left world coordinates so fit/center actions match the user's mental model.
- Split workflow graph data into `studio-workflow-graph.js` and interaction styling into `styles-studio-canvas-interactions.css` to keep the main renderer under the maintenance threshold.
- Split canvas interaction geometry and node-drag lifecycle into `canvas-interaction-geometry.js` and `canvas-node-drag.js`; `canvas-interactions.js` is now below the 300-line maintenance threshold.
- Added `canvas-selection-actions.js` for batch node operations so `app.js` and canvas interactions stay below the maintenance threshold.
- Added `canvas-relation-focus.js` for graph-based focus roles so the renderer does not carry traversal logic.
- Added `canvas-viewport-actions.js` for fit/center/reset/navigator metrics so the interaction binder stays below the maintenance threshold.
- Added default workflow-node opening: every visible workflow node now has a stable `data-open-node-kind` mapping and opens the corresponding LibTV-style node panel instead of only changing selection.
- Added a canvas topbar `返回画布` action for node-detail/resource/starter modes, keeping node panel transitions reversible.
- Added opened-node context bars through `render-studio-node-context.js`: text, script, image, video, audio, director, and video-merge panels now show the originating canvas node plus clickable upstream/current/downstream chain chips and a local return action.
- Moved the selected-node prompt card below its node so it no longer blocks adjacent node actions.
- Split canvas node create/open state transitions into `studio-node-actions.js` so `app.js` stays below the maintenance threshold.
- Turned prompt-node primary actions from disabled placeholders into node-local safe previews: text/script/image/video/audio prompt panels now show ready/generating/complete/error status, animated local progress, and a reversible `safe_node_generation_preview` result without starting a provider.
- Added selectable edge relationship controls: clicking a connected edge highlights it, selects both endpoint nodes, shows a compact upstream/downstream toolbar, can center the endpoints in view, and can disconnect custom links while protecting default workflow links.
- Added real node-local parameter controls through `studio-node-control-state.js`: text/script attempt chips, image mode/spec controls, video mode/spec/toggle controls, and audio target/mode/voice/spec controls now persist active state through local UI state instead of acting as decorative labels.
- Added `styles-studio-node-controls.css` for pressed/hover feedback and compact parameter-option cards across text, image, video, audio, and script nodes.
- Added a real video `运镜` control panel with animated motion preview, camera movement, strength, subject action, and rhythm controls; the video node summary now updates when these local settings change.

## Director Desk Top-View Upgrade

- Replaced the ordinary user path for the director node with `renderDirectorFlowV3`, a LibTV-style canvas node that behaves like a small professional editor instead of a static asset card.
- Added `director-setup-model.js` as the safe front-end model for camera, subject, Key/Fill/Back/Practical lights, reflector, flag, bed, window light, and poster marks.
- Added draggable top-view objects through `data-director-drag-id`; drag state is persisted in `directorElementOverrides` and reflected immediately in the camera/object panel.
- Added explicit actions for `save-director-setup` and `apply-director-setup-to-shot`. Saving creates a visible `director_setup` asset; applying writes a local prompt-context preview for the current shot.
- Added `styles-studio-director-node-flow.css` to isolate the v3 top-view editor styling, reset old pseudo-3D grid transforms, and keep director object labels clipped within the stage.
- Kept the backend prompt/memory trace invisible. The user sees only director setup status, scene asset output, and prompt context summary.

## Verification

Runtime-hosted browser QA used:

```powershell
python tools\workbench_libtv_canvas_header_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_prompt_optimizer_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_toolbox_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_relation_focus_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_canvas_viewport_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_director_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
python tools\workbench_libtv_workflow_node_open_browser_qa.py --base-url http://127.0.0.1:8806/workbench/
```

Current evidence:

- canvas header browser QA: passed on desktop, tablet, and mobile.
- add-node browser QA: passed on desktop, tablet, and mobile.
- prompt optimizer browser QA: passed on desktop and mobile.
- toolbox browser QA: passed on desktop, tablet, and mobile.
- canvas interactions browser QA: passed; verified pan transform change, double-click node creation, node drag coordinate change, visible source output and target input ports, target-locked pending edge, highlighted connection target, success-ripple connected edge, persistent `edge-idle-flow`, long-press marquee, group drag moving another selected node, selection frame/toolbar visibility, align-row, duplicate, delete-custom restore, edge toolbar visibility, selected edge glow, custom-edge disconnect, no provider requests, and no console/page errors.
- relation focus browser QA: passed; verified selected, direct upstream, direct downstream, upstream edge, downstream edge, dimmed node, and dimmed edge states with no provider requests and no console/page errors.
- canvas viewport browser QA: passed; verified MAP mini-map, 8 node marks, viewport rectangle, fit-view transform change to `0.55`, center-selection bringing the selected node near viewport center, reset to `100%`, no provider requests, and no console/page errors.
- director interactions browser QA: passed; verified director node creation, top-view object drag persistence, object selection panel sync, apply-to-shot prompt context, save-as-scene-asset, selected visible asset, no provider requests, and no console/page errors.
- workflow node open browser QA: passed; verified all 8 default nodes open to the expected text/script/image/director/video/video-merge panels, preserve `data-opened-node-id`, show opened-node context id/kind/upstream-current-downstream chains, navigate from the `script-input` downstream chip into `storyboard`, show prompt optimization where applicable, move prompt-node generation status to `complete` after local preview, return to canvas, and do not start provider requests.
- workflow node open browser QA now also verifies node-control activation for text, script, image, and video workflow nodes.
- add-node desktop browser QA now verifies node-control activation for text, image, video, audio, and script nodes, and confirms text-node overflow is reduced to zero.
- add-node browser QA now verifies the video `运镜` panel across desktop, tablet, and mobile: the panel is visible, the clicked motion value becomes active, and the summary mentions the selected value.
- Shared browser QA helpers now live in `tools/workbench_libtv_browser_qa_common.py`; add-node and workflow-node QA scripts are back below the 300-line maintenance threshold.
- add-node desktop browser QA after director v3 changes: passed; director stage object overflow was reduced to no stage-object text overflow, with no viewport overflow.
- workflow node open browser QA now verifies canvas-to-node spatial transitions: default node open uses `enter` / `node-enter-from-canvas`, graph context chip navigation uses `chain` / `node-chain-swap`, and return-to-canvas uses `return` / `canvas-node-return`.
- add-node browser QA now verifies direct add-node panel transitions, and desktop QA confirms the compact director v3 panel plus upload/history resource paths no longer leave overflowing add-node menus on screen.
- `styles-studio-mobile-node-workspace.css` now owns tablet/mobile node-detail compaction after the LibTV shell: compact topbar, 12-slot bottom dock, wrapped node context bar, clamped node-flow width, scrollable node-detail stage, single-column parameter grids, and compact Director Desk top-view objects.
- add-node browser QA now treats visible text/control overflow as a failure on desktop, tablet, and mobile while excluding intentional scroll containers. Current evidence shows all add-node/resource cases at `overflow_node_count=0` across all three viewports.
- workflow node open browser QA passed after the mobile compaction and still verifies `enter`, `chain`, and `return` animations, including Director Desk return-to-canvas pulse.
- focused Web/canvas/node-context tests: `14 passed`.
- full pytest: `889 passed`.
- `maintenance_audit`: `failed=0`, `passed=5`, `warning=1`; the only remaining warning is long-running project records `DEVLOG.md` / `TASK_TRACKER.md`.
- canvas interaction QA script remains below the maintenance threshold at `300` lines after adding port, edge-flow, and edge-toolbar coverage.
- `git diff --check`: passed with Windows line-ending warnings only.

Full regression and maintenance gates were run after the interaction update.

## Boundaries

- No live provider call.
- No MiniMax call.
- No secret, key, cookie, signed URL, private local media path, provider raw response, or generated media byte is committed.
- Browser QA and pytest are runtime verification only. They are not human acceptance, provider smoke, business validation, or durable memory promotion.
