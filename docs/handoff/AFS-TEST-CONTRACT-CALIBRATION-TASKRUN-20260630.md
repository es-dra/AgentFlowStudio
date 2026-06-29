# AFS 第五波 TaskRun Packet - Test Contract Calibration + Baseline Freeze Prep - 2026-06-30

## Task

Task ID: `AFS-T3a Test Contract Calibration + Baseline Freeze Prep`

本轮目标是在进入长周期 Codex 目标模式前，处理第四波发现的 4 个全量
pytest blocker。任务边界是测试合同校准和基线冻结准备，不是新功能开发、
不做 Runtime/Studio 行为扩展、不打开 provider gate、不提交、不推送、不部署。

任务分类：`Deep` 维护 / QA gate。重点是让测试表达真实产品合同，避免用过硬
静态阈值制造新的维护债。

## 中文门槛结论

本轮已经把第四波记录的 4 个全量 pytest blocker 全部解除。全量测试从
`686 passed, 4 failed, 520 deselected, 2 warnings` 回到
`690 passed, 520 deselected, 2 warnings`。

本轮没有修改 Runtime Service、Studio 前端、OpenAPI snapshot、provider adapter
或生成链路。产品行为没有变化，public API 没有变化，provider gate 没有打开。

关键判断：

- 两个结构化错误失败是 stale test contract。Runtime 当前返回结构化 safe error
  payload，测试应断言 `error/detail_code/status/retryable/request_id/project_id`
  和 unsafe marker 不泄漏，而不是继续期待旧的字符串或两字段小字典。
- 两个模块拆分失败是过硬静态行数阈值。相关 route/helper 已有拆分边界，当前真实
  合同应是：关键 helper 模块存在、route 不重新定义已拆出的 helper、超过 300 行
  的活跃文件必须继续被 `maintenance_audit` 记录为 `oversized_files` warning。
- `runtime_video_dispatch.py` 当前 689 行，仍是明确维护债。本轮不把它伪装成
  已解决，只把它从全量 pytest blocker 退回到维护审计 warning，并记录后续拆分项。

## Branch / Head / Status

- AFS repo: `D:\Projects\AgentFlowStudio`
- Branch: `master`
- HEAD at startup: `ed292f6b752c9150e9a4b9a85fccdcfef5135b14`
- Tracking: `master...origin/master`
- Worktree: single checkout, no extra worktree observed
- GitHub sync: not performed
- Server sync: not performed
- Runtime health: not checked
- Provider gates: not opened
- Commit / push / deploy: not performed

## Dirty Ownership Ledger

| 分类 | 路径 / 表面 | 本轮归属 |
|---|---|---|
| 测试合同校准 | `tests/test_api_runtime_llm_enhancement_modules.py` | 本轮修改。将 300 行硬阈值改为 maintenance-audit warning 合同。 |
| 测试合同校准 | `tests/test_api_runtime_video_routes_modules.py` | 本轮修改。将 route/helper oversized 债务纳入 audit warning 合同。 |
| 测试合同校准 | `tests/test_api_runtime_service.py` | 本轮修改。对齐结构化 safe error payload。 |
| 测试合同校准 | `tests/test_api_runtime_studio_state.py` | 本轮修改。对齐 `studio_state_conflict` 结构化 payload。 |
| 第五波记录 | `docs/handoff/AFS-TEST-CONTRACT-CALIBRATION-TASKRUN-20260630.md` | 本轮新增。 |
| 第五波索引 | `DEVLOG.md`, `docs/handoff/INDEX.md` | 本轮追加记录。 |
| COS execution state | `AFS-Goal-Driven-Execution-State-v0.1.yaml` | 本轮最小更新。 |
| 前序成果 | OpenAPI snapshot、第一/二/三/四波 handoff、media/openapi/persistence tests | 保留，不重写。 |
| do-not-touch | `docs/demo-docs-20260629/` | 未清理、未提交、未触碰。 |
| do-not-touch | Learning_notes `.obsidian`、Week Planner、CompanyOS/COS 无关改动 | 未触碰。 |

## Red Baseline

本轮先复现第四波 4 个失败：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_enhancement_modules.py::test_llm_enhancement_keeps_runtime_helpers_split tests\test_api_runtime_video_routes_modules.py::test_video_routes_keep_runtime_helpers_split tests\test_api_runtime_service.py::test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text tests\test_api_runtime_studio_state.py::test_studio_state_uses_expected_version_to_prevent_stale_overwrite -q
# 4 failed, 1 warning
```

失败分类：

| Test | 分类 | 处理方式 |
|---|---|---|
| `test_llm_enhancement_keeps_runtime_helpers_split` | 过硬静态行数阈值。`runtime_llm_enhancement.py` 446 行；修正后又暴露 `runtime_llm_enhancement_safety.py` 331 行。 | 保留 helper 拆分合同；超过 300 行必须出现在 `maintenance_audit` oversized warning。 |
| `test_video_routes_keep_runtime_helpers_split` | 过硬静态行数阈值。`runtime_video_routes.py` 397 行；修正后又暴露 `runtime_video_dispatch.py` 689 行。 | 保留 route/helper 边界合同；oversized 由维护审计跟踪，`runtime_video_dispatch.py` 进入后续拆分债。 |
| `test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text` | stale structured-error assertion。 | 断言当前结构化 safe error 字段，并继续验证 unsafe marker 不泄漏。 |
| `test_studio_state_uses_expected_version_to_prevent_stale_overwrite` | stale structured-error assertion。 | 断言 `studio_state_conflict`、`state_conflict`、`raw_detail` 和无 unsafe marker。 |

## Repair Method

本轮只改测试合同：

- 对 module split tests：
  - 保留 helper 模块存在性检查。
  - 保留 route 不重新定义已拆出 helper 的检查。
  - 保留 LLM helper 文件无 `\ufffd` 的编码检查。
  - 将 `len(source.splitlines()) <= 300` 改为：
    - 300 行及以下直接通过；
    - 超过 300 行必须出现在 `tools.maintenance_audit.build_maintenance_audit`
      的 `oversized_files` warning 中，且 warning detail 匹配当前行数。
- 对结构化错误 tests：
  - 断言当前 Runtime safe error payload 的稳定字段。
  - 保留 `response_contains_unsafe_marker(...) is False`。

## Behavior / API Change

- Runtime behavior changed: no.
- Studio behavior changed: no.
- OpenAPI changed: no.
- Provider adapter changed: no.
- Public API changed: no.
- Provider call started: no.
- Secret, token, signed URL, provider raw response, local private media bytes written: no.

## Verification

```text
git status --short --branch
# master...origin/master with first/second/third/fourth/fifth wave dirty files;
# docs/demo-docs-20260629/ remains pre-existing untracked do-not-touch.

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_enhancement_modules.py::test_llm_enhancement_keeps_runtime_helpers_split tests\test_api_runtime_video_routes_modules.py::test_video_routes_keep_runtime_helpers_split tests\test_api_runtime_service.py::test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text tests\test_api_runtime_studio_state.py::test_studio_state_uses_expected_version_to_prevent_stale_overwrite -q
# red baseline reproduced: 4 failed, 1 warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_enhancement_modules.py tests\test_api_runtime_video_routes_modules.py tests\test_api_runtime_service.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_media_contract.py -q
# 27 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest
# 690 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files
```

收口验证在记录更新后运行：

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9; high_confidence_count=0
# oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok
```

## Maintenance Audit Classification

本轮没有消除所有 oversized warning，也没有声称消除维护债。校准后的测试合同让
oversized 活跃文件继续进入维护审计，而不是让全量 pytest 被硬编码行数阈值阻断。

当前需要后续处理的明确拆分债：

- `apps/api/runtime_video_dispatch.py`：689 行，超过 500 行，后续应做独立
  video dispatch split slice，优先拆出 provider polling / manifest projection /
  prompt-risk logging 等纯 helper，避免在 T3a 中做高风险行为改动。
- `apps/api/runtime_llm_enhancement.py`：446 行，仍在 301-500 warning 区间。
- `apps/api/runtime_video_routes.py`：397 行，仍在 301-500 warning 区间。
- `apps/api/runtime_llm_enhancement_safety.py`：331 行，仍在 301-500 warning 区间。

## Evidence State

Evidence state after this TaskRun, if final audit/diff/YAML checks pass:

`structure_verified_full_pytest_green_baseline_candidate`

Non-claims:

- Not GitHub sync.
- Not server sync.
- Not Runtime health verification.
- Not provider smoke.
- Not human acceptance.
- Not business validation.
- Not durable memory promotion.

## Commit / Push Recommendation

建议下一轮在确认 final status 后执行 baseline freeze commit/push，而不是在本轮自动执行。

推荐分组：

1. Contract/test baseline:
   OpenAPI snapshot parity test、Runtime media contract test、T3a test contract calibration。
2. Records/handoff:
   DEVLOG、handoff index、第一到第五波 TaskRun packets、execution state note。

提交前必须重新确认 `git status --short --branch`，并明确排除
`docs/demo-docs-20260629/`，除非用户另行授权。

## Server Sync Recommendation

本轮不做服务器同步。建议在 commit/push 后单独执行三端同步任务：

1. 本地 `master` 与 `origin/master` 对齐。
2. 服务器 `/home/afs-ops/AgentFlowStudio` fast-forward 到同一 commit。
3. 服务器 `/opt/afs/AgentFlowStudio` fast-forward 到同一 commit。
4. 如需要，安全重启或等待 `afs-runtime.service` 自动拉起。
5. 检查 `/health`，并单独记录 provider gates。

Runtime health 不能替代 human acceptance。

## Cleanup Review

- Keep: four calibrated tests.
- Keep: this fifth-wave handoff.
- Keep: first/second/third/fourth wave records.
- Keep: OpenAPI snapshot and media contract tests.
- Defer: `runtime_video_dispatch.py` split; it is visible maintenance debt.
- Defer: `docs/demo-docs-20260629/`.
- Defer: Learning_notes unrelated dirty state.
- No cleanup of history-unknown files was performed.

## Next Valid Task

Recommended next task: `AFS-T4 Baseline Freeze Commit/Push + Three-End Sync Prep`.

Only after local final checks are green should the next task commit, push, and
then separately verify GitHub/server/runtime health. Full goal-mode development
can start after that baseline is frozen and synced, with provider gates still
closed unless explicitly authorized.
