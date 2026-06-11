# AFS MVP 提示词优化联合验收清单

日期：2026-06-11

本文用于 Web UI 线程完成后，统一验收 LibTV 式画布节点提示词优化 MVP。它不是新功能需求，不扩大 Web 表面，只把 Runtime、知识库、fixtures、浏览器 QA 和安全边界放到同一张验收表里。

## 验收目标

第一版 MVP 只验证一件事：

```text
LibTV 式画布节点 prompt 输入
-> 用户点击优化提示词
-> Web 调用 Runtime prompt-optimizations
-> 后台按专业知识库优先装配 prompt
-> 用户可替换、追加、应用到当前节点
-> provider requests 为 0
```

用户不应该看到知识库管理、规则权重、trace 明细、候选记忆审核、provider 配置、工程路径或媒体字节。

## 节点覆盖

| 节点 | 必须有优化入口 | Runtime target | 关键后台域 | 用户可见结果 |
|---|---:|---|---|---|
| text | 是 | `prompt` | directing, cinematography, lighting, negative_constraints | 可优化文本/叙事提示词 |
| image | 是 | `image` / `keyframe` | cinematography, lighting, production_design, character_consistency | 可优化画面、构图、灯光和角色一致性 |
| video | 是 | `video` | video_motion, cinematography, lighting, negative_constraints | 可优化运动、时间推进和镜头连续性 |
| audio | 是 | `audio` | audio_design, negative_constraints | 可优化旁白、节奏、停顿、音色边界 |
| script | 是 | `script` | short_video_script, storyboard, negative_constraints | 可优化脚本 beat 和分镜交接 |
| director | 是 | `video` | director_setup_2d, cinematography, lighting, production_design | 可优化二维导演台场景上下文 |
| video_merge | 否 | 暂不接入 | none | 默认无 prompt 输入，不显示优化按钮 |

## 前端只展示

- 原始 prompt。
- 优化后 prompt。
- 替换、追加、复制、应用到节点等普通创作动作。
- 简单状态：已优化、可重试、本地降级。

## 前端禁止展示

- provider secret、key、cookie、token。
- 本地绝对路径、signed URL、媒体字节。
- provider 原始响应。
- `PromptAssemblyTrace` 的内部规则权重、registry hash、候选记忆、长期记忆判断。
- `Runtime`、`Provider Gate`、`rule id`、`weight` 等工程词作为普通用户主界面文案。

## 后台必须证明

- 每次优化有 `PromptAssemblyTrace`。
- trace 包含真实 `rule_id`、domain、match reason。
- `professional_knowledge_base` 优先级高于人物/场景资产和用户偏好。
- 用户偏好不能覆盖专业硬约束、角色身份、场景连续性和 provider-off 安全边界。
- 知识库主副本与 repo 执行副本 normalized hash 一致。
- `provider_calls_started=false`。
- `writes_company_kb=false`。
- `writes_long_term_memory=false`。

## 联合验收顺序

1. 读取 `git status --short`，确认 Web UI 线程是否仍在改 `apps/workbench/**`。
2. 跑 API fixtures，确认 6 类节点都能调用 Runtime。
3. 跑知识库覆盖和同步检查，确认各节点至少命中专业规则域。
4. 跑 API-only smoke，确认 provider requests 为 0，unsafe matches 为 0。
5. 启动 Runtime Service。
6. 跑 Web prompt optimizer browser QA，确认真实浏览器里能输入、优化、展示、应用，且 provider requests 为 0。
7. 跑 Web 线程的 LibTV focused tests。
8. 跑 full pytest。
9. 跑 maintenance audit、repository retention review、`git diff --check`。
10. 全部通过后，再统一更新 `DEVLOG.md`、`TASK_TRACKER.md` 和 handoff index。

## 推荐命令

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_agentflow_knowledgebase.py tests\test_agentflow_knowledgebase_coverage.py -q
.\.venv\Scripts\python.exe tools\prompt_optimizer_api_smoke.py --fixture-dir examples\frontend_runtime_service\prompt_optimizer_nodes --output-dir data\processed\runs\prompt_optimizer_api_smoke

.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8793 --runtime-root data\processed\runs\runtime_service_joint_acceptance
.\.venv\Scripts\python.exe tools\workbench_prompt_optimizer_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_prompt_optimizer_browser_qa

.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
git diff --check
```

## 通过标准

- API fixtures：6 个节点全部通过。
- API smoke：`passed=6`、`failed=0`、`provider_calls_started=0`、`unsafe_matches=0`。
- Browser QA：desktop 和 mobile 都通过；`runtime_optimizer_request_urls` 非空；`provider_request_urls=[]`；console/page errors 为 0；无横向溢出。
- Full pytest：0 failed。
- Maintenance audit：0 failed、0 warning。
- Retention review：无删除候选、无必须人工复核项。
- `git diff --check`：无 whitespace error；Windows CRLF 提示不算失败。

## 非声明

- 不是 human acceptance。
- 不是 business validation。
- 不是 provider smoke。
- 不是 durable memory 晋升。
- 不是 SaaS、账号、支付、多用户协作或真实公开视频资源站。
