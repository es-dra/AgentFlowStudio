# AFS 本地内测 Runbook

状态：AgentFlow Studio 本地内测操作说明。

本文把当前 Production Memory asset loop 变成测试人员可重复执行的本地流程。它不是 SaaS validation，不是 human acceptance，不是 business validation，也不会写入 durable `10-Startup` memory。

## 适用范围

测试人员拿到显式本地项目素材后，可以跑一条可审计链路：

```text
Round 1 asset package
-> tester feedback evidence
-> candidate update
-> explicit promotion decision
-> profile version
-> Round 2 context projection
-> consistency review
-> optional provider gate smoke
```

AFS 只在 ignored runtime path 下保存结构化 runtime artifact。不要提交 source media、generated media、provider config、signed URL、secret、cookie 或 private local path。

## 输入

必填：

- `--asset-profile-seed`：已脱敏 seed JSON。
- `--project-materials`：测试人员显式提供的本地 ignored 项目目录。
- `--feedback-json`：已脱敏 tester feedback fixture 或 JSON evidence。
- `--consistency-review-json`：已脱敏 consistency review fixture。
- `--output`：ignored runtime 输出目录。

可选：

- `--character-reference-image`：显式本地 ignored 角色参考图。
- `--provider-config`：provider gate 使用的本地配置路径。

推荐 runtime path：

```text
data/processed/runs/local_internal_test/<project>_asset_loop_round_1/
data/processed/runs/local_internal_test/<project>_asset_loop_round_2/
data/processed/runs/local_internal_test/<project>_provider_validation_gate_plan/
data/processed/runs/local_internal_test/<project>_provider_validation_gate_live/
```

## Round 1

运行 deterministic asset harness：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main production-memory-loop-run-real-asset-test-harness `
  --asset-profile-seed data/processed/runs/local_internal_test/loulan_fixture_inputs/asset_profile_seed.loulan.local.json `
  --feedback-json data/processed/runs/local_internal_test/loulan_fixture_inputs/asset_feedback.loulan.local.json `
  --consistency-review-json data/processed/runs/local_internal_test/loulan_fixture_inputs/asset_consistency_review.loulan.local.json `
  --project-materials "<explicit local project materials path>" `
  --character-reference-image "<explicit local character reference image path>" `
  --promotion-decision promoted `
  --promotion-rationale "Runtime-only explicit decision for Round 2 context projection; not durable memory." `
  --generated-at 2026-06-04T00:00:00+08:00 `
  --decided-at 2026-06-04T00:20:00+08:00 `
  --reviewed-at 2026-06-04T00:30:00+08:00 `
  --output data/processed/runs/local_internal_test/<project>_asset_loop_round_1
```

预期输出：

```text
operator_loop/
asset_profiles.json
asset_profile_readiness.json
asset_test_package.json
asset_test_package.md
asset_feedback_event.json
asset_profile_update_candidate.json
asset_profile_promotion_decision.json
asset_profile_version.json
asset_profile_context_projection.json
asset_consistency_review.json
real_asset_test_report.json
real_asset_test_report.md
review_screen_selected_files.json
```

通过条件：

- `real_asset_test_report.json` 的 `run_status=passed`。
- `provider_calls_started=false`。
- `writes_long_term_memory=false`。
- `writes_company_kb=false`。
- 不持久化 private local path。

如果 `run_status=completed_with_blocks`，检查 `blocks`。常见原因：

- `project_materials_missing`：只跑了 fixture。
- `profile_version_missing`：promotion decision 没有生成 profile version。
- `context_projection_not_ready`：没有可用 promoted profile version。
- `consistency_review_not_ready`：review fixture 或 projection 不可用。

## Review Screen

打开 Web Memory Workbench，选择 Round 1 输出的本地 JSON。Review Screen 必须回答：

- 当前测试哪个 character、scene、profile、profile version。
- 哪些 refs included。
- 哪些 refs blocked，以及原因。
- tester feedback 是 `kept`、`partially_kept`、`failed` 还是 `unknown`。
- 下一步建议是 `no_change`、`candidate`、`blocked`、`retired` 还是 `promoted`。
- 当前不声明 human acceptance、business validation、durable memory 或 `10-Startup` promotion。

`review_screen_selected_files.json` 是 operator 选择文件提示。Web UI 保持 read-only、selected-local-JSON only。

## Round 2

运行 context runtime validation：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main production-memory-loop-two-round-context-runtime-validation `
  --round-1 data/processed/runs/local_internal_test/<project>_asset_loop_round_1 `
  --consistency-review-json data/processed/runs/local_internal_test/loulan_fixture_inputs/asset_consistency_review.loulan.local.json `
  --generated-at 2026-06-04T00:40:00+08:00 `
  --reviewed-at 2026-06-04T00:50:00+08:00 `
  --output data/processed/runs/local_internal_test/<project>_asset_loop_round_2
```

通过条件：

- `two_round_context_runtime_report.json` 的 `runtime_verification_status=verified`。
- 每条 included Round 2 context ref 都有 profile version、source profile version id、source decision id、evidence refs。
- superseded 或 blocked refs 不进入 included context。
- 报告继续声明 no human acceptance、no business validation、no durable memory、no `10-Startup` write。

改善解释：

- `improved`：结构上能复用 evidence-backed promoted profile context。
- `no_clear_improvement`：检查 `reason_if_not_improved`。
- `blocked`：检查 controls 和 blocked refs。

允许的 no-improvement reasons：

```text
context_insufficient
feedback_unclear
profile_granularity_wrong
test_materials_insufficient
provider_or_output_randomness_too_high
cannot_judge
```

## Project Manifest

Round 1 和 Round 2 artifact 存在后，用 Project Manifest v0.1 作为项目工作台入口。

最小 contract：

```json
{
  "artifact_type": "agentflow_project_manifest",
  "schema_version": "0.1.0",
  "project_id": "proj_xxx",
  "project_type": "short_video_campaign",
  "goal": "...",
  "source_assets": [],
  "runs": [],
  "packages": [],
  "feedback_refs": [],
  "profile_version_refs": [],
  "status": "in_progress",
  "does_not_store_secrets": true,
  "does_not_store_private_asset_bytes": true,
  "does_not_auto_sync": true
}
```

manifest 只引用 artifact，不复制 output content、provider responses、signed URLs、media bytes、secrets 或 private paths。

## Provider Gate

Provider validation 是可选 smoke，必须在 deterministic Round 1/Round 2 通过之后再打开。

readiness-only plan：

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE='true'
$env:AFS_ALLOW_REMOTE_VIDEO='true'

.\.venv\Scripts\python.exe -m apps.cli.main production-memory-loop-provider-validation-gate `
  --request-validation `
  --asset-profile-seed data/processed/runs/local_internal_test/loulan_fixture_inputs/asset_profile_seed.loulan.local.json `
  --output data/processed/runs/local_internal_test/<project>_provider_validation_gate_plan
```

未授权时必须输出 blocked evidence。授权后也只记录 capability、request summary、status、artifact refs 和 redacted metadata，不保存 secret、signed URL、媒体字节或私有路径。

## 最小验收清单

- Round 1 能生成完整 package 和 review screen selected files。
- Round 2 included refs 可追溯到 profile version 与 evidence refs。
- blocked refs 不进入下一轮 context。
- Project Manifest 能引用 Round 1 / Round 2 / provider gate 输出，但不复制内容。
- provider smoke 只作为 runtime evidence，不写成人工验收或商业验证。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest tests/test_production_memory_asset_test_run_harness.py tests/test_production_memory_two_round_context_runtime_validation.py tests/test_production_memory_provider_validation_gate.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_project_manifest_contract.py tests/test_web_static_project_manifest.py tests/test_contract_examples.py -q
```
