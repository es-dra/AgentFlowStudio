# AFS API Adapter 计划

状态：Runtime Service v0.2。

## 目的

API Adapter 是现有 AFS core 外面的一层本地轻量服务。它不是新的执行引擎，也不是数据库层。

它负责把前端动作翻译成安全的后端操作：

```text
frontend action
-> Runtime Service endpoint
-> deterministic AFS function / provider gate
-> ignored runtime output
-> safe artifact refs and report summary
```

## 启动方式

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

Workbench 静态入口由 Runtime Service 提供：

```text
http://127.0.0.1:8790/workbench/
```

可选 runtime root：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service `
  --host 127.0.0.1 `
  --port 8790 `
  --runtime-root data/processed/runs/runtime_service
```

## Endpoint Map

### `GET /health`

返回服务可用状态和边界 flags。前端只用它显示连接状态，不要从 health 推断 provider 是否可用。

### `GET /capabilities`

返回支持的 action 和 status vocabulary。

当前 status：

```text
queued
running
succeeded
failed
blocked
cancelled
```

### `GET /workbench/`

返回 `apps/workbench` 静态前端入口。该入口只服务浏览器工作台文件；
执行仍必须通过 Runtime Service API，不允许浏览器直接调用 CLI、扫描本地目录或读取私有素材。

### `POST /projects`

创建本地 `agentflow_project_manifest`。

Request fields：

- `project_id`
- `project_type`
- `goal`
- `status`

Response includes：

- `manifest`
- safe manifest `artifact_id`

### `GET /projects/{project_id}/manifest`

读取或创建 project manifest。前端应把它当作项目入口，不要通过扫描 runtime 目录重建项目。

### `POST /projects/{project_id}/source-assets`

Registers source assets or references as safe summaries. The browser sends
only `asset_id`, `asset_type`, `label`, and `summary`; the Runtime Service
stores a manifest ref with `ref_kind= safe_summary` and does not persist local
media paths or bytes.

### `POST /projects/{project_id}/content-cards`

Registers user-facing content or scene cards for the creation canvas. The
browser sends `card_id`, `card_type`, `title`, `summary`, and
`target_platform`. The Runtime Service stores a safe content-card summary and
projects it into workbench canvas cards plus the filmstrip.

### `POST /projects/{project_id}/canvas-draft`

Drafts a first Hook / Proof / CTA creation canvas from the project's safe
source summaries. The Runtime Service reads only Project Manifest summaries,
writes `agentflow_runtime_canvas_draft`, appends safe content cards to the
manifest, and records a `draft_canvas` job for the Job Center. It does not call
providers, persist private asset locations, or promote memory.

### `POST /projects/{project_id}/scene-inspector`

Updates the selected scene/content card with safe inspector summaries:
`prompt`, `reference_summary`, `style_direction`, and `retry_intent`.
This endpoint stores planning text only. It does not persist private paths,
media bytes, provider raw responses, or generated outputs.

### `POST /projects/{project_id}/review-decisions`

Records a user-facing review decision for a canvas card or concrete review
candidate. The browser sends `card_id`, optional `candidate_id`, optional
`artifact_id`, `decision` (`keep`, `revise`, or `reject`), `note`, and
`generated_at`. The Runtime Service writes a safe review-decision artifact,
adds it to project feedback refs, and does not promote it to durable memory.

### `GET /projects/{project_id}/workbench-state`

读取前端可直接消费的项目工作台状态。该 endpoint 把 manifest、jobs、artifact refs、provider gate 和 blockers 翻译成用户语言：

- project summary；
- navigation labels；
- canvas cards；
- asset library；
- filmstrip；
- review room candidates and decision counts；
- style memory product summary；
- job center progress, polling policy, and blocked-action guidance；
- activity timeline counts, blockers, latest actions, and safe primary artifact refs；
- project event history；
- provider preflight state；
- advanced evidence refs。

前端应优先用它驱动画布、项目中心、任务状态和审片入口，不应在浏览器端自行拼接底层 artifact 图谱。

`workbench-state` also includes `project_readiness` for the current safe next action and workflow gate statuses, and `activity_timeline` for product-facing runtime trace navigation.

### `GET /artifacts/{artifact_id}`

按 id 读取 safe artifact。

返回 JSON payload 或 text content，以及 metadata：

- `artifact_id`
- `artifact_type`
- `filename`
- `role`
- `media_type`

不返回私有本地路径。

### `POST /runs/asset-test`

运行 Round 1 deterministic asset loop。

必填：

- `project_id`
- `asset_profile_seed`
- `promotion_decision`
- `promotion_rationale`
- `generated_at`
- `decided_at`
- `reviewed_at`

可选：

- `loop`
- `feedback_json`
- `consistency_review_json`
- `project_materials`
- `character_reference_image`
- `reviewer_role`

返回：

- job summary；
- `real_asset_test_report`；
- package、feedback、profile version、context projection、consistency review、review-screen selected files 的 artifact refs。

如果素材缺失，job 可以返回 `blocked` 和有效报告。前端应展示为测试素材 blocker，不要当作 service crash。

### `POST /runs/two-round-validate`

从 Round 1 job 运行 Round 2 context validation。

必填：

- `project_id`
- `round_1_job_id`
- `generated_at`
- `reviewed_at`

返回：

- job summary；
- `two_round_context_runtime_report`；
- Round 2 context projection 和 consistency review 的 artifact refs。

### `POST /feedback`

记录 raw runtime feedback evidence。

该 endpoint 不晋升 memory，只创建 feedback artifact，并更新 project manifest 的 feedback refs。

### `POST /provider/validation-plan`

生成 provider readiness / blocker evidence。

它不会启动 live provider call。live provider execution 仍保持 blocked，直到后续显式 endpoint 和 gate 加入。

返回：

- job summary；
- `provider_safe_manifest`；
- provider blockers；
- artifact refs。

## API Versioning Rule

v0.1 不要随意改 endpoint 名称或 response key。若必须改，需要同步更新：

- `tests/test_api_runtime_service.py`
- `docs/frontend_integration/`
- `examples/frontend_runtime_service/`
- 前端 client / adapter。

## v0.2 计划

- `POST /provider/validation-run`：只在显式 gate 打开时运行 live provider smoke。
- OpenAPI 固定导出。
- 前端 client 生成说明。
- project list / import / export。
- 更细的 job progress。
