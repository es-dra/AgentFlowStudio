# AFS-WEB-LIBTV-VIDEO-MOTION-CONTROLS-006R

## Summary

This slice continues the LibTV-style canvas refinement by making the video node's `运镜` surface a real local control panel instead of a static chip.

It supports the current product direction: the user works directly on canvas nodes, each node owns its own settings, and AFS prompt memory / provider details remain hidden behind safe UI state.

## Landed

- Added a video motion panel inside the LibTV-style video node.
- Added an animated motion preview with a camera marker and directional path.
- Added node-local controls for:
  - camera movement: `推进`, `拉远`, `横移`, `环绕`, `上摇`, `手持`
  - movement strength: `轻微`, `标准`, `强`
  - subject action: `静止凝视`, `走入画面`, `回头`, `抬头`
  - rhythm: `慢`, `标准`, `快`
- Updated the video node summary so clicked motion settings appear in the current generation settings.
- Extended browser QA so the video motion panel must be visible, the clicked value must become active, and the summary must mention the clicked value.

## Evidence

- `node --check apps\workbench\src\render-studio-video-node-flow.js`
- `python -m py_compile tools\workbench_libtv_browser_qa_common.py tools\workbench_libtv_add_node_browser_qa.py`
- `python -m pytest tests\test_web_workbench_libtv_add_node_flows.py tests\test_web_workbench_libtv_browser_qa.py -q`
- `python tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- `python tools\workbench_libtv_workflow_node_open_browser_qa.py --base-url http://127.0.0.1:8806/workbench/`
- `python -m pytest -q`: `890 passed`
- `python tools\maintenance_audit.py`: `failed=0`, `passed=5`, `warning=1` for long-running record files only
- `git diff --check`: passed with Windows line-ending warnings only

Latest browser evidence for the video node includes:

- `video_motion.panel_visible=true`
- `video_motion.clicked=true`
- `video_motion.value=拉远`
- `video_motion.active=true`
- `video_motion.summary_mentions_value=true`

Canvas interaction QA also passed in the same Runtime-hosted session with pan, double-click node creation, bottom-dock-safe drag, pending Bezier edge, target lock/highlight, connected edge flow, marquee multi-select, group drag, batch toolbar, and custom-edge disconnect.

## Boundaries

- No live provider call.
- No MiniMax call.
- No secret, key, cookie, signed URL, local private media path, provider raw response, or generated media byte was introduced.
- This is browser/runtime verification only. It is not human acceptance, provider smoke, business validation, or durable memory promotion.
