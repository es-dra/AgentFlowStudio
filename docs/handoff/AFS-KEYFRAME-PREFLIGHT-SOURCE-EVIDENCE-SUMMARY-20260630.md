# AFS-T26 Keyframe Preflight Source Evidence Summary

## 任务信息

- Task ID: `AFS-T26`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `e50130175c93a5c24836ac7d8399667dfcb46c0f`
- 模式: provider-closed full goal-mode product slice
- 状态: 本地收口验证待提交和推送

本轮目标是把已经进入 keyframe context 的固定资产来源证据，提升为
generation preflight 响应里的安全摘要。这样 Studio 或后续审查界面不需要
遍历完整 `included_assets`，也能直接看到本次 keyframe preflight 携带的
固定资产来自哪个 human gate 和哪个 asset-card candidate。

## Dirty Ownership Ledger

本轮拥有:

- `apps/api/runtime_generation_preflight.py`
- `tests/test_api_runtime_fixed_asset_source_evidence_context.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-KEYFRAME-PREFLIGHT-SOURCE-EVIDENCE-SUMMARY-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Generation preflight 响应新增两个顶层安全字段:

- `included_asset_source_evidence_count`
- `included_asset_source_evidence_refs`

每个 ref 只包含公开、安全、可审查字段:

- `asset_id`
- `asset_type`
- `label`
- `status`
- `source_contract`
- `source_human_gate_id`
- `source_asset_card_candidate_id`
- `source_stage`
- `result_asset_status`
- provider call、generated media、human creative acceptance、business
  validation 的非声明布尔字段

完整的 `included_assets[*].source_evidence` 仍然保留。新增顶层摘要只是让
preflight review surface 更容易消费来源证据，不新增 route，不改变 request
schema，也不扩大 OpenAPI path。

Preflight token digest 现在包含 included asset 的来源证据标识。这样同一个
review token 不只绑定资产 id，也绑定本次 preflight 审查过的来源证据。

## 本轮改动

- 在 `runtime_generation_preflight.py` 中新增
  `_included_asset_source_evidence_refs()` 和 `_source_evidence_digest()`。
- 在共享 generation preflight 响应里增加来源证据 count 和 refs。
- 扩展固定资产来源证据 context 回归测试，覆盖摘要字段、重复 preflight
  token 确定性，以及 `data_base64`、`signed_url`、本地绝对路径等 unsafe
  marker 不外露。

## 非目标和边界

- 不新增 Runtime route。
- 不新增 request 字段。
- 不扩展 OpenAPI path。
- 不改 Studio UI。
- 不打开 provider gate。
- 不调用 live provider。
- 不写入生成媒体或私有媒体字节。
- 不写入 provider raw response、signed URL、本地绝对路径、token 或 secret。
- 不做 deploy、server sync 或 Runtime health check。
- 不声明 human creative acceptance 或 business validation。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_fixed_asset_source_evidence_context.py tests\test_api_runtime_context_resolver.py -q
# 19 passed, 1 existing warning
```

Closeout verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T26

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增重复 sanitizer。
- 没有新增一次性工具。
- 新 helper 保持在现有 preflight 模块内，只负责来源证据摘要。
- 触达代码和测试文件均低于项目 300 行 warning 阈值。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

下一切片应把 keyframe preflight 的 source-evidence refs 展示到 Studio 审查
界面，或把 production graph 的 fixed-asset reuse evidence 连接到具体 Studio
inspection surface。分支达到 20 commits、80 changed files 或 5000 insertions
任一阈值时，必须停止新增功能并进入 merge review gate。
