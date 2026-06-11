# AFS Professional Knowledgebase Prompt Assembly 001

中文摘要：本文记录专业知识库与 Prompt Assembly 的当前后端交接状态。当前有效结论是知识库权重最高，其次是人物/场景资产，最后才是用户偏好；用户偏好不得覆盖专业硬约束、角色身份、场景连续性或节点参数。后续接入真实模型时，应沿用这里的 rule id、trace、safe manifest 和 provider gate 边界。

执行标准：每次优化都要记录命中的 rule id、适用原因、权重、被抑制的偏好和最终 prompt 结构。专业规则不是黑箱偏好，而是可解释的导演、摄影、灯光、美术、连续性和负面约束。后续专家意见只能以规则、权重、适用场景、反例和质量检查项进入，不能直接变成不可追踪的模型偏好。

下一步口径：接入真实图片模型前，应先用现有 deterministic 路径确认每类节点都能命中合理规则域，并且输出能被 Studio 节点直接应用。模型返回结果只能作为候选证据进入项目运行目录，不能覆盖知识库规则，也不能保存原始 provider 响应。若专家调权，应先写小范围规则变更、fixture 和回归测试，再考虑扩大覆盖。

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
- `apps/api/runtime_creative_agent.py`: layered single-agent decision layer for hard/strong/soft constraints, candidate scoring, Pareto-style selection, and image/keyframe provider translation.
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
- creative agent candidate ids, scores, constraint layers, selected candidate, and provider translation;
- selected slots;
- background context refs;
- suppressed user preference context;
- conflict resolution policy;
- knowledgebase version, registry hash, and rule count.

The safe manifest exposes only safe knowledgebase metadata. It does not expose provider secrets, local absolute paths, signed URLs, media bytes, or provider raw responses.

## Verification

Latest focused verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_agentflow_knowledgebase.py tests\test_agentflow_knowledgebase_coverage.py tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_service.py tests\test_web_studio_static.py -q
```

Current focused result after Studio cleanup and creative-agent trace: pass.
Browser QA is now scoped to `/studio/`; old `/workbench/` browser tools and
handoffs have been deleted.

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
