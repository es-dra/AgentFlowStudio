# Project Manifest Contract

`agentflow_project_manifest` 是 AFS 本地项目工作台索引。当前用途是让测试人员在一个项目有多个 run、package、feedback、profile version 或 provider smoke 时，先打开这一份 manifest，再进入具体 artifact。

它只引用 artifact，不复制 run 输出、私有本地路径、媒体字节、provider response、signed URL、secret、账号状态或 `10-Startup` durable memory。

## 版本

当前 contract：

```text
artifact_type = agentflow_project_manifest
schema_version = 0.1.0
```

## 必填字段

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

允许的 `status`：

```text
in_progress
blocked
ready_for_next_round
```

## 本地内测职责

manifest 必须回答六个问题：

- 这是哪个项目。
- 当前有哪些 runs。
- 哪些 packages 可 review。
- 哪些 feedback refs 只是 raw evidence。
- 哪些 profile versions 可以进入下一轮 context。
- 项目状态是 `in_progress`、`blocked` 还是 `ready_for_next_round`。

manifest 不是执行引擎。它只指向 Round 1、Round 2 或 provider gate artifact，例如：

```text
real_asset_test_report.json
asset_test_package.json
asset_feedback_event.json
asset_profile_version.json
two_round_context_runtime_report.json
provider_safe_manifest.json
```

## Web 视图

read-only Web Memory Workbench 能识别 selected local JSON 中的 `artifact_type=agentflow_project_manifest`。

视图应展示：

- project id、project type、goal、status。
- source assets。
- run refs。
- package refs。
- feedback refs。
- profile version refs。
- boundary flags。

Web 视图仍然只读，只处理 selected-local-JSON。它不扫目录、不跟随私有 ref、不持久化 browser state、不执行 provider、不写 memory。

## 边界规则

Project Manifest v0.1 禁止包含：

- provider config path。
- API key、token、cookie、auth header。
- signed URL 或 provider result URL。
- source media bytes 或 generated media bytes。
- private local absolute path。
- provider response body。
- database/account/sync state。

可以包含 stable artifact refs 和经过脱敏的 local project identifier。

## 示例和验证

示例：

```text
examples/agentflow/project_manifest.example.json
```

验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_project_manifest_contract.py tests/test_web_static_project_manifest.py tests/test_contract_examples.py -q
```

validator 对 secret/private fragments 保持严格，因为 manifest 是测试人员导航入口，不是资产存储。
