---
doc_type: company_os_feedback_packet
status: candidate
last_updated: 2026-06-10
source_task: AFS-WEB-RC-FREEZE-2026-06-10
confidentiality: internal
writes_company_kb: false
---

# Company OS Feedback Packet - AFS Web RC Freeze

## 中文摘要

本反馈包只记录一条候选经验：复刻外部产品时，先落地低学习成本的功能骨架和本地安全主路径，再逐步显性化 AFS 自己的证据链、质量门、反馈复用、项目记忆、Provider Gate 和组织复盘能力。它不主张把 Company OS 的所有概念一次性塞进主界面，也不把浏览器 QA 当成人工验收或商业验证。当前结论来自 AFS Web Workbench 的一次工程候选版本冻结，因此只能进入候选反馈流程，不能直接成为公司级 active rule。

这条经验的实际价值在于控制节奏：先让用户看得懂项目入口、画布、节点、素材、历史、工具箱和执行意图；再用审片、记忆、任务和 provider gate 建立 AFS-native 的工作方式；最后通过最小 provider 纵切验证真实模型链路。下一步建议用 LLM/script 作为第一条纵切，因为脚本和分镜文本更容易审查、记录、复用和修正。图片 provider 可以排在第二步，视频 provider 应排在第三步，避免把异步任务、成本、失败恢复、媒体字节和质量判断一起压到第一个真实接入任务上。

## 1. Project Context

- Project: AgentFlow Studio
- Repository scope: current AgentFlowStudio checkout
- Session date: 2026-06-10
- Task: freeze the current Web Workbench release candidate and prepare the first provider vertical slice.
- Work mode: Strategic / Deep
- Project-local record path: `docs/frontend_integration/AFS_WEB_RC_FREEZE_CLOSEOUT_2026-06-10.zh-CN.md`
- Confidentiality: internal

## 2. Company OS Context Used

| Source | Used? | Notes |
|---|---|---|
| Company OS source rule chain | yes | Used as the source-of-truth boundary. The repo only stores execution projection. |
| Project `AGENTS.md` | yes | Used for provider gate, evidence boundary, and no-private-material constraints. |
| `docs/company_operating_model.md` | yes | Used to keep AFS as a product execution surface, not a Company OS mirror. |
| Task tracker / acceptance packet / QA ledger | yes | Used as project-local lifecycle and evidence records. |

## 3. Reusable Lesson

Candidate rule:

When replicating an external product for an AFS-style workbench, land the low-learning-cost functional skeleton first, freeze it as an engineering RC, and only then introduce AFS-native differentiation through evidence chain, quality gates, feedback reuse, project memory, provider gate, and organizational review surfaces.

Do not force every Company OS concept into the first UI layer. The main UI should stay understandable; COS/AFS-native concepts should become visible through workflow state, evidence, review, and safe gates.

## 4. Evidence Produced

| Artifact | Path | Status |
|---|---|---|
| RC freeze closeout | `docs/frontend_integration/AFS_WEB_RC_FREEZE_CLOSEOUT_2026-06-10.zh-CN.md` | engineering RC |
| Acceptance packet | `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md` | updated |
| UX QA ledger | `docs/frontend_integration/AFS_WEB_UX_QA_LEDGER.zh-CN.md` | updated |
| Task tracker | `TASK_TRACKER.md` | updated |
| Devlog | `DEVLOG.md` | updated |
| Browser QA manifests | `data/processed/runs/workbench_libtv_*_browser_qa/` | runtime verification only |

## 5. Candidate Feedback

| Feedback type | Target | Candidate action |
|---|---|---|
| workflow_update | External product replication sequence | keep_candidate |
| product_rule | Do not overexpose COS concepts in first-layer UI | keep_candidate |
| provider_sequence | Start provider vertical slice with LLM/script before image/video | keep_candidate |
| evidence_boundary | Keep runtime verification, human acceptance, provider smoke, business validation, durable memory separate | reinforce_candidate |

## 6. Routing Decision

Route this packet through:

```text
10-Startup/80-Workflow/ai-native-company-workflow/feedback-routing.md
```

Selected destinations:

- [x] Project-local DEVLOG / TASK_TRACKER / QA ledger
- [x] Candidate rule ledger
- [x] Workflow template update
- [x] Strategy evidence
- [ ] Company memory candidate
- [ ] Contract/schema update
- [ ] No Company OS update needed

## 7. Human Review Gate

- Reviewer: user
- Review date: pending
- Decision: keep_candidate pending review
- Reason: the lesson is likely reusable, but it came from one AFS Web RC freeze and must not be auto-promoted.
- Next validation task: apply the same sequence to the LLM/script provider vertical slice, then decide whether the rule deserves promotion.

## 8. Claim Boundary

- Verified: project-local Workbench RC has runtime/browser/test evidence after final gates pass.
- Not verified: human acceptance, provider smoke, business validation, or durable memory promotion.
- Inferred: the sequencing rule should generalize to similar external-product replication tasks.
- Must not be copied into public repos: private Company OS source notes, secret, signed URL, local private material, provider raw response, generated media bytes, or unreviewed business conclusions.
