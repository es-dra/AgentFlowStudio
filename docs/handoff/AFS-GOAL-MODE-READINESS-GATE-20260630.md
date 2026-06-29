# AFS 第四波 TaskRun Packet - Goal-Mode Readiness Gate - 2026-06-30

## Task

Task ID: `AFS-T3 Goal-Mode Readiness Gate`

本轮目标是判断第一、第二、第三波成果之后，AFS 是否可以进入长周期 Codex 目标模式开发。本轮不是功能开发，不打开 provider gate，不提交，不推送，不部署，不做服务器 runtime health 检查。

任务分类：`Deep` release/readiness gate，带 QA / Release Gatekeeper 判断。

## 中文门禁结论

本轮结论很直接：前三波成果已经形成了可以解释、可以归属、可以继续收口的本地候选基线，但还不能作为“干净冻结基线”启动长周期无人值守开发。原因不是产品方向不清楚，也不是 Runtime 与 Studio 的合同没有治理，而是全量测试仍然有四个失败。只要全量测试仍是红色，后续大范围目标模式就会把真实测试债务和新增开发风险混在一起，下一轮很难判断问题到底来自旧测试合同、旧维护阈值，还是来自新功能改动。

因此，本轮不建议提交、推送或部署，也不建议把当前状态同步到服务器作为新运行基线。更稳妥的路线是先做一个很小的测试合同校准任务：把两个已经过时的结构化错误断言修正为当前 Runtime safe error payload 的真实合同；再处理两个过硬的静态行数阈值，选择有证据的模块拆分，或者把测试改成“模块职责已经拆出、维护审计继续报警、后续拆分有明确计划”的真实维护合同。这个任务完成并通过全量验证后，再做基线冻结、提交、推送和三端同步。

当前证据等级只能表述为“结构已核验，但全量测试仍有阻塞项”。这不是服务器健康，不是 provider smoke，不是人类验收，也不是业务验证。下一轮如果要进入 full goal prompt，必须把本文件、前三波 handoff、OpenAPI snapshot、media contract 测试和 execution state 作为启动上下文，同时把 provider gate 默认关闭、do-not-touch 目录、未提交波次成果和全量测试阻塞项写入明确约束。

## Branch / Head / Status

- AFS repo: `D:\Projects\AgentFlowStudio`
- Branch: `master`
- HEAD: `ed292f6b752c9150e9a4b9a85fccdcfef5135b14`
- Tracking: `master...origin/master`
- Local/origin code baseline: HEAD 与 `origin/master` 同步。
- Local wave state: 第一、第二、第三、第四波成果仍未提交。
- GitHub sync: not performed.
- Server sync: not performed.
- Runtime health: not checked.
- Provider gates: not opened.

## Dirty Ownership Ledger

| 分类 | 路径 / 表面 | 归属判断 |
|---|---|---|
| 第一/二/三/四波记录 | `DEVLOG.md` | 继续保留，本轮追加 readiness gate 记录。 |
| 第一/二/三/四波索引 | `docs/handoff/INDEX.md` | 继续保留，本轮追加第四波入口。 |
| 第二波成果 | `docs/openapi/afs-runtime-service.openapi.json` | 第二波 OpenAPI snapshot 重新生成成果；当前 49 paths，不含 `image-assets*`。 |
| 第三波成果 | `tests/test_api_runtime_studio_state_persistence.py` | 只修正结构化错误 payload 断言。 |
| 第一波成果 | `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md` | 保留。 |
| 第二波成果 | `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md` | 保留。 |
| 第三波成果 | `docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md` | 保留。 |
| 第四波成果 | `docs/handoff/AFS-GOAL-MODE-READINESS-GATE-20260630.md` | 本文。 |
| 第二波测试 | `tests/test_api_runtime_openapi_snapshot.py` | 保留，防 OpenAPI snapshot 漂移。 |
| 第三波测试 | `tests/test_api_runtime_media_contract.py` | 保留，固定 Studio-facing private media contract。 |
| 既有未跟踪 | `docs/demo-docs-20260629/` | do-not-touch；本轮不清理、不提交。 |
| source-KB 最小状态 | `AFS-Goal-Driven-Execution-State-v0.1.yaml` | 仅记录第四波 gate 结论和 next valid action。 |
| source-KB 既有脏状态 | `.obsidian`、Week Planner、CompanyOS/COS 其它改动 | do-not-touch；本轮不 stage、不清理、不晋升。 |

## First / Second / Third Wave Baseline Summary

第一波 `AFS-T0 Startup Scan`：

- 建立真实 startup scan、dirty ownership ledger、项目入口和非目标边界。
- 明确 `docs/demo-docs-20260629/` 与 Learning_notes 既有脏状态为 do-not-touch。
- 证据等级：`structure_verified`，不声明 runtime health、provider smoke、human acceptance 或 business validation。

第二波 `AFS-T2 Runtime Contract`：

- 发现并修复 OpenAPI snapshot 漂移：默认 Runtime exporter 为 49 paths，旧 snapshot 为 34 paths。
- 重新生成 `docs/openapi/afs-runtime-service.openapi.json`。
- 新增 `tests/test_api_runtime_openapi_snapshot.py`，防止 committed snapshot 再次漂移。
- 审计 Studio fetch 边界，未发现绕过 Runtime 直接接触 CLI/provider 的前端路径。

第三波 `AFS-T2b Runtime Media Contract`：

- 将 `image-assets*` 判定为 Studio-facing private Runtime media contract。
- 决定本阶段不纳入 public OpenAPI：上传含 `data_base64`，preview route 返回媒体字节，公开前需要专门 media API slice。
- 新增 `tests/test_api_runtime_media_contract.py`，覆盖 OpenAPI 排除、安全 JSON、preview content-type/no-store、无 base64/本地路径/signed URL 回显。
- 修正一个 Studio-state unsafe preview URL 测试断言，使其匹配当前结构化 Runtime error payload。

## Read Scope

- `project-development-workflow` skill and startup/verification/memory references
- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md`
- `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md`
- `docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_api_runtime_openapi_snapshot.py`
- `tests/test_api_runtime_media_contract.py`
- `tests/test_api_runtime_studio_state_persistence.py`
- `pyproject.toml`
- `apps/api/runtime_service.py`
- `apps/api/runtime_image_assets.py`
- Studio runtime client, media preview, asset sync, upload, and persistence files
- `AFS-Goal-Driven-Execution-State-v0.1.yaml`

## Verification

```text
git status --short --branch
# ## master...origin/master
# M DEVLOG.md
# M docs/handoff/INDEX.md
# M docs/openapi/afs-runtime-service.openapi.json
# M tests/test_api_runtime_studio_state_persistence.py
# ?? docs/demo-docs-20260629/
# ?? docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md
# ?? docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md
# ?? docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md
# ?? tests/test_api_runtime_media_contract.py
# ?? tests/test_api_runtime_openapi_snapshot.py

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed; CLI help rendered

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe -m pytest
# failed: 686 passed, 4 failed, 520 deselected, 2 warnings
```

Full pytest failures:

| Test | Classification | Gate impact |
|---|---|---|
| `tests/test_api_runtime_llm_enhancement_modules.py::test_llm_enhancement_keeps_runtime_helpers_split` | Existing static threshold debt. `apps/api/runtime_llm_enhancement.py` is 446 lines while the test hard-codes `<=300`. | Blocks clean baseline freeze. Do not fix by hiding the threshold; either split with a focused plan or change the test to express the real module contract plus maintenance-audit warning policy. |
| `tests/test_api_runtime_video_routes_modules.py::test_video_routes_keep_runtime_helpers_split` | Existing static threshold debt. `apps/api/runtime_video_routes.py` is 397 lines while the test hard-codes `<=300`. | Blocks clean baseline freeze. Same remedy: focused route split or calibrated maintainability contract. |
| `tests/test_api_runtime_service.py::test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text` | Stale test assertion. Runtime now returns structured safe error detail with non-secret metadata, while the test expects a minimal two-field dict. | Should be fixed in a test-contract calibration slice. |
| `tests/test_api_runtime_studio_state.py::test_studio_state_uses_expected_version_to_prevent_stale_overwrite` | Stale test assertion. Runtime now returns structured `studio_state_conflict` detail with `raw_detail`, while the test expects substring membership on a string detail. | Should be fixed in a test-contract calibration slice. |

Additional verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; status=warning; passed=3; warning=4
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9, high_confidence_count=0
# oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id before this update was AFS-T2b; evidence_state=structure_verified
```

## Unresolved Warnings / Blockers

Blocking for clean full-goal baseline:

- Full `pytest` is red with 4 failures.
- Two failures are stale structured-error test assertions.
- Two failures are hard static line-count thresholds. The line-count checks are stricter than the repository's current maintenance-audit policy and should be handled as a dedicated test-maintenance slice, not patched opportunistically inside this gate.

Non-blocking but must remain visible:

- `maintenance_audit` has `failed=0`, but warning classes remain: oversized files, Chinese coverage debt, secret-like false-positive/low-confidence fragments, and legacy frozen surface.
- `docs/demo-docs-20260629/` remains untracked and intentionally untouched.
- First/second/third/fourth wave成果 have not been committed or pushed.
- GitHub/server/runtime health/human acceptance/business validation were not checked in this TaskRun.

## Readiness Judgment

Judgment: `not ready` for unbounded full Codex goal mode.

Reason:

- The first three waves form a coherent, explainable, test-backed local baseline at the focused-contract level.
- The dirty worktree is explainable and attributable.
- However, the required full `pytest` gate is red. A long-running unattended development mode should not start from a red full-test baseline unless the user explicitly accepts that failure ledger as the baseline, which is not recommended here.

Allowed next state:

- Ready for a bounded follow-up task: `AFS-T3a Test Contract Calibration + Baseline Freeze Prep`.
- Not ready for broad feature development, provider integration, or server deployment.

## Commit / Push Recommendation

Do not commit or push in this TaskRun.

Recommended sequence before commit/push:

1. Run `AFS-T3a Test Contract Calibration + Baseline Freeze Prep`.
2. Fix or intentionally reframe the 4 full-pytest blockers:
   - update stale structured-error tests to assert safe structured payloads;
   - handle hard line-count tests by either focused route splitting or replacing brittle numeric thresholds with a maintainability contract that matches `maintenance_audit`.
3. Rerun full verification: CLI help/version, full pytest, Studio JS check, maintenance audit, diff check, YAML parse if state changes.
4. Then commit in clear groups:
   - contract/test baseline: OpenAPI snapshot, OpenAPI parity test, media contract test, structured-error test calibration;
   - records/handoff: DEVLOG, handoff index, first/second/third/fourth wave packets.
5. Push only after local full verification is green or the user explicitly accepts a documented red-test baseline.

## Server Sync Recommendation

Do not server-sync or deploy in this TaskRun.

Recommended server sequence after a clean local commit/push:

1. Confirm local `master` and `origin/master` at the same commit.
2. Fast-forward server `/home/afs-ops/AgentFlowStudio`.
3. Fast-forward server `/opt/afs/AgentFlowStudio`.
4. Restart or allow restart of `afs-runtime.service` only after the server checkout is aligned.
5. Check Runtime `/health` and record provider gates separately.

Server sync is not a substitute for local verification, and Runtime health is not human acceptance.

## Full Goal Mode Entry Conditions

Full goal mode should start only when all of these are true:

- Dirty ownership ledger is cleanly frozen: either committed or explicitly accepted as the baseline.
- Full pytest is green, or a human-approved red-test exception is recorded with exact failing tests and allowed scope.
- `npm.cmd run check:studio-js` is green.
- `tools\maintenance_audit.py` has `failed=0`, and warning classes are classified.
- OpenAPI snapshot parity test is green.
- Runtime media contract test is green.
- Provider gates remain closed unless the task explicitly authorizes a capability.
- No secrets, provider raw response, signed URL, local private media bytes, customer material, real cost, or invite plaintext are written into repo records.
- GitHub/server/runtime health/human acceptance/business validation remain separate evidence states.

Baseline files for the next full-goal prompt:

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md`
- `docs/handoff/AFS-RUNTIME-CONTRACT-TASKRUN-20260630.md`
- `docs/handoff/AFS-RUNTIME-MEDIA-CONTRACT-TASKRUN-20260630.md`
- `docs/handoff/AFS-GOAL-MODE-READINESS-GATE-20260630.md`
- `docs/openapi/afs-runtime-service.openapi.json`
- `tests/test_api_runtime_openapi_snapshot.py`
- `tests/test_api_runtime_media_contract.py`
- `AFS-Goal-Driven-Execution-State-v0.1.yaml`

## Evidence State

Evidence state: `structure_verified_with_full_pytest_blockers`.

Non-claims:

- Not server sync.
- Not Runtime health verification.
- Not provider smoke.
- Not human acceptance.
- Not business validation.
- Not durable memory promotion.

## Cleanup Review

- Keep: first/second/third/fourth wave handoff packets.
- Keep: OpenAPI snapshot parity test.
- Keep: Runtime private media contract test.
- Keep: structured unsafe-preview test update from third wave.
- Defer: `docs/demo-docs-20260629/`.
- Defer: Learning_notes unrelated dirty state.
- Defer: public OpenAPI promotion of `image-assets*`.
- Block: full goal mode until full pytest blockers are handled or explicitly accepted.

## Next Valid Task

Recommended next task: `AFS-T3a Test Contract Calibration + Baseline Freeze Prep`.

Goal for T3a:

- Resolve the 4 full-pytest blockers without changing product behavior.
- Rerun full verification.
- Produce a commit/push/sync-ready baseline decision.

Do not start broad unattended development from the current red full-test state.
