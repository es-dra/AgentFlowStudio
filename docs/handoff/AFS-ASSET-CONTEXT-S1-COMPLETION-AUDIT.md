# AFS 资产上下文 S1 完成度审计

日期：2026-06-12

分支与工作树：

```text
codex/afs-asset-context-s1
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-asset-context-s1
```

## 目标

S1 的目标不是只把资产上下文结构写进代码，而是让“敲定一次、全片遵守”形成一份可复现的真实生成证据。工程侧还必须保持 provider gate 纪律，全量 pytest 与浏览器 QA 通过，并覆盖锁定项无条件注入、子图回退、主体参考图选择、预算保底等计划内不变量。

## 当前结论

状态：`blocked_for_live_provider_evidence`

Gate-closed Runtime/Web S1 已验证通过。当前唯一未完成项是真实 MiniMax A/B/C 生成输出，因为本机环境没有打开 image gate：

```text
AFS_ALLOW_REMOTE_IMAGE=true
```

最新验证没有启动真实 provider 调用。这个结果符合 gate 纪律，但还不能算作目标要求的真实生成证据。

## 逐项证据

| 要求 | 当前证据 | 状态 |
|---|---|---|
| `visual_asset v0.1` promote/list/retire，S1 状态只保留 fixed/rejected/retired | `apps/api/runtime_visual_assets.py`；`tests/test_api_runtime_visual_assets.py` | 通过 |
| 空 signature、空 feature card、缺人工确认会拒绝 promote | `tests/test_api_runtime_visual_assets.py` | 通过 |
| 重复 label 返回 warning，resolver 行为确定 | `tests/test_api_runtime_visual_assets.py`；`tests/test_api_runtime_context_resolver.py` | 通过 |
| `Primary character` / `Primary scene` 占位抽取不再产出候选 | `tests/test_api_runtime_prompt_memory_candidates.py` | 通过 |
| extracted context 只留候选区，legacy background 不被 resolver 消费 | `tests/test_api_runtime_prompt_memory_candidates.py`；`tests/test_api_runtime_context_resolver.py` | 通过 |
| `context_subgraph` 禁止前端传资产文本 | `apps/api/runtime_context_resolver.py`；`tests/test_api_runtime_context_resolver.py` | 通过 |
| optimize 只注入已连线或 label 命中的 signature，且数量受控 | `apps/api/runtime_context_resolver.py`；`tests/test_api_runtime_context_resolver.py` | 通过 |
| generate 只消费子图连线可达 fixed assets | `tests/test_api_runtime_context_resolver.py`；`tests/test_api_runtime_generation_comparison.py` | 通过 |
| 无子图请求保持旧 `asset_refs` 路径 | `tests/test_api_runtime_context_resolver.py` | 通过 |
| negative locks 默认无条件注入，除非本次临时解除 | `tests/test_api_runtime_context_resolver.py` | 通过 |
| 临时解除只属于请求级，并进入 trace/bundle | `tests/test_api_runtime_context_resolver.py`；浏览器 QA 报告 | 通过 |
| 可见提示词有预算保底，锁定与身份段不裁剪 | `apps/api/runtime_context_budget.py`；`tests/test_api_runtime_context_resolver.py` | 通过 |
| MiniMax 主体参考图只给人物资产；场景图不占 subject slot | `tests/test_api_runtime_keyframe_reference_assets.py` | 通过 |
| provider prompt 不含内部 gate/claim/secret 治理词 | `tests/test_api_runtime_creative_agent_keyframes.py` | 通过 |
| A/B/C 三臂定义可复现 | `apps/api/runtime_generation_comparisons.py`；`tests/test_api_runtime_generation_comparison.py` | 通过 |
| A 臂为原始 prompt、无 asset refs、无参考图 | `tests/test_api_runtime_generation_comparison.py`；`runs/studio_asset_context_live_comparison_report.json` | 通过 |
| B 臂走新 resolver generate 路径，但排除 fixed asset 注入 | `tests/test_api_runtime_generation_comparison.py`；`runs/studio_asset_context_live_comparison_report.json` | 通过 |
| C 臂走新 resolver generate 路径，并注入 fixed feature/locks/reference | `tests/test_api_runtime_generation_comparison.py`；`runs/studio_asset_context_live_comparison_report.json` | 通过 |
| 浏览器闭环：上传 -> 固定资产 -> 点名未连线提示 -> 一键连线 -> 临时解除 -> 生成 -> A/B/C report | `tools/studio_asset_context_browser_qa.py`；`runs/studio_asset_context_browser_qa_report.json` | gate-closed 通过 |
| live A/B/C runner 可复现且受 gate 保护 | `tools/studio_asset_context_live_comparison.py`；`tests/test_studio_asset_context_live_comparison_tool.py` | readiness 通过 |
| 可复现本地参考图可生成 | `tools/studio_asset_context_sample_reference.py`；`runs/studio_asset_context_sample_reference.png` | 通过 |
| 真实 MiniMax A/B/C 生成输出存在 | 当前环境缺少 image gate 授权；本地 ignored provider config 已用于 no-call readiness，但未做 live 校验 | 缺失 |

## 最新验证

```text
Focused S1 pytest: 34 passed, 1 Starlette/httpx warning
Browser QA: passed, provider gate blocked, provider_calls_started=false
Gate-safety preflight: passed, simulated image gate ready without runner approval, provider_calls_started=false
Studio JS node --check: passed
Full pytest: 798 passed, 1 Starlette/httpx warning
maintenance_audit.py: passed, 0 warnings
git diff --check: passed, Windows CRLF notices only
```

## 当前 gate 状态

```text
AFS_ALLOW_REMOTE_IMAGE: not set
AFS_PROVIDER_CONFIG: not set in shell
ignored provider config: exists in main checkout and was supplied to readiness runner
provider key material: not inspected or persisted
```

## 最后一步

用户显式授权 image provider 后，运行：

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE = "true"
& 'D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe' tools\studio_asset_context_live_comparison.py --provider-config D:\Projects\AgentFlowStudio\configs\providers.local.json --allow-live-provider --sample-reference-output runs\studio_asset_context_sample_reference.png
```

完成目标需要 runner report 同时满足：

```text
runner_mode=live_provider
comparison_status=succeeded
provider_calls_started=true
A.result_ref_count > 0
B.result_ref_count > 0
C.result_ref_count > 0
C.fixed_asset_injection=true
C.reference_image_count=1
```

这一步即使成功，也只代表 provider smoke / runtime evidence；不代表人工验收、商业验证、视频可控性或 durable memory 晋升。
