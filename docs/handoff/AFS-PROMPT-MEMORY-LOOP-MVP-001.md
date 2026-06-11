# AFS Prompt Memory Loop MVP 001

Date: 2026-06-11

Owner role: Runtime/API Integrator + Memory Steward

## Scope

This slice lands the first local deterministic node prompt optimizer behind Runtime Service. The product surface should stay close to a LibTV-like canvas: nodes, prompt inputs, asset references, and generation entry points remain the main user model. The visible MVP delta is an "optimize prompt" action beside node prompt inputs.

New API surface:

```text
POST /projects/{project_id}/prompt-optimizations
```

No public memory review API is included in this MVP. Character, scene, style, and user preference context is assembled in the backend and returned only through safe prompt artifacts and trace references.

## Runtime Behavior

- `prompt-optimizations` takes node-level prompt input: node id, node type, prompt text, generation target, platform, style, optional asset refs, and optional `DirectorSetup2D`.
- Prompt assembly uses this priority order:
  1. repo-safe professional knowledge rules
  2. script character and scene context extracted from prior node prompts or supplied assets
  3. user/style preferences
- The backend applies repo-safe rules for cinematography, lighting, character consistency, scene abstraction, script/storyboard handoff, keyframe continuity, and 2D director setup translation.
- The response writes safe artifacts:
  - `agentflow_creative_brief`
  - `agentflow_prompt_assembly_trace`
  - `agentflow_prompt_optimization_safe_manifest`
  - `agentflow_run_trace`
- The backend stores extracted background context for future prompt optimization, but this is not durable Company OS memory and is not exposed as a user review queue.

## Frontend Contract

Frontend may use:

- `project_id`
- `job_id`
- `artifact_id`
- `ui_surface=node_prompt_optimizer`
- response `original_prompt`
- response `optimized_prompt`
- `creative_brief.optimized_prompt`
- `prompt_assembly_trace.context_priority`
- `prompt_assembly_trace.knowledge_rules`
- `prompt_assembly_trace.background_context_refs`
- `prompt_assembly_trace.extracted_context_refs`

Frontend should not add a memory confirmation panel for this MVP. The intended UI integration is: each canvas node prompt input gets an optimize action that can replace or copy the optimized prompt.

Frontend must not use:

- provider secret
- local absolute path
- signed URL
- generated media bytes
- provider raw response
- CLI-internal orchestration details

## Boundaries

- Local deterministic only.
- Provider gate remains closed; no live provider call was made.
- Background context is project-level Runtime Service state, not durable Company OS memory.
- Runtime verification is not human acceptance, business validation, provider smoke, or durable memory promotion.
- This slice does not clone LibTV's full product or media generation stack; it only supports the prompt optimization capability needed by a LibTV-like canvas.

## Verification

Red tests first confirmed the mismatch with the clarified MVP: old request shape still required `user_goal`, OpenAPI exposed memory review routes, and response shape returned creative memory state.

Current focused verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_llm_script_vertical.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
git diff --check
```

Observed result after realignment:

```text
3 passed, 1 warning
11 passed, 1 warning
CLI help passed
CLI version: 0.1.0
maintenance_audit: failed=0, passed=6, warning=0
874 passed, 1 warning
git diff --check passed with CRLF warnings only
```

## Next

- Wire the Web UI node prompt inputs to `POST /projects/{project_id}/prompt-optimizations`.
- Add a compact "optimize prompt" affordance for script, text, image/keyframe, video, and director nodes.
- Keep background context invisible by default; advanced diagnostics may show safe trace refs only.
- After deterministic node optimization is accepted, open an explicit LLM gate only for a minimal prompt/script optimization smoke.
