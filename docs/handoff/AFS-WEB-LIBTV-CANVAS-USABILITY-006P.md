# AFS-WEB-LIBTV-CANVAS-USABILITY-006P

## Scope

Tighten the LibTV-style canvas from visual imitation toward usable node-editor behavior.

## Landed

- Selected and dragging workflow nodes now stay above the floating bottom dock.
- The workflow canvas has a bottom safe band so nodes dragged low remain operable.
- Image, video, and audio node panels now show a live current-setting summary.
- Node control QA now checks that clicked controls change readable node settings, not only button styling.
- Canvas interaction QA now drags a node into the dock area and asserts it remains above the dock.

## Evidence

- `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- `python tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- `python tools\workbench_libtv_workflow_node_open_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- Focused Workbench tests: `16 passed`

## Boundaries

- No provider call.
- No MiniMax call.
- No secret, signed URL, local private media path, provider raw response, or generated media byte exposure.
- Browser QA is runtime verification only, not human acceptance or business validation.

## Next Slice

Continue node-by-node interaction fidelity:

- Text/script nodes should gain a small setting summary if their attempt mode starts affecting generation behavior.
- Video node should expose motion/intensity controls as real local state.
- Director node should get stronger object relationship feedback when camera, subject, and lights are selected together.
