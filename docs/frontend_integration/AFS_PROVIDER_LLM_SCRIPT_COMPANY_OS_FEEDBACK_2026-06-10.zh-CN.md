---
doc_type: company_os_feedback_candidate
status: candidate_pending_human_review
last_updated: 2026-06-10
source_stage: afs_provider_llm_script_vertical_prep
writes_company_kb: false
---

# Company OS Feedback Candidate - LLM/Script Provider Vertical Prep

## 中文摘要

这是一条候选反馈，不是 active rule。它来自 AFS Web RC 冻结后的 LLM/script provider 前置切口，核心经验是：在真实 provider smoke 之前，应该先落一个默认 gate closed 的安全计划接口。这个接口先证明责任边界、artifact 边界和反馈复用边界，再讨论是否打开真实模型调用。

本候选规则适合进入 Company OS 的候选队列，因为它把“能调用模型”和“应该如何安全接入模型”拆开了。前端只拿 project、job、artifact 和 safe manifest；Runtime Service 才负责 provider gate；provider 原始响应、密钥、签名链接、本地素材路径和生成媒体字节都不能进入仓库或前端主界面。审片反馈只能先作为 candidate constraints 使用，不能自动晋升为 durable memory。

当前证据只证明 gate-closed 工程骨架、本地确定性脚本/分镜草案和 candidate-only 反馈复用已经落地，并通过 focused API 测试。它还没有经过 live LLM smoke、人工验收、商业验证或长期记忆晋升。因此本反馈只能保留为 candidate，等下一步真实 LLM smoke 完成后再由用户判断是否提升为 limited 或 active 规则。

## 1. Project Context

- Project: AgentFlow Studio
- Repository scope: current AgentFlowStudio checkout
- Session date: 2026-06-10
- Task: prepare the first provider vertical slice after Web RC freeze.
- Project-local evidence path: `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_VERTICAL_PREP_2026-06-10.zh-CN.md`

## 2. Candidate Lesson

Before opening a real provider smoke, land a gate-closed safe-artifact plan endpoint first.

For text-provider verticals, the first engineering slice should prove:

- the frontend does not call the provider directly;
- the Runtime Service owns the provider boundary;
- the default gate is closed;
- the system writes safe request/manifest/artifact refs;
- raw provider responses are not stored;
- review feedback is reusable only as candidate constraints;
- runtime verification remains separate from human acceptance, provider smoke, business validation, and durable memory.

## 3. Evidence

| Evidence | Path / Command | Result |
|---|---|---|
| Provider prep packet | `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_VERTICAL_PREP_2026-06-10.zh-CN.md` | created |
| Focused API test | `.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_script_vertical.py -q` | `3 passed, 1 warning` |
| Runtime endpoint | `POST /provider/script-draft-plan` | landed |
| Safe artifact roles | `llm_script_request_plan`, local deterministic `script_storyboard_safe_artifact`, `script_provider_safe_manifest` | landed |
| OpenAPI surface | `/provider/script-draft-plan` | exported |

## 4. Candidate Routing

Suggested destination:

```text
10-Startup/80-Workflow/ai-native-company-workflow/feedback-routing.md
```

Candidate actions:

- [x] Candidate rule ledger
- [x] Workflow template update
- [x] Provider-gate engineering checklist
- [ ] Company memory candidate
- [ ] Active rule

## 5. Human Review Gate

- Reviewer: user
- Review date: pending
- Decision: keep_candidate pending review
- Reason: this came from one AFS provider-prep slice. It is likely reusable, but should be validated through the actual gated LLM smoke before promotion.

## 6. Claim Boundary

- Verified: gate-closed safe artifact skeleton, local deterministic script/storyboard draft, candidate-only review constraints, and tests.
- Not verified: live LLM provider smoke, human acceptance, business validation, durable-memory promotion.
- Must not be copied into public repo docs as policy: local Company OS source notes, secrets, signed URLs, private materials, provider raw response, generated media bytes, or unreviewed commercial conclusions.
