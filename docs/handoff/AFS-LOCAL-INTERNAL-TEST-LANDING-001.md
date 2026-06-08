# AFS 本地内测落地交接 001

日期：2026-06-04

Owner role：Release Integrator + Memory / Evidence Steward

## 范围

本切片把 AFS 从“本地可交测基线”推进到“本地内测可跑闭环”。完成链路：

```text
Asset Profile Review Screen
-> Real Asset Test Run Harness
-> Two-Round Context Runtime Validation
-> Project Manifest v0.1
-> Provider Validation Gate
```

这是本地 deterministic workbench slice，不是 SaaS，不是 provider product validation，不是 human acceptance，不是 business validation，也不会写 durable `10-Startup` memory。

## 已实现

- Web Asset Profile Review Screen：选择本地 asset context projection 或 consistency review JSON 后，显示 included refs、blocked refs、tester feedback 分类、next recommendation 和 non-claims。
- `asset-test-run-harness`：在 ignored runtime path 下生成 Round 1 package，包括 package、feedback、candidate、显式 promotion decision、profile version、context projection、consistency review、Markdown report 和 review-screen selected-files manifest。
- `asset-two-round-validate`：从 Round 1 profile version evidence 派生 Round 2 context projection 和 consistency review，并输出 `two_round_context_runtime_report.json` 与 Markdown。
- Project Manifest v0.1：新增本地 JSON contract validator、example 和 read-only Web project view。
- `asset-provider-validation-gate`：默认只输出 blocked 或 ready provider gate evidence、`provider_safe_manifest.json` 和 Markdown report，不默认启动 provider call。

## 默认 runtime 输出

```text
data/processed/runs/local_internal_test/asset_loop_round_1/
data/processed/runs/local_internal_test/asset_loop_round_2/
data/processed/runs/local_internal_test/provider_validation_gate/
```

这些都是 runtime path。不要提交真实素材、生成媒体、provider config、secret、signed URL 或 private local path。

## Tester 入口

主 runbook：

```text
docs/local_internal_test_runbook.md
```

关键命令：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main asset-test-run-harness --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json --promotion-decision promoted --promotion-rationale "Operator explicitly approved this profile version for round two context projection." --decided-at 2026-06-04T00:20:00+08:00 --reviewed-at 2026-06-04T00:30:00+08:00
.\.venv\Scripts\python.exe -m apps.cli.main asset-two-round-validate --round-1 data/processed/runs/local_internal_test/asset_loop_round_1
.\.venv\Scripts\python.exe -m apps.cli.main asset-provider-validation-gate --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json
```

## 已跑过的 smoke

Fixture-only runtime smoke：

- Round 1：`completed_with_blocks`，block id 为 `project_materials_missing`。
- Round 2：`runtime_verification_status=verified`，但 `improvement_assessment=no_clear_improvement`，原因是 `test_materials_insufficient`。
- Provider gate：`blocked`，`provider_calls_started=false`。

Loulan 显式素材 runtime smoke：

- 使用用户提供的本地 LoulanSceneAssets 和角色参考图，作为 ignored runtime input。
- Round 1：passed。
- Round 2：`runtime_verification_status=verified`，`improvement_assessment=improved`。
- 输出未持久化 Loulan 绝对路径或参考图文件名。

Provider smoke：

- 显式 image/video gate 和本地 provider config 后，provider gate 先达到 `ready_not_run`。
- 初次 live smoke 暴露 Kling transport instability。
- 已修复 httpx 到 curl fallback、poll transient retry、curl TLS handshake retry。
- 修复后 Minimax image i2i 和 Kling I2V 均产出成功。
- 该结果只是 provider smoke / runtime evidence，不是 human acceptance 或 business validation。

## 验证

本切片曾完成：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
node --check apps\web\memory-workbench-production-asset-review-screen.js
node --check apps\web\memory-workbench-asset-review-render.js
node --check apps\web\memory-workbench-project-manifest.js
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

结果：

- CLI help/version passed。
- Web JS syntax checks passed。
- Focused test groups passed。
- Full pytest passed：994 tests。
- 后续 Loulan/provider recovery focused tests passed：Web 15 tests、Production Memory asset/provider 60 tests、contract/CLI/project manifest 33 tests、Kling 23 tests。

Browser smoke 当时没有声明为 human acceptance：Browser tool / Playwright 不可用，Edge headless 被环境阻塞。

## 剩余风险

- Loulan 只证明结构和 runtime compatibility，不证明人工验收或商业价值。
- Fixture-only run 正确输出 `no_clear_improvement`，不能当成产品改善证据。
- Provider smoke 只说明 adapter/gate 在当时配置下可跑，不代表稳定生产 SLA。
- 历史项目文档仍有旧英文和旧 `Company` 表达，后续由 docs-only 中文摘要归档切片处理。

## 非声明边界

- 不声明 human acceptance。
- 不声明 business validation。
- 不写 durable memory。
- 不晋升 `10-Startup` / COS active rule。
- 不保存 secret、signed URL、provider response body、私有素材字节或生成媒体。
