# AFS TaskRun - Deterministic Promotion Browser Harness - 2026-06-30

## 任务

Task ID: `AFS-T15 Deterministic Promotion Browser Harness`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `fe4be34b535c2193fd199a6c995953ddd2e39692`

Status: implemented, browser/runtime verified, pending commit/push at time of writing.

本轮目标是在 T12/T14 的 fixed visual asset promotion contract 之后，补一条真实浏览器
路径：Runtime seed 一个带 accepted asset-card human gate summary 的节点，Studio
页面打开固定资产面板并提交，最后从 Runtime 视觉资产记录中核验 `promotion_gate`。

## 中文结论

T14 已经证明 payload builder 自身能正确带上 provenance，但还没有证明真实 `/studio/`
交互会把这个 payload 送到 Runtime 并落成安全的 visual asset record。T15 新增
`tools/studio_visual_asset_promotion_browser_qa.py`，使用临时 Runtime root、真实浏览器
和 FastAPI TestClient POST proxy 完成这一段。

浏览器报告显示：固定资产提交成功，Runtime 记录中的 `promotion_gate` 包含
`source_human_gate_id=runtime_human_gate_accepted` 和
`source_asset_card_candidate_id=asset_card_candidate_main`，console error 为 0，
response error 为 0，`provider_calls_started=false`。本轮没有打开 provider gate，
没有生成媒体，没有部署，也没有声明 human creative acceptance 或 business validation。

本轮的工程判断是：accepted human gate summary 已经是 Studio 后续固定资产操作的
安全依据，但它必须先被 Runtime Studio-state 安全持久化，才能支持刷新、恢复和浏览器
级回归。直接把字段塞进已有大型 sanitizer 会制造新的维护债，所以本轮把
`humanGateDecisions` 单独放进小模块处理，只保留人类 gate ID、目标类型、目标 ID、
决策、状态、记录时间和不写长期记忆声明。这样既能让浏览器路径证明真实 UI 行为，
又不会让前端接触 provider raw、本地绝对路径、signed URL、媒体字节或公司知识库写入。
这条 harness 只证明“UI 到 Runtime 的 contract 可以走通并留下安全记录”，不证明资产
创意质量已经被人类接受，也不证明任何远程模型能力已经可用。后续如果要做 provider
smoke，必须另开任务、明确能力 gate，并继续把 runtime verification、provider smoke、
human acceptance 和 business validation 分开记录。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `tools/studio_visual_asset_promotion_browser_qa.py` | T15 browser harness | Keep; single-purpose browser/runtime proof for promotion provenance. |
| `tests/test_studio_visual_asset_promotion_browser_qa_tool.py` | T15 focused tests | Keep; covers harness path defaults and seeded Studio-state contract. |
| `apps/api/runtime_studio_state_human_gate.py` | T15 sanitizer module | Keep; avoids inflating the existing param-values module above 300 lines. |
| `apps/api/runtime_studio_state_params.py` | T15 sanitizer wiring | Keep; allows safe `humanGateDecisions` persistence. |
| `tools/studio_asset_context_browser_qa_support.py` | T15 helper consolidation | Keep; common Studio static route helper for browser QA tools. |
| `tools/studio_asset_context_browser_qa.py`, `tools/studio_full_coverage_browser_qa.py` | T15 dedupe | Keep; behavior unchanged, helper imported from support. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15 records | Keep. |
| External execution state YAML | T15 state | Update minimally outside AFS git. |
| `runs/studio_visual_asset_promotion_browser_qa_t15.*` | ignored runtime evidence | Generated locally, not committed. |
| `docs/demo-docs-20260629/` | existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-DETERMINISTIC-PROMOTION-UI-HARNESS-20260630.md`
- external `AFS-Goal-Driven-Execution-State-v0.1.yaml`
- external `AFS-Task-Ledger-v0.1.md`
- `apps/studio/src/panels/visual-asset-panel.js`
- `apps/studio/src/panels/visual-asset-promotion-request.js`
- `apps/studio/src/human-gate-provenance.js`
- `apps/api/runtime_visual_assets.py`
- Runtime Studio-state sanitizer modules
- existing browser QA tools and tests

## Write Scope

- `apps/api/runtime_studio_state_human_gate.py`
- `apps/api/runtime_studio_state_params.py`
- `tools/studio_visual_asset_promotion_browser_qa.py`
- `tools/studio_asset_context_browser_qa_support.py`
- `tools/studio_asset_context_browser_qa.py`
- `tools/studio_full_coverage_browser_qa.py`
- `tests/test_studio_visual_asset_promotion_browser_qa_tool.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff
- external execution state YAML

## Contract

The browser harness verifies:

- Runtime Studio-state can persist a safe `humanGateDecisions` summary.
- Studio hydration can open the seeded image node and fixed visual asset modal.
- The UI submit path calls Runtime `POST /projects/{project_id}/visual-assets/promote`.
- The Runtime visual asset record stores a safe `promotion_gate`.
- `promotion_gate` carries sanitized human gate and asset-card candidate refs.
- Runtime record keeps `media_bytes_returned_by_api=false`,
  `provider_raw_response_stored=false`, `writes_long_term_memory=false`, and
  `writes_company_kb=false`.
- The browser report records `provider_calls_started=false`, zero console errors,
  and zero actionable response errors.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_studio_visual_asset_promotion_browser_qa_tool.py -q
# red baseline: ImportError for missing studio_visual_asset_promotion_browser_qa
# final: 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_studio_visual_asset_promotion_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_support.py -q
# 12 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\studio_visual_asset_promotion_browser_qa.py --report runs\studio_visual_asset_promotion_browser_qa_t15.json --timeout-ms 90000
# passed; ignored report shows promotion_gate, console_error_count=0,
# response_error_count=0, provider_calls_started=false

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_studio_visual_asset_promotion_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_tool.py tests\test_studio_asset_context_browser_qa_support.py -q
# 27 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest
# first run failed because initial sanitizer placement pushed
# runtime_studio_state_param_values.py above the 300-line module guard
# final run: 712 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4

git diff --check
# passed
```

## Evidence State

```text
runtime_browser_verified_deterministic_promotion_harness
```

This is browser/runtime verification only. It is not provider smoke, not
generated media evidence, not human creative acceptance, not business
validation, not deploy verification, and not server three-end sync.

## Cleanup Review

- The first sanitizer placement was rejected by full pytest because it created
  line-count maintenance debt; the helper was split into
  `runtime_studio_state_human_gate.py`.
- Two existing browser QA scripts no longer carry duplicate Studio static route
  helpers.
- New browser harness is below 300 lines and does one scenario.
- Generated `runs/` evidence remains ignored and uncommitted.
- `docs/demo-docs-20260629/` remains untouched.

## Deferred Items

- Provider smoke remains blocked until the user explicitly authorizes a specific
  capability and provider gate.
- Human creative acceptance still requires a human reviewer using a real review
  packet; this browser harness does not satisfy it.
- Server `/home` and `/opt` sync/deploy are intentionally not part of this codex
  branch slice.

## Next Valid Task

```text
AFS-T16 Provider-Smoke Readiness Gate or Goal-Mode Branch Integration Review
```
