# AFS Studio Hard Cleanup 001

Date: 2026-06-11

Owner role: Frontend Contract Steward + Maintainability Steward + QA / Release Gatekeeper

## Goal

Make AFS Studio the only active user-facing frontend and remove retired Workbench / memory-workbench product surfaces from the current code path.

## Cleanup Decision

Delete:

- `apps/workbench/`
- `apps/web/`
- `apps/api/runtime_workbench_static.py`
- Workbench-specific browser QA tools.
- Workbench and static memory-workbench UI tests.
- Active frontend integration docs that instructed new work to use the old Workbench path.

Keep:

- Runtime Service core APIs.
- Prompt optimization Runtime API and local fallback.
- Non-UI production memory, manifest, artifact, and provider-gate contracts.
- Current Studio, Runtime, knowledgebase, and provider-gate handoffs only.

Delete in the 2026-06-12 continuation:

- stale `AFS-WEB-*` and `AFS-LIBTV-*` handoffs;
- stale Workbench/browser-QA superpowers plans and specs;
- stale Web archive files;
- maintenance ledgers that preserved `apps/web`, `apps/workbench`, or `docs/frontend_integration` as active references.

## Replacement Path

Current user-facing frontend:

```text
http://127.0.0.1:<port>/studio/
```

Current frontend source:

```text
apps/studio/
```

## Boundaries

- No provider calls are introduced.
- No secrets, local absolute media paths, signed URLs, provider raw responses, or generated media bytes are added.
- `/workbench/` is retired as a static frontend path.
- Backend API names are not broadly renamed in this slice unless required by tests.
- Old, unused, or misleading docs are deleted when replacement paths and tests are clear; no archive-by-default policy.

## Verification Plan

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py tests\test_web_studio_static.py -q
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

Browser QA:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8806
```

Open `http://127.0.0.1:8806/studio/` and verify canvas creation, node dragging, Bezier connection, prompt optimization, and director setup with provider gates closed.

## Verification Result

2026-06-11 本轮已验证：

- `/studio/` 返回 200，`/workbench/` 返回 404。
- 全量测试：`762 passed, 1 warning`。唯一 warning 为 Starlette / httpx TestClient 依赖提示。
- `tools/maintenance_audit.py` 通过，0 warning。
- `git diff --check` 通过，仅有 Windows CRLF 提示。
- `apps/studio/src/**/*.js` 全部 `node --check` 通过。
- Runtime-hosted 浏览器 QA 通过：双击建节点、提示词优化六段输出、优化浮层避让 prompt bar、端口拖出贝塞尔连线、框选、导演台打开、无横向溢出、无 console/page error。

额外修复：

- 端口拖线热区现在优先识别点位下方的输出端口，避免邻近节点覆盖端口时误判为拖动节点。

## Follow-up UI Polish Result

2026-06-12 本轮追加验证：

- 左上角布局修复：1440px、1024px 和窄屏视口下，抽屉与顶栏边界无重叠，页面无横向溢出。
- 二维导演台可打开：对象列表、2D 网格布置板、相机视锥、灯光光束、人物朝向、道具形状和右侧参数面板均可见。
- 导演台节点可保存布置，节点摘要展示“1 个机位 / 1 个主体 / 3 盏灯”。
- 从底部 dock 添加节点时，新节点出生在画布可视中心，不再落入底部 dock 安全区。
- 导演台节点可通过输出端口连接图片节点，连接线带 `director-edge` 语义样式。
- 图片节点提示词优化浮层显示“导演台布置”来源 chip，优化结果包含机位、FOV、Key Light、Back Light 和“避免光源冲突/机位冲突/空间关系错乱”等约束。
- 浏览器 QA 无 console/page error；provider gate 仍关闭。
- 全量测试：`767 passed, 1 warning`。唯一 warning 为 Starlette / httpx TestClient 依赖提示。
- `repository_retention_review` 的 `manual_review_required_count` 为 0；临时浏览器 QA 截图未留在工作树。
- `tools/maintenance_audit.py` 无失败；`oversized_files` 已清零，仅剩既有 human-facing Markdown 中文覆盖 warning。
- `git diff --check` 通过，仅有 Windows CRLF 提示。

额外维护修正：

- 将二维导演台参数字段拆到 `apps/studio/src/panels/director-fields.js`，避免 `director-shell.js` 超过维护阈值。
- 将导演台 prompt API 测试拆到 `tests/test_api_runtime_director_setup_prompt.py`。
- 将 AgentFlow local AgentOps contract 示例的 `doc_path` 从已删除旧维护文档改为当前 `docs/company_operating_model.md`。
