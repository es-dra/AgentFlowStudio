# AFS Professional Prompt Optimization Deterministic Hardening - 2026-07-02

## Scope

Provider-closed deterministic hardening for image, keyframe, and video prompt optimization. This preserves AFS as an AI-native manga/image/video production workbench and does not reposition the product as a prompt platform.

## Base

- Worktree: `C:\Users\chenzy\.codex\worktrees\d46d\AgentFlowStudio`
- Branch: `codex/afs-professional-prompt-optimization-hardening-20260702`
- Base: `4cc62a36df5d724f0861154d195067f260e65fc1`
- `master` and `origin/master` matched the base after `git fetch --prune origin`.

## Product Delta

- Added deterministic professional visual prompt clauses for image/keyframe/video prompt optimization.
- Real Chinese prompts such as `女生在笑`, `女生微笑`, `雨夜街道，紧张`, `让她慢慢回头微笑`, and `开心` now extract subject, emotion, scene, action, and motion semantics instead of falling through to generic placeholders.
- Image/keyframe optimized prompts now include subject identity, restrained realistic expression cues, expression decomposition before action, body/action carrier, grounded scene, light/camera detail, continuity, and negative constraints.
- Video optimized prompts now include start state, transition, movement/body carrier, camera/environment motion, end state, duration/beat language, and first-frame/source continuity when available.
- Image-to-video prompt optimization now emphasizes motion-first continuation and first-frame/source provenance instead of restating the entire upstream image.

## Quality Delta

- Added a focused semantic test file for representative professional prompt optimization cases.
- Preserved provider-closed behavior: no provider calls, no image/video generation, no external download.
- Kept Studio UI unchanged; the lightweight optimize action near prompt input remains as-is.

## Governance Delta

- Internal trace artifacts remain backend artifacts; no knowledgebase UI or internal engineering trace was exposed to users.
- Non-claims preserved: no provider smoke, no generated-media quality claim, no human creative acceptance, no business/public/legal validation, no deploy/runtime/server health claim, no CompanyOS projection, no durable-memory promotion, no COS active-rule promotion.

## Files Touched

- `apps/api/runtime_professional_prompt_contract.py`
- `apps/api/runtime_prompt_memory_slots.py`
- `apps/api/runtime_prompt_memory_engine.py`
- `tests/test_api_runtime_professional_prompt_optimization.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-PROFESSIONAL-PROMPT-OPTIMIZATION-DETERMINISTIC-HARDENING-20260702.md`

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_professional_prompt_optimization.py
# red before implementation: 5 failed, 1 warning
# green after implementation: 5 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_memory_candidates.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_director_setup_prompt.py tests\test_algorithm_library_contracts.py
# 81 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 862 passed, 520 deselected, 2 warnings

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

git diff --check
# passed

git status --short -- docs\demo-docs-20260629 .obsidian
# no output; protected paths untouched
```

`npm run check:studio-js` was not run because Studio JavaScript was not touched.

## Residual Risks

- This is deterministic prompt-contract verification only. It does not prove generated media quality.
- The repo still contains legacy mojibake Chinese strings in older tests/modules; this slice adds a real-CJK override path without broad text cleanup.
- Final readiness still requires independent evaluator review before integration.

## Next Action

Route this branch to an independent evaluator for `implementation_ready_for_review`.
