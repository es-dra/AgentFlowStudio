# AFS Creative Intent Control Agent Engineering Summary

中文摘要：本文只记录创作意图控制智能体在 AFS repo 中的安全工程投影。当前实现是 deterministic 的单智能体多视角流程，用于把节点 prompt、节点参数、专业知识、角色/场景上下文和 provider 能力约束转化为 canonical creative brief 与 provider prompt。详细算法思想、可专利讨论和实验观察保留在 `10-Startup` 私有知识库；repo 侧不保存 provider raw、secret、媒体字节、本地私有路径或不可公开商业判断。

执行标准：智能体输出必须区分 canonical brief、provider prompt、候选评分、选择理由和安全 trace。内部可以使用导演、摄影、灯光、美术、连续性和 provider 适配等视角，但前端不展示多智能体过程。图片/关键帧 gate 通过前，不接视频；未经确认的反馈只能是候选证据，不能成为强记忆。

Date: 2026-06-12; selection-policy update 2026-07-29

This repo stores only the safe engineering projection of the creative intent
control agent. The detailed algorithm discussion and patent-candidate notes
live in the private `10-Startup` knowledge base.

## Current Scope

The first implementation is a deterministic layered single-agent path inside
Runtime Service:

```text
node prompt
-> slot extraction
-> professional rule selection
-> background character / scene context
-> hard / strong / soft constraint layering
-> three candidate creative briefs
-> weighted primary-axis scores + generation_target bias + hard-control veto
-> canonical prompt + provider translation
-> safe trace and manifest
```

Selection policy method: `weighted_primary_axes_with_target_bias`.
It is not a true Pareto frontier. Primary axes are
`visual_controllability`, `character_consistency`, `scene_continuity`, and
`provider_fit`, with `professional_alignment` as the tie-breaker. Generation
target only applies a small bias; hard node-parameter controls veto candidates
that drop those controls from the canonical prompt.

Current working-mode baseline:
[AFS_CREATIVE_AGENT_WORKING_MODE_BASELINE_20260729.md](AFS_CREATIVE_AGENT_WORKING_MODE_BASELINE_20260729.md)

The user-facing Studio surface still shows only the node prompt optimization
action and result. It does not expose memory review, knowledgebase management,
candidate scoring, provider raw payloads, or local artifact paths.

## Runtime Files

- `apps/api/runtime_creative_agent.py`
- `apps/api/runtime_prompt_memory_engine.py`
- `apps/api/runtime_prompt_memory.py`
- `apps/api/runtime_keyframes.py`
- `apps/api/runtime_keyframe_routes.py`

## API Surface

- `POST /projects/{project_id}/prompt-optimizations`
- `POST /projects/{project_id}/keyframe-generations`

`prompt-optimizations` returns the optimized prompt and safe artifacts.
`keyframe-generations` is image-gated by `AFS_ALLOW_REMOTE_IMAGE`; with the gate
closed, it returns a blocked safe manifest and starts no provider call.

## Safety Rules

- No provider call by default.
- No provider config path in keyframe request bodies.
- No secret, signed URL, provider raw response, local private path, or media
  bytes in API responses or registered JSON artifacts.
- Feedback and extracted context remain candidate/background evidence, not
  durable memory.
- Provider smoke is not human acceptance or business validation.

## Verification

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_creative_agent_keyframes.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py tests\test_api_runtime_service.py tests\test_web_studio_static.py tests\test_api_runtime_creative_agent_keyframes.py -q
```

The key regression checks are:

- creative-agent trace includes constraint layers, candidates, scores, selected
  candidate, and provider translation;
- node parameters are treated as hard controls;
- user preferences are lower priority than professional and node constraints;
- keyframe route is blocked before network when `AFS_ALLOW_REMOTE_IMAGE` is not
  enabled;
- OpenAPI exposes keyframe generation without a provider secret/config surface.
