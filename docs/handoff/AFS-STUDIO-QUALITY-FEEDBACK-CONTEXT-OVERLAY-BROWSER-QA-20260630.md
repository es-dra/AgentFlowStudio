# AFS-T15i Studio 质量反馈 Context Overlay 浏览器 QA - 2026-06-30

## 任务信息

- 任务编号：`AFS-T15i Studio Quality Feedback Context Overlay Browser QA`
- 当前分支：`codex/afs-project-book-full-goal-20260630`
- 起始提交：`69a34eea1d7ab1d4da90833b0fc2eccbcaf95daf`
- 当前状态：本地浏览器 / Runtime 链路已验证；本 handoff 用于提交推送前的收口记录。

本轮不是新增产品功能，而是把 T15h 质量反馈到「下一轮本地上下文」
的 UI 切片补上真实浏览器证据。核心目标是确认 Studio 前端实际点击路径、
Runtime `/feedback`、feedback candidate promotion、context overlay、Studio
state 持久化和 safe manifest 引用之间没有 contract 漂移。

## Dirty Ownership Ledger

本轮拥有并允许提交的改动：

- `apps/studio/src/feedback-candidate-flow.js`
- `apps/api/runtime_studio_state_quality_feedback.py`
- `tests/test_api_runtime_studio_quality_feedback_state.py`
- `tests/test_studio_quality_feedback_context_overlay_browser_qa_tool.py`
- `tests/test_web_studio_feedback_candidate_artifact_ids.py`
- `tools/studio_quality_feedback_context_overlay_browser_qa.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-QUALITY-FEEDBACK-CONTEXT-OVERLAY-BROWSER-QA-20260630.md`

明确不触碰：

- `docs/demo-docs-20260629/` 仍是既有未跟踪目录，本轮没有 staging、清理或修改。
- 未修改服务器 checkout、`master`、provider 配置、生成媒体文件、私有素材、secret 或 CompanyOS/COS active rule。

## 读取范围

本轮读取了项目启动规则和当前状态文件，包括 `AGENTS.md`、
`docs/company_operating_model.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md`，
并继续审计 T15h 的质量反馈 UI、Runtime Studio-state sanitizer、feedback
candidate Runtime contract、现有静态测试和浏览器 QA 支撑工具。

## 写入范围

本轮只写入质量反馈 context overlay closeout 路径：

- Studio feedback candidate promotion / context overlay 请求构造和本地 summary。
- Runtime Studio-state `qualityFeedbackCandidates` sanitizer。
- 浏览器 QA 工具和针对长 artifact id 的 deterministic 回归测试。
- 项目记录和本 handoff。

没有新增 Runtime public route，没有更新 OpenAPI，没有扩展 provider adapter，
没有修改真实生成链路。

## 发现的事实

真实浏览器 QA 首次跑通 Studio UI 时暴露了一个 contract 问题：

- Runtime 生成的 feedback、promotion、context overlay artifact id 可能长于 180 字符。
- Studio 之前把 `promotion_decision_artifact_id` 当普通短文本处理并截断到 180 字符。
- 截断后的 id 无法在 Runtime manifest 中匹配，context overlay POST 被 Runtime 以 422 拒绝。

这不是视觉问题，而是 Runtime artifact 引用与 Studio 本地 UI summary 的边界不一致。

## Contract 判断

Artifact id 是安全引用，不是 operator prose。它仍然必须有长度上限，
但上限需要覆盖 Runtime artifact identifier 的实际长度。最终边界：

- `feedback_artifact_id`
- `promotion_artifact_id`
- `context_overlay_artifact_id`

这些字段在 Studio request / summary 和 Runtime Studio-state sanitizer 中统一使用
512 字符 artifact-ref 上限。普通文本字段继续保留已有短上限，避免 notes、
rationale、scope label 或 provider 相关内容被放宽。

## 本轮改动

- Studio `feedback-candidate-flow.js` 增加 `ARTIFACT_REF_MAX_LENGTH = 512`，
  只用于 artifact reference 字段。
- Runtime `runtime_studio_state_quality_feedback.py` 增加同样的 artifact-ref 上限，
  并用于 feedback / promotion / context overlay artifact id。
- 新增 Playwright 浏览器 QA 工具
  `tools/studio_quality_feedback_context_overlay_browser_qa.py`。
- 新增浏览器 QA 工具 contract 测试、长 artifact id Studio JS 回归测试、
  Runtime Studio-state sanitizer 回归测试。

## 安全边界

- Provider gate 没有打开。
- 没有 provider raw response、signed URL、secret、cookie、token、本地绝对私有路径或媒体字节进入仓库。
- 浏览器 QA 使用临时本地 Runtime root 和 FastAPI TestClient 路由。
- `runs/` 下报告属于 ignored runtime evidence，没有提交。
- 本轮不声明 provider smoke、人类创作验收、商业验证、部署验证或服务器 Runtime 健康。

## 验证结果

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_studio_quality_feedback_context_overlay_browser_qa_tool.py tests\test_web_studio_feedback_candidate_static.py tests\test_web_studio_feedback_candidate_artifact_ids.py tests\test_api_runtime_studio_quality_feedback_state.py -q
# 17 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\studio_quality_feedback_context_overlay_browser_qa.py --report runs\studio_quality_feedback_context_overlay_browser_qa_t15i.json --timeout-ms 90000
# status=passed; provider_calls_started=false; manifest_feedback_ref_count=3

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 750 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed
```

维护审计在新 handoff 中文化前曾出现新增
`human_doc_chinese_coverage` warning；本文件改成中文主文档后，该 warning
回到既有 22 项，没有新增文档覆盖率维护债。

## Cleanup Review

- 没有删除历史文件。
- 没有合并分支。
- 没有同步服务器。
- 长 artifact id 的 JS 回归被拆到独立测试文件，避免继续膨胀既有静态测试文件。
- `tools/studio_quality_feedback_context_overlay_browser_qa.py` 为 299 行，低于 300 行维护阈值。

## Evidence State

`runtime_browser_verified_studio_quality_feedback_context_overlay_pending_commit_push`

## 下一步

下一步有效任务是 `AFS-T19 Goal-Mode Branch Integration Review Gate`。

在 T19 review 通过并得到明确授权前，不继续新增功能、不合并 `master`、
不同步服务器、不运行 provider smoke。
