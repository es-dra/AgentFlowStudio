# AFS Prompt Memory Loop MVP 001

中文摘要：本文记录第一版节点 prompt 优化闭环的后端能力。当前产品面只在 Studio 节点输入处提供优化动作，后台可使用知识库、角色/场景上下文和低权重用户偏好，但不展示候选记忆审核 UI。这里的“memory loop”只表示项目级背景证据复用，不等于 durable memory，也不等于公司知识库晋升。

执行标准：优化输出要适合节点直接使用，并保持 Intent、Subject、Scene、Action、Camera、Lighting、Motion、Continuity 和 Negative Constraints 等结构。第二次优化可以复用前次抽取的人物和场景，但必须在 trace 中说明来源和非 durable memory。provider gate 关闭时仍要本地 deterministic 可用。

下一步口径：前端只需要调用节点优化接口、展示优化结果并允许替换或追加到节点 prompt；后台 trace、候选评分、知识库权重和上下文来源不进入普通 UI。真实模型接入时，先让 prompt 优化和关键帧生成形成一条可回放证据链，再根据人工反馈调整规则。任何反馈都先作为候选证据，不能静默改变 durable memory。

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
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_service_v02.py tests\test_web_studio_static.py -q
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
