# AFS-T24 Fixed Asset Source Evidence Context

## 任务信息

- Task ID: `AFS-T24`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点: `e7671002af2d82ad648be45a8e3f9832b572f5da`
- 模式: provider-closed full goal-mode product slice
- 目标: 把 fixed visual asset 的来源证据整理成安全 public projection，并让它进入 keyframe context，形成 `asset candidate -> human gate -> fixed asset -> context` 的可追踪链路。

## Dirty Ownership Ledger

本轮拥有:

- `agentflow/algorithms/fixed_asset_memory/__init__.py`
- `agentflow/algorithms/fixed_asset_memory/promotion_gate.py`
- `tests/test_api_runtime_visual_asset_promotion_gate.py`
- `tests/test_api_runtime_fixed_asset_source_evidence_context.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FIXED-ASSET-SOURCE-EVIDENCE-CONTEXT-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

`public_visual_asset(record)` 现在会从既有 `promotion_gate` 派生 `source_evidence`:

- `artifact_type=agentflow_fixed_visual_asset_source_evidence`
- `source_contract`
- `source_human_gate_id`
- `source_asset_card_candidate_id`
- `source_stage`
- `result_asset_status`
- `provider_calls_started=false`
- `generated_media_claimed=false`
- `human_creative_acceptance_claimed=false`
- `business_validation_claimed=false`
- `safe_payload=true`

`included_asset()` 继续使用 `public_visual_asset()`，所以 keyframe preflight 的 `included_assets` 会自然携带同一个 safe `source_evidence`。

## 本轮改动

- Added `public_source_evidence()` in `fixed_asset_memory/promotion_gate.py`.
- Exposed `source_evidence` from `public_visual_asset()`.
- Extended Runtime visual asset promotion tests.
- Added a small focused keyframe-context regression test instead of expanding the already-oversized context-resolver test file.

## 非目标和边界

- 不新增 request 字段。
- 不修改 OpenAPI request contract。
- 不调用 live provider。
- 不生成或保存媒体字节。
- 不写 provider raw、本地绝对路径、signed URL、secret。
- 不声明 human creative acceptance 或 business validation。
- 不做 deploy、server sync 或 provider smoke。

## 验证

已完成 focused 验证:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_visual_asset_promotion_gate.py -q
# 2 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 1 passed, 1 existing warning
```

已完成收口验证:

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
# yaml_ok=True; current_task_id=AFS-T24

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 未新增 route、schema fork、provider path、一次性工具或重复 sanitizer。
- 没有继续扩展大型 context resolver 测试文件。
- 新增 source evidence 是从已有 promotion gate 派生，避免在 record 中复制冗余字段。
- `docs/demo-docs-20260629/` 未清理、未归入本轮成果。

## 下一步

下一批最有效切片: 让 production graph 或 Studio workflow 更明确地消费 fixed asset source evidence，或者改进从 script 到 candidates/human gate/promotion 的操作入口。达到 20 commits、80 files 或 5000 insertions 任一阈值时必须停止新增功能并进入 merge review gate。
