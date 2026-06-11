# AFS Professional Knowledgebase Prompt Assembly 001

Date: 2026-06-11

Owner role: Runtime/API Integrator + Knowledgebase Steward + QA / Release Gatekeeper

## Scope

This slice completes the first backend intelligence core for the LibTV-style node prompt optimizer:

```text
node prompt input
-> Runtime POST /projects/{project_id}/prompt-optimizations
-> deterministic slot extraction
-> professional rule selection
-> character / scene / preference context selection
-> sectioned optimized prompt
-> PromptAssemblyTrace + safe manifest
```

The Web surface remains intentionally small: each node prompt input exposes only an optimize action and a result popover. There is no user-facing memory review queue, no knowledgebase management UI, and no real provider generation.

## Knowledgebase

Two synchronized copies now exist:

- Source copy: `10-Startup/70-Projects/AgentFlow-Studio/knowledgebase`.
- Runtime copy: `agentflow/knowledge`.

The repo copy contains:

- `README.md`
- `registry.json`
- `schema/creative_prompt_rule.schema.json`
- `rules/*.jsonl`
- `examples/node_prompt_optimization_examples.jsonl`

Current v1 has 47 repo-safe professional prompt rules across directing, cinematography, lighting, production design, storyboard, short video script, character consistency, keyframe continuity, video motion, director setup 2D, and negative constraints.

Rules are generic professional production guidance only. They do not include company-private knowledge, provider raw responses, signed URLs, local private assets, business judgment, or internal retrospectives.

## Runtime Assembly

New runtime pieces:

- `agentflow/knowledge/creative_prompt_rules.py`: registry/rule loader, validation, normalized hash sync check, deterministic rule selector.
- `apps/api/runtime_prompt_memory_slots.py`: deterministic Chinese/English slot extraction for subject, scene, action, emotion, lighting, camera, motion, style, preferences, assets, and director setup.
- `apps/api/runtime_prompt_memory_engine.py`: prompt assembly engine with fixed context priority.
- `apps/api/runtime_prompt_memory_assembly.py`: compatibility wrapper over the new engine.
- `apps/api/runtime_prompt_memory.py`: response trace and safe manifest now include knowledgebase version, registry hash, rules count, selected slots, suppression, and conflict resolution.

Context priority remains fixed:

```text
professional_knowledge_base
-> script_character_scene_assets
-> user_preferences
```

User preferences can tune soft style language, but they cannot override professional constraints, current node intent, character identity, scene continuity, or provider-off safety boundaries.

## Trace And Safety

`PromptAssemblyTrace` now records:

- selected rule ids, domains, weights, and match reasons;
- selected slots;
- background context refs;
- suppressed user preference context;
- conflict resolution policy;
- knowledgebase version, registry hash, and rule count.

The safe manifest exposes only safe knowledgebase metadata. It does not expose provider secrets, local absolute paths, signed URLs, media bytes, or provider raw responses.

## Verification

Latest focused verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_agentflow_knowledgebase.py tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_llm_script_vertical.py tests\test_api_runtime_service.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py tests\test_web_workbench_libtv_add_node_flows.py tests\test_web_workbench_libtv_audio_add_node_flow.py tests\test_web_workbench_libtv_browser_qa.py tests\test_web_workbench_libtv_canvas_header.py tests\test_web_workbench_libtv_canvas_header_browser_qa.py tests\test_web_workbench_libtv_execution_scaffold.py tests\test_web_workbench_libtv_mobile_layout.py tests\test_web_workbench_libtv_resource_entries.py tests\test_web_workbench_libtv_toolbox_browser_qa.py tests\test_web_workbench_libtv_toolbox_skeleton.py tests\test_web_workbench_vertical_flow.py tests\test_web_workbench_prompt_optimizer_browser_qa.py -q
```

Result: `56 passed, 1 warning`.

Browser QA:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\workbench_prompt_optimizer_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_prompt_optimizer_browser_qa
```

Result: `qa_status=passed`, prompt optimizer requests `2`, provider requests `0`, console errors `0`, page errors `0`, horizontal overflow `false`.

Evidence:

```text
data/processed/runs/workbench_prompt_optimizer_browser_qa/workbench_prompt_optimizer_browser_qa.json
data/processed/runs/workbench_prompt_optimizer_browser_qa/screenshots/desktop/prompt-optimizer.png
data/processed/runs/workbench_prompt_optimizer_browser_qa/screenshots/mobile/prompt-optimizer.png
```

Final verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

Results:

```text
CLI help passed
version 0.1.0
full pytest: 878 passed, 1 warning
maintenance_audit: passed; failed=0, warning=0
git diff --check: passed; CRLF warnings only
```

## Boundaries

- No remote LLM/image/video provider was enabled.
- No provider smoke was performed.
- No generated media bytes were saved.
- No durable memory or Company OS active rule was promoted.
- Browser/runtime verification is not human acceptance or business validation.

## Next

1. After human review, expert adjustments can enter as explainable rules, weights, applicability scopes, negative constraints, or quality checks.
2. Keep future embedding/RAG/database work behind a separate architecture decision; v1 remains deterministic and local.
