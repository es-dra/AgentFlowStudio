# AFS-WEB-LIBTV-CANVAS-INTERACTION-SAFETY-006Q

## Summary

This slice tightens the LibTV-style canvas interaction layer. The goal is not another visual pass; it makes the graph behave more like a real node editor when users drag nodes near the bottom dock or move connected nodes.

## Changes

- Connected Bezier edges update while a dragged node or selected node group is moving.
- Node drag end now computes a safe visible work area from the topbar, viewport edges, and bottom dock.
- If a dragged node would intersect the bottom dock, the canvas pans the content back into view instead of relying on z-index.
- Browser QA now requires `selected_node_clear_of_dock=true`; z-index alone is no longer enough to pass the bottom-dock safety check.

## Evidence

- `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
  - Passed.
  - `selected_node_clear_of_dock=true`.
  - Dragged node bottom: `912`.
  - Bottom dock top: `930`.
  - Confirmed double-click add menu, pending Bezier edge, target lock, success ripple, edge toolbar, marquee multi-select, group drag, duplicate, align, and delete.
- `python tools\workbench_libtv_canvas_viewport_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
  - Passed.
  - Confirmed mini-map, fit-view, center-selection, reset, no horizontal overflow, no console/page errors, and no provider requests.
- `node --check apps\workbench\src\canvas-node-drag.js`
  - Passed.
- `python -m py_compile tools\workbench_libtv_browser_qa_common.py tools\workbench_libtv_canvas_interactions_browser_qa.py`
  - Passed.
- `python -m pytest tests\test_web_workbench_libtv_canvas_interactions_browser_qa.py tests\test_web_workbench_studio.py -q`
  - Passed: `6 passed`.

## Boundaries

- No provider call.
- No MiniMax call.
- No secret, signed URL, local private media path, provider raw response, or generated media bytes were exposed.
- This is Runtime-hosted browser verification, not human acceptance, business validation, provider smoke, or durable memory promotion.

## Next

- Add a targeted browser assertion that connected edge paths change during node drag before pointer-up.
- Continue improving per-node controls, especially video motion/camera movement controls, without exposing backend memory internals in the UI.
