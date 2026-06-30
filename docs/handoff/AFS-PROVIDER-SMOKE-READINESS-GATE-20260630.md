# AFS TaskRun - Provider Smoke Readiness Gate - 2026-06-30

## Task

Task ID: `AFS-T16 Provider-Smoke Readiness Gate`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `abea0d15edd5c7274ecb1be955baec055b669889`

Status: implemented and locally verified; pending commit/push at time of writing.

本轮目标不是运行 live provider smoke，而是校准已有的 no-cost readiness 工具，避免把环境变量 gate 已开启误判为
“本会话已授权 provider 调用”。这条 gate 服务下一轮真实 provider smoke 的启动判断，但自身不发起 LLM、image、
video、vision、ASR 或 external download。

## 中文结论

旧的 `tools/afs_provider_connected_validation_readiness.py` 已经能检查 Runtime health、Runtime actions、GFR
provider validation packet、provider config 是否存在，以及 LLM/image/video/vision gate 的投影状态。问题是：在
`AFS_ALLOW_REMOTE_LLM=true` 和 `AFS_ALLOW_REMOTE_IMAGE=true` 的机器上，旧报告会直接返回
`ready_for_provider_smoke`。这与当前项目书规则冲突，因为环境 gate 只是技术状态，不等于当前任务获得了 live
provider 调用授权。

本轮把状态机改为三层：

- `ready_for_authorization`: 技术面接近就绪，但 LLM/image 必要 gate 仍未开启。
- `ready_for_human_authorization`: 技术面和必要 gate 都已就绪，但当前任务没有显式 live smoke 授权。
- `ready_for_provider_smoke`: 只有在 no-cost readiness 工具被显式传入 `--live-smoke-authorized` 后才返回；工具本身仍
  只做检查，不会发起 provider call。

当前本地真实报告状态为 `ready_for_human_authorization`：GFR packet 存在，Runtime health 为 `ready`，Runtime
required actions 齐全，provider config 来源存在但不披露真实路径，LLM/image gate 投影为 true，video/vision 为
false。由于本轮没有用户授权 live smoke，报告明确记录
`human_live_provider_smoke_authorized=false`、`env_gates_are_not_authorization=true`、
`provider_calls_allowed_by_this_tool=false`、`provider_calls_started=false`。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `tools/afs_provider_connected_validation_readiness.py` | T16 readiness gate calibration | Keep; reuses existing tool and avoids a second provider-readiness concept. |
| `tests/test_afs_provider_connected_validation_readiness.py` | T16 contract tests | Keep; locks env-gate-not-authorization behavior and secret/path non-disclosure. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T16 records | Keep. |
| This handoff | T16 TaskRun evidence | Keep. |
| External execution state YAML | T16 state | Update minimally outside AFS git. |
| `runs/provider_smoke_readiness_gate_t16.json` | ignored local evidence | Generated locally, not committed. |
| `docs/demo-docs-20260629/` | pre-existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-DETERMINISTIC-PROMOTION-BROWSER-HARNESS-20260630.md`
- `docs/handoff/AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617.md`
- `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-READINESS-20260617.json`
- `docs/GFR_EXECUTION_PROJECTION.md`
- `README.md`
- `pyproject.toml`
- `apps/api/runtime_service.py`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tools/afs_provider_connected_validation_readiness.py`
- `tests/test_afs_provider_connected_validation_readiness.py`
- project-book execution state, task ledger, runbook, execution spec, readiness review, and project book

## Write Scope

- `tools/afs_provider_connected_validation_readiness.py`
- `tests/test_afs_provider_connected_validation_readiness.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff
- external execution state YAML

## Contract

The provider-smoke readiness gate now guarantees:

- It is a no-cost readiness report, not a provider smoke runner.
- It checks Runtime health and required actions through a temporary local Runtime TestClient.
- It checks provider config presence without printing the real path or reading provider secrets.
- It records provider gate projection but does not infer human approval from environment variables.
- It requires explicit readiness authorization before returning `ready_for_provider_smoke`.
- It keeps `provider_calls_started=false`, `secrets_printed=false`, and `provider_calls_allowed_by_this_tool=false`.
- It keeps provider smoke, runtime verification, human acceptance, business validation, and durable memory promotion separate.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_provider_connected_validation_readiness.py -q
# 5 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe tools\afs_provider_connected_validation_readiness.py --report runs\provider_smoke_readiness_gate_t16.json
# status=ready_for_human_authorization
# provider_calls_started=false
# secrets_printed=false
# env_gates_are_not_authorization=true
# path_disclosed=false

.\.venv\Scripts\python.exe -m pytest
# 713 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9, oversized_files=59

YAML parse for external execution state
# yaml_parse_ok

git diff --check
# passed
```

## Evidence State

```text
structure_verified_provider_smoke_readiness_gate_no_provider_call
```

This is readiness/contract verification only. It is not live provider smoke,
not generated media evidence, not human creative acceptance, not business
validation, not deploy verification, and not server three-end sync.

## Cleanup Review

- Reused the existing provider-readiness tool instead of adding a parallel readiness artifact.
- Added one explicit status instead of creating a new provider smoke runner.
- Did not read provider config contents, provider keys, signed URLs, cookies, raw responses, or local media bytes.
- No Runtime/OpenAPI/Studio product behavior changed.
- Generated `runs/` report remains ignored and uncommitted.
- `docs/demo-docs-20260629/` remains untouched.

## Deferred Items

- Live LLM + image/keyframe provider smoke still requires explicit user authorization of the exact capability scope and cost/risk boundary.
- Video, vision, ASR, and external download remain separate authorization gates.
- Human creative acceptance requires a separate human review packet and cannot be inferred from readiness or smoke.
- Server `/home` and `/opt` sync/deploy are intentionally not part of this codex branch slice.

## Next Valid Task

```text
AFS-T17 Goal-Mode Branch Integration Review or authorized one-sample LLM+image provider smoke
```
