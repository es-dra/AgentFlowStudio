# AFS LibTV 节点提示词优化集成 001

Date: 2026-06-11

Owner role: Runtime/API Integrator + Frontend Contract Steward

## 范围

本轮把 LibTV 式 Web 画布里的提示词优化入口接到 Runtime Service：

```text
canvas node prompt input
-> POST /projects/{project_id}/prompt-optimizations
-> optimized_prompt + safe artifact refs
-> replace / append / apply to node
```

用户侧仍只看到节点上的“优化”动作和优化结果面板；不新增候选记忆确认、拒绝或独立记忆管理 UI。

## 实现

- `runtime-client` 新增 `optimizePrompt(projectId, payload)`。
- `app-actions` 的 `optimize-current-prompt` 先调用 Runtime API；失败时使用本地规则优化器降级。
- 新增 `prompt-optimizer-runtime.js` 负责节点类型映射、请求组装、Runtime 响应归一化和 fallback 包装。
- `render-prompt-optimizer` 显示 `Runtime 已优化` 或 `本地规则降级`，并持续显示 `Provider 未启动`。
- 后端 `prompt-optimizations` 保持单接口，只返回优化提示词、安全 manifest 和 artifact refs。

## 固定边界

- Prompt 组装优先级固定为：`professional_knowledge_base` -> `script_character_scene_assets` -> `user_preferences`。
- 前端本地 `prompt-optimizer-knowledge.js` 只是 fallback，不是最终专业知识库来源。
- 本轮不写专业知识库文件；写入位置需要用户确认后再开始。
- 未启动远程 LLM、image 或 video provider。
- 未写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
- 本轮验证不是 human acceptance、business validation 或 durable memory 晋升。

## 验证

已完成验证：

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_llm_script_vertical.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_llm_script_vertical.py tests\test_api_runtime_service.py tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py tests\test_web_workbench_libtv_add_node_flows.py tests\test_web_workbench_libtv_audio_add_node_flow.py tests\test_web_workbench_libtv_browser_qa.py tests\test_web_workbench_libtv_canvas_header.py tests\test_web_workbench_libtv_canvas_header_browser_qa.py tests\test_web_workbench_libtv_execution_scaffold.py tests\test_web_workbench_libtv_mobile_layout.py tests\test_web_workbench_libtv_resource_entries.py tests\test_web_workbench_libtv_toolbox_browser_qa.py tests\test_web_workbench_libtv_toolbox_skeleton.py tests\test_web_workbench_vertical_flow.py tests\test_web_workbench_prompt_optimizer_browser_qa.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\workbench_prompt_optimizer_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_prompt_optimizer_browser_qa
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

结果：

```text
7 passed
22 passed, 1 warning
52 passed, 1 warning
browser QA qa_status=passed; runtime_optimizer_request_urls=2; provider_request_urls=0
873 passed, 1 warning
maintenance_audit status=passed; warning=0
git diff --check passed with line-ending warnings only
```

浏览器 QA 证据：

```text
data/processed/runs/workbench_prompt_optimizer_browser_qa/workbench_prompt_optimizer_browser_qa.json
data/processed/runs/workbench_prompt_optimizer_browser_qa/screenshots/desktop/prompt-optimizer.png
data/processed/runs/workbench_prompt_optimizer_browser_qa/screenshots/mobile/prompt-optimizer.png
```

## 下一步

1. 向用户确认专业知识库文件存放位置。
2. 位置确认后，再实现 repo-safe 专业知识库 v1，不复制公司私有知识库原文。
3. 专业知识库接入后，继续验证 rule id trace、知识库优先级和用户偏好低权重约束。
