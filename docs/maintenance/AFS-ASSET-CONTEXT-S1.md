# AFS 资产语义与图谱上下文 S1 维护账本

日期：2026-06-12

责任角色：Runtime/API 集成、Studio 交互、Provider Gate 维护。

## 目标

本轮只重整 `b2d2df0` 之上的语义层。上传、预览、provider gate、safe artifact、生成图回流为 image asset、MiniMax adapter 和非声明边界保持不推倒重写。

新的工程边界是：固定资产是生成强约束的唯一来源，画布连线决定生成时携带哪些资产，提示词优化只生成用户可见提示词。

## 维护决策

- 新增 `visual_asset v0.2`，只保存安全引用和人工确认后的特征卡，不保存图片字节；v0.2 追加 `supersedes_asset_id` 作为同名资产版本链。
- 上传图和生成图在 promote 之前只是 image asset candidate，不是 fixed visual asset。
- `visual_asset` 的 S1 状态只包含 `fixed`、`rejected`、`retired`。
- `Primary character`、`Primary scene` 这类占位 slot 不再产生候选记录。
- 正常抽取只写入 `extracted_context`，带 `source_node_id`、`confidence` 和 `created_at`，不再自动 merge 到 `characters`、`scenes` 或 `style_preferences`。
- 存量 `creative_memory_state.characters/scenes/style_preferences` 作为 `legacy_background_context` 隔离，不迁移，不被新 resolver 当作 fixed asset 消费。
- `context_subgraph` 是客户端断言，不是安全边界；后端只接受 asset id，并按 id 从 Runtime 资产库读取特征卡、锁定项和参考图。
- `context_subgraph` 跳数规则：`generation` 与 `director` 边消耗最多 3 跳预算；`reference` 边不消耗普通预算，但最多连续 6 条以防环路。节点/边总闸仍是 24/32。
- Generate 模式 fixed asset 注入上限：人物最多 3 个 full feature card，场景最多 1 个 full feature card；超出连线资产降级为 signature-only，并以 `degraded_to_signature_over_limit` 写入 `context_bundle.excluded_assets`。
- 同项目同类型同 label 的多个 fixed asset 只选择版本链末端；无 `supersedes_asset_id` 链时选择最新 `server_recorded_at`，被排除项记录 `superseded_by_newer_label_version`。
- Web 仍是单画布，不新增模式 Tab；工作模式只体现在 Runtime trace、artifact 和 API 行为中。
- 浏览器 QA 以 `tools/studio_asset_context_browser_qa.py` 作为可复跑入口。当前 Windows/Chrome 环境中页面内 mutating POST 到 Runtime 会挂起，脚本用 FastAPI TestClient 对页面发出的 POST/PUT 做同 runtime_root 代理；报告显式记录 `browser_api_post_proxy=fastapi_testclient`，不把它声明为纯浏览器网络证据。
- 真实 A/B/C evidence 以 `tools/studio_asset_context_live_comparison.py` 作为可复跑入口。该脚本默认只产出 gate-closed readiness report；真实图片 provider 调用必须同时满足 `AFS_ALLOW_REMOTE_IMAGE=true`、provider config、`--allow-live-provider` 和本地参考图。参考图可以来自 `--reference-image`，也可以由 `--sample-reference-output` 通过 `tools/studio_asset_context_sample_reference.py` 生成。

## 验证计划

```powershell
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' -m pytest tests\test_api_runtime_visual_assets.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_generation_comparison.py
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_web_studio_static.py
Get-ChildItem -Path apps\studio\src -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' -m pytest
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' tools\studio_asset_context_browser_qa.py
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' tools\studio_asset_context_live_comparison.py
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' tools\maintenance_audit.py
git diff --check
```

## 最新验证结果

```text
Focused Runtime/Web set: 34 passed, 1 Starlette/httpx warning.
Full pytest: 798 passed, 1 Starlette/httpx warning.
Studio JS node --check: passed.
Browser QA script: passed with provider gate closed; report records browser API POST proxy via FastAPI TestClient due local Chrome POST hang.
Live comparison runner gate-closed readiness: passed with ignored provider config path supplied; provider_calls_started=false.
Live comparison gate-safety preflight: simulated `AFS_ALLOW_REMOTE_IMAGE=true` without `--allow-live-provider`; blocked with `live_provider_flag_missing`, provider_calls_started=false.
Maintenance audit: passed with 0 warnings.
git diff --check: passed with Windows CRLF notices only.
```

## 边界

- `AFS_ALLOW_REMOTE_IMAGE=true` 只授权图片能力，不授权 LLM、ASR、video 或外部下载。
- A/B/C 真实 provider 调用必须显式打开 image gate。
- Runtime verification 不是 human acceptance，也不是 business validation。
- comparison report 和 extracted context 都只是证据，不会自动晋升为长期记忆。
