# AFS Legacy Freeze 维护账本

日期：2026-06-13  
分支：`codex/afs-hygiene-cleanup-20260613`  
基线：`6c2cccf refactor(runtime): retire production memory HTTP routes`  
冻结 tag：`legacy-frozen-20260613`

## 目标

让 `master` 进入低维护、无冗余、无错误信息的状态，为后续多方位浏览器测试清场。本轮只做仓库卫生清理，不新增产品能力，不打开 provider gate，不改 Runtime/OpenAPI 字段。

## 决策

- Production Memory 与分发链遗产面原地冻结，不删除、不移动，保留为未来重写参考。
- 默认 `pytest` 只作为当前 Runtime/Studio/契约门禁；冻结遗产测试改为 `pytest -m legacy` 单独运行，不作为合并门禁。
- 维护审计仍全仓扫描 secret、Company 源路径和 tracked runtime artifact；oversized 与中文覆盖只针对 active 面，冻结目录单列为 `legacy_frozen_surface` warning。
- 旧 `NARRATOCUT_ALLOW_REMOTE_*` provider gate 兼容全量退役；当前配置只接受 `AFS_ALLOW_REMOTE_*`。
- `ComplianceResult` 仅剩 schema package re-export 与 roundtrip 测试引用，已作为孤儿 schema 删除。
- `docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md` 指向已退役 Runtime 路由，已删除；历史 maintenance/DEVLOG 记录保留。
- 根目录未跟踪的 `AFS-CLEANUP-INSTRUCTIONS-*` 与 `AFS-PROJECT-HEALTH-REVIEW-*` 是本地输入资料，不纳入提交；repository retention review 将其归类为 `local_workspace_input`，不计为仓库 retention 人工复审项。

## 冻结范围

- `agentflow/memory/`
- `apps/cli/production_memory_*`
- `agentflow_studio/asr_sop/`
- `agentflow_studio/audio_sop/`
- `agentflow_studio/candidate_sop/`
- `agentflow_studio/highlight_sop/`
- `agentflow_studio/ocr_sop/`
- `agentflow_studio/production/`
- `agentflow_studio/slicing_sop/`
- `agentflow_studio/workflow_engine/`
- 对应 production-memory 与分发链测试，按显式文件名/前缀标记为 `legacy`。

## 已完成切片

- 切片 0：新增 `.gitattributes`，执行 `git add --renormalize .`；实际只有 `.gitattributes` 与 retention policy/test 分类变更，没有全仓内容噪声。
- 切片 1：新增 `legacy` pytest marker、`tests/conftest.py` 收集钩子、legacy 标记保护测试；维护审计新增 `legacy_frozen_surface` 分类。
- 切片 2：删除过期 v0.2 Runtime handoff；更新 local internal test runbook 为 legacy CLI-only；退役 `NARRATOCUT_ALLOW_REMOTE_*`；删除孤儿 `ComplianceResult`。

## 验证记录

```text
tag push legacy-frozen-20260613: passed
slice 0 repository retention focused test: 3 passed
slice 0 full pytest before test downgrade: 886 passed, 2 warnings
pytest --collect-only -q: 362/889 collected, 527 deselected
pytest -m legacy --collect-only -q: 527/889 collected, forbidden current-gate hits=0
legacy marker + maintenance audit focused tests: 12 passed
default pytest after legacy marker: 362 passed, 527 deselected, 2 warnings
pytest -m legacy after legacy marker: 527 passed, 362 deselected, 1 warning
slice 2 focused provider/schema/runtime/static tests: 66 passed, 1 warning
slice 2 default pytest: 363 passed, 527 deselected, 2 warnings
slice 2 legacy pytest: 527 passed, 363 deselected, 1 warning
maintenance_audit: failed=0, passed=4, warning=3
git diff --check: exit 0, Windows LF conversion notices only
merged master default pytest initial rerun: blocked by untracked local input files
local input classification regression test: 4 passed
```

## 非声明

- 本轮没有 provider call。
- 本轮不写 durable memory。
- 本轮不写公司源头知识库。
- 本轮不是 human acceptance 或 business validation。

## 后续

- 更大范围的 `docs/handoff/` 与 `docs/maintenance/` 历史账本瘦身放到浏览器 QA 后的独立文档清理切片。
- 真正删除或重写 Production Memory / 分发链遗产代码，需要另开独立迁移切片，并以 `legacy-frozen-20260613` tag 作为回退参考。
