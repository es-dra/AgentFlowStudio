---
doc_type: provider_vertical_prep
status: engineering_prep_done_pending_provider_smoke
last_updated: 2026-06-10
owner_role: Engineering Delivery Lead
provider_gate: closed
writes_company_kb: false
---

# AFS LLM/Script Provider Vertical Prep - 2026-06-10

## 中文摘要

本文件记录 Web RC 冻结之后的第一条 provider 纵切前置工作。当前目标不是直接接入真实模型，而是先把 Runtime Service 的安全边界、任务记录、artifact 形态和反馈复用协议落下来。这样后续即使打开 LLM gate，也不会让前端直接接触 provider 配置、密钥、原始响应或本地素材路径。

本阶段新增的是“计划型 + 本地草案型”接口：用户目标进入后端后，系统写安全请求计划、本地确定性脚本/分镜草案和 safe manifest。默认情况下 `AFS_ALLOW_REMOTE_LLM` 关闭，任务状态会显示为 blocked，但这不是失败，而是在提醒后续真实 provider smoke 必须由用户显式授权。审片反馈可以作为下一轮候选约束复用，但不能自动成为长期记忆，也不能写入 Company KB。

这份准备包的判断口径是：工程骨架已经可测，真实 provider 还没有启动；runtime verification 已经有 focused API 证据，human acceptance、provider smoke、business validation 和 durable memory promotion 都仍然未发生。后续如果继续推进，应先明确授权 LLM gate，再做最小 live smoke，并继续只保存脱敏后的 safe artifact。

## 1. Scope

本阶段从 Web RC 冻结后的下一步开始：准备第一条 provider 纵切，但不启动真实 provider。

本阶段只落地 LLM/script 的安全 Runtime 骨架：

- 用户目标进入 Runtime Service。
- Runtime 写入 LLM 脚本请求计划、脚本/分镜安全脚手架、safe manifest。
- 任务中心可以看到 `llm_script_draft_plan` job。
- Review feedback 只作为第二轮 candidate constraints 复用。
- 默认 `AFS_ALLOW_REMOTE_LLM` 关闭时，job 状态为 `blocked`，但仍保留可审计的安全 artifact。

本阶段不做：

- 不继续扩展 LibTV UI 功能面。
- 不调用 OpenAI-compatible 或任何远程 LLM provider。
- 不接 image/video provider。
- 不保存 provider raw payload、生成媒体字节、本地私有路径、secret 或 signed URL。
- 不把审片反馈写成 durable memory。

## 2. Implemented Product Objects

| Object | Path / API | Status |
|---|---|---|
| Runtime endpoint | `POST /provider/script-draft-plan` | landed |
| Request model | `ProviderScriptDraftPlanRequest` | landed |
| Safe plan artifact | `llm_script_request_plan.json` | landed |
| Script/storyboard safe draft | `script_storyboard_safe_artifact.json` | landed with local deterministic draft |
| Provider safe manifest | `script_provider_safe_manifest.json` | landed |
| Run trace | `agentflow_run_trace.json` | landed |
| Job center label/guidance | `llm_script_draft_plan` | landed |
| OpenAPI export surface | `/provider/script-draft-plan` | landed |

## 3. Evidence

TDD evidence:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_script_vertical.py -q
```

Result:

```text
3 passed, 1 warning
```

Red/green boundary:

- Red 1: route missing, returned `404`, OpenAPI path missing.
- Red 2: local draft and second-round candidate constraints missing from safe artifact.
- Green: gate-closed plan endpoint returns safe job/artifacts, local deterministic script/storyboard draft, and candidate-only review constraints; OpenAPI includes the new route and request schema.

Final verification:

| Gate | Command | Result |
|---|---|---|
| Focused Runtime/API | `.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_script_vertical.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py -q` | `8 passed, 1 warning` |
| Full pytest | `.\.venv\Scripts\python.exe -m pytest` | `871 passed, 1 warning` |
| Maintenance audit | `.\.venv\Scripts\python.exe tools\maintenance_audit.py` | `failed=0, passed=6, warning=0` |
| CLI help | `.\.venv\Scripts\python.exe -m apps.cli.main --help` | passed |
| CLI version | `.\.venv\Scripts\python.exe -m apps.cli.main version` | `0.1.0` |
| Diff check | `git diff --check` | passed with Windows CRLF normalization warnings only |

Maintainability:

```text
288 apps/api/runtime_service.py
241 apps/api/runtime_provider_script.py
 98 apps/api/runtime_provider_script_routes.py
123 apps/api/runtime_models.py
125 apps/api/runtime_artifacts.py
 96 apps/api/runtime_workbench_jobs.py
 96 apps/api/runtime_workbench_support.py
171 tests/test_api_runtime_llm_script_vertical.py
```

No file in this slice crossed the 300-line maintenance warning line.

## 4. Safety Boundary

Default gate behavior:

- `AFS_ALLOW_REMOTE_LLM` absent or false: `provider_gate.status = blocked`。
- `provider_calls_started = false`。
- `remote_provider_calls_started = false`。
- `raw_provider_response_stored = false`。
- `generated_media_bytes_stored = false`。
- local deterministic script/storyboard draft is allowed as runtime verification evidence, not provider smoke.
- `writes_long_term_memory = false`。
- `writes_company_kb = false`。

Claim boundary:

- This is runtime engineering preparation.
- This is not human acceptance.
- This is not provider smoke.
- This is not business validation.
- This is not durable memory promotion.

## 5. Next Provider Slice

The next smallest provider step should be a gated LLM smoke only after explicit authorization.

Minimum next path:

1. Confirm `AFS_ALLOW_REMOTE_LLM=true` explicitly for that task.
2. Use configured model gateway through the Runtime Service boundary, not from the frontend.
3. Reduce provider output to a safe script/storyboard artifact.
4. Store no raw provider response.
5. Record Review Room keep/revise/reject feedback.
6. Use feedback in a second request as candidate constraints only.

Image provider remains second. Video provider remains third.

## 6. Stage Closeout

Current completion:

- LLM/script provider vertical prep: complete as a gate-closed Runtime skeleton with local deterministic script/storyboard draft.
- Browser QA: not rerun for this backend-only slice; existing Web RC browser QA remains valid for UI freeze only.
- Focused API evidence: complete.
- Full-suite evidence: complete.

Reference-only:

- LibTV script/node labels remain UI reference material.
- No LibTV provider behavior was copied or validated.

AFS product objects:

- Provider-gated LLM/script plan endpoint.
- Safe artifact chain.
- Local deterministic script/storyboard draft.
- Candidate-only feedback reuse policy.
- Job center guidance for gate-closed state.

Company OS feedback: `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`
