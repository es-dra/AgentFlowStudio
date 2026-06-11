# AFS MVP Prompt Optimizer Support 001

日期：2026-06-11

## 目标

在 Web UI 线程继续重做 LibTV 式画布期间，本并行线只补后台支撑材料：节点提示词优化契约、API fixtures、知识库覆盖、API-only smoke 和演示种子。目标是 Web 完成后可以直接进入节点输入、优化提示词、应用到节点、provider 为 0 的第一版 MVP 验收。

## 写入范围

本线新增或修改：

- `docs/frontend_integration/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md`
- `examples/frontend_runtime_service/prompt_optimizer_nodes/*.zh.json`
- `examples/frontend_runtime_service/prompt_optimizer_demo_project.example.json`
- `tests/test_api_runtime_prompt_node_contract.py`
- `tests/test_agentflow_knowledgebase_coverage.py`
- `tools/prompt_optimizer_api_smoke.py`
- `agentflow/knowledge/creative_prompt_rules.py`
- `agentflow/knowledge/registry.json`
- `agentflow/knowledge/rules/audio_design.jsonl`
- `10-Startup/70-Projects/AgentFlow-Studio/knowledgebase/registry.json`
- `10-Startup/70-Projects/AgentFlow-Studio/knowledgebase/rules/audio_design.jsonl`

本线最初不修改 Web UI 文件；Web 线程完成后进入联合验收时，为修复真实浏览器 QA 与静态契约漂移，追加了最小 Web 侧修复：补齐 LibTV 画布 topbar/toolbox QA、抽出 `render-studio-canvas-topbar.js`、拆分画布 CSS 并压回维护阈值。没有启动 provider。

## 交付内容

- 契约文档固定节点类型：`text`、`image`、`video`、`audio`、`script`、`director`；`video_merge` 默认无 prompt 输入，不显示优化按钮。
- 六类节点 fixtures 均包含 request、expected domains、expected sections、forbidden UI terms 和 provider expected false。
- demo seed 包含一个短剧项目、2 个角色、2 个场景、项目风格、用户偏好和 6 个节点 prompt request。
- 新增 4 条 `audio_design` 规则：旁白表达、停顿重音、音色一致性、音效/配乐边界。
- selector 对 image/keyframe/video/director 节点补充 `production_design` 专业域兜底，避免视觉节点丢失美术场景规则。
- API-only smoke 使用 FastAPI TestClient，不启动浏览器，不依赖 DOM selector，不调用 provider。

## 验证结果

已通过：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_node_contract.py -q
# 4 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_agentflow_knowledgebase_coverage.py -q
# 3 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py -q
# 8 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_agentflow_knowledgebase.py tests\test_agentflow_knowledgebase_coverage.py -q
# 7 passed

.\.venv\Scripts\python.exe tools\prompt_optimizer_api_smoke.py --fixture-dir examples\frontend_runtime_service\prompt_optimizer_nodes --output-dir <ignored-runtime-output>
# status=passed, total=6, passed=6, provider_calls_started=0, unsafe_matches=0
```

联合验收补充通过：

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\workbench_prompt_optimizer_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_prompt_optimizer_browser_qa
# passed; desktop/mobile; runtime optimizer requests=2; provider_request_urls=[]

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\workbench_libtv_toolbox_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_libtv_toolbox_browser_qa
# passed; desktop/tablet/mobile; 6 toolbox intents; provider_request_urls=[]

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\workbench_libtv_canvas_header_browser_qa.py --base-url http://127.0.0.1:8793/workbench/ --output-dir data\processed\runs\workbench_libtv_canvas_header_browser_qa
# passed; desktop/tablet/mobile; title/menu/canvas switch/new canvas; provider_request_urls=[]

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
# 886 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; one oversized-file warning: apps/workbench/src/canvas-interactions.js 401 lines

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
# delete_candidate_count=0; manual_review_required_count=0

git diff --check
# exit 0; Windows CRLF conversion warnings only
```

## 非声明

- 不是 Web browser acceptance。
- 不是 provider smoke。
- 不是 human validation。
- 不是 durable memory 声明。
- 不是 SaaS、账号、支付、多用户协作或真实公开视频资源站。

## 后续联合验收

本次已经完成一次 API + Web browser + full pytest + maintenance/retention/diff 联合验收。后续如果 Web UI 继续改 `apps/workbench/**`，需要重新跑上述浏览器 QA 和 full pytest；`canvas-interactions.js` 的 401 行维护 warning 建议单独开 Web 交互拆分任务处理，不放进 prompt optimizer 支撑线。
