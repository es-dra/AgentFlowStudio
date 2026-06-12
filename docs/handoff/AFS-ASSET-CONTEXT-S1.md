# AFS 资产语义与图谱上下文 S1 交接

日期：2026-06-12

分支与工作树：

```text
codex/afs-asset-context-s1
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-asset-context-s1
```

## 已完成

- 新增 `visual_asset v0.1` Runtime 存储路径：
  `projects/<project_id>/visual_assets/<visual_asset_id>/visual_asset.json`。
- 新增 visual asset 的 promote、list、retire API。
- promote 要求人工 review、非空 signature、非空 feature card 和候选 image asset 引用；不依赖 LLM gate。
- 同项目同类型 label 重复时返回 warning，但不阻塞；resolver 后续按确定性排序处理。
- 新增 `context_subgraph v0.1`、请求级 `temporary_lock_overrides` 和 `context_bundle v0.1`。
- prompt optimization 和 keyframe generation 在携带子图时共用 resolver。
- optimize 视野可看全项目 fixed assets，但只注入已连线或 label 命中的 signature，最多 4 条；其他 fixed assets 只返回给面板参考。
- generate 视野只消费子图连线可达的 fixed assets，读取完整 feature card、negative locks 和主体参考图。
- 锁定项默认无条件注入 provider prompt；临时解除只影响本次请求，不修改资产。
- MiniMax 单参考图位只给人物资产；场景资产不会占 subject reference。
- 新增 `generation_comparison_report v0.1`：A 为裸 prompt 旧路径，B 为新 resolver 但排除 fixed asset 注入，C 为 B 加 fixed asset feature/locks。
- Studio 会发送 `context_subgraph`，提供最小固定资产确认面板，在节点上保存 fixed visual asset id，并显示“本次携带”摘要。
- 优化面板会标注 fixed assets 的 connected / unconnected 状态；点名但未连线的资产提供一键连线；best-effort 锁定冲突提供“本次解除”，只写入请求级 `temporary_lock_overrides`。
- 新增可复跑浏览器 QA：`tools/studio_asset_context_browser_qa.py`。该脚本启动临时 Runtime、打开 Chrome、走上传 -> 固定 -> 点名未连线 -> 一键连线 -> 临时解除 -> 生成 -> A/B/C report，并生成 `runs/studio_asset_context_browser_qa_report.json` 与截图。
- 新增 S1 A/B/C evidence runner：`tools/studio_asset_context_live_comparison.py`。默认只写 gate-closed readiness report；只有同时设置 `AFS_ALLOW_REMOTE_IMAGE=true`、provider config、`--allow-live-provider` 和真实本地 `--reference-image`，或显式生成 `--sample-reference-output`，才允许图片 provider 调用。
- 新增 deterministic 参考图生成器：`tools/studio_asset_context_sample_reference.py`，用于在不接触私有素材和 provider 的情况下生成可复现 PNG 参考图。
- 新增完成度审计：`docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md`，逐项列出当前已验证要求和唯一缺口（真实 MiniMax A/B/C 输出）。

## 不在 S1

- LLM 反推特征卡。
- 资产抽屉卡片管理、编辑和版本化。
- storyboard shot schema 与一键铺画布。
- 未经 `AFS_ALLOW_REMOTE_IMAGE=true` 授权的真实 provider A/B/C 评分。

## 已跑验证

```text
Focused Runtime/Web set: 34 passed, 1 Starlette/httpx warning after S1 sample-reference fixes.
Full pytest: 798 passed, 1 Starlette/httpx warning after S1 sample-reference fixes.
Studio JS node --check: passed.
CLI help/version: passed.
Browser QA: `tools/studio_asset_context_browser_qa.py` passed with provider gate closed; report records `browser_api_post_proxy=fastapi_testclient` because local Chrome POST to Runtime hangs in this environment.
Live comparison runner: gate-closed readiness passed; `provider_calls_started=false`; report path is `runs/studio_asset_context_live_comparison_report.json`.
Gate-safety preflight: simulated `AFS_ALLOW_REMOTE_IMAGE=true` without `--allow-live-provider`; runner blocked with `live_provider_flag_missing`; report path is `runs/studio_asset_context_gate_safety_report.json`.
Maintenance audit: passed with 0 warnings.
git diff --check: passed with Windows CRLF notices only.
```

## 合并前仍需确认

No local engineering verification remains open on the gate-closed S1 implementation. Live MiniMax evidence still requires explicit `AFS_ALLOW_REMOTE_IMAGE=true` authorization and `--allow-live-provider`. The local ignored provider config in the main checkout has been supplied to the no-call readiness runner without reading or persisting its contents. A local reference image can be supplied with `--reference-image` or generated deterministically with `--sample-reference-output`.

Recommended live command after user authorization:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE = "true"
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' tools\studio_asset_context_live_comparison.py --provider-config D:\Projects\AgentFlowStudio\configs\providers.local.json --allow-live-provider --sample-reference-output runs\studio_asset_context_sample_reference.png
```

Provider gate 默认关闭。即便打开 image gate，也不代表 video、LLM、ASR 或外部下载已被授权。
