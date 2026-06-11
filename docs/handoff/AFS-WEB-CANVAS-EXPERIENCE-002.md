# AFS-WEB-CANVAS-EXPERIENCE-002 Handoff

Status: implemented in `codex/afs-web-refoundation-vertical-001`.

## Scope

This slice upgrades the Runtime-hosted Workbench canvas from a static production map into an interactive creator surface:

- SVG canvas edge layer with connected and pending edge states.
- Node hover lift, selected state, linked/dimmed upstream and downstream emphasis, status chips, and inline actions.
- Node drag handles with 12px snap-grid behavior and local connection intent state.
- Visible asset shelf for character turnarounds, scene boards, keyframes, video clips, audio clips, and director setup assets.
- 2D Director Desk v1 with reference frame, top-down floor plan, camera, subject, key/fill/back lights, modifiers, props, and parameter inspector.
- Local deterministic prompt optimizer with structured sections for character, scene, lighting, camera, keyframe, video motion, and negative prompts.

## Safety Boundary

- No provider call was started.
- No MiniMax key, provider key, token, signed URL, provider raw response, local private media path, or generated media byte was written to the repo.
- Visible assets are represented by safe summaries and thumbnail refs only.
- Hidden assets such as user preference, feedback, abstract character traits, failure experience, and style constraints remain backend-only concepts. The UI only says that project constraints were applied.
- Prompt optimization v1 is local deterministic logic. A future MiniMax or other LLM enhancement must stay behind `AFS_ALLOW_REMOTE_LLM=true`.

## Verification

- Red tests first failed on missing prompt optimizer and canvas interaction markers.
- Focused new tests:
  `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py::test_prompt_optimizer_local_knowledge_base_is_wired tests\test_web_workbench_studio.py::test_libtv_style_canvas_workspace_is_wired -q`
  passed: `2 passed`.
- Focused Workbench suite:
  `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py tests\test_web_workbench_libtv_add_node_flows.py tests\test_web_workbench_libtv_execution_scaffold.py -q`
  passed: `21 passed`.
- Runtime-hosted browser QA on `http://127.0.0.1:8798/workbench/` passed for desktop and mobile with console errors `0`.
- Browser QA evidence: `data/processed/runs/workbench_canvas_experience_qa/desktop-home.png`, `desktop-canvas.png`, `desktop-assets-prompt.png`, `desktop-director.png`, and `mobile-canvas.png`.

## Follow-Up

- Add persisted node positions and edge graph serialization once Runtime Service exposes a frontend-safe canvas graph contract.
- Convert Director Desk setup into a backend `director_setup_asset` safe manifest once the asset registry supports this public shape.
- Add a gated MiniMax LLM enhancement path for prompt optimizer after local deterministic behavior remains stable.
- Add image/video provider slices separately; this slice intentionally does not open image or video gates.

