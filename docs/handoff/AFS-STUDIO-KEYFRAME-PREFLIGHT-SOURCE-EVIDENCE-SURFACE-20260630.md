# AFS-T27 Studio Keyframe Preflight Source Evidence Surface

## 任务信息

- Task ID: `AFS-T27`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `5a8d306774183ffde1fb680ad28c90630ed06fd7`
- 模式: provider-closed full goal-mode product slice
- 状态: 本地验证待提交和推送

本轮目标是把 T26 Runtime preflight 的来源证据摘要接到 Studio 现有生成前确认
界面。这样操作者在继续 keyframe 或 video 生成前，可以直接看到本次携带的
固定资产来自哪个 human gate 或 asset-card candidate。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/generation-preflight-source-evidence.js`
- `apps/studio/src/node-generation-guards.js`
- `tests/test_web_studio_preflight_source_evidence_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-KEYFRAME-PREFLIGHT-SOURCE-EVIDENCE-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Studio 现在在固定资产 carry confirmation modal 中读取 Runtime preflight 的
`included_asset_source_evidence_refs`，并显示安全摘要:

```text
来源证据：角色 · Lin Wan ← asset_card_candidate:main_character
```

如果 Runtime 还没有顶层 refs，helper 会从 `included_assets[*].source_evidence`
做兼容 fallback。显示字段只来自 Runtime safe projection，不读取 provider raw、
本地路径、signed URL、媒体字节或 secret。

## 本轮改动

- 新增 `generation-preflight-source-evidence.js`，只负责把 preflight 来源证据
  转成一行可读摘要。
- `node-generation-guards.js` 在固定资产携带确认 modal 中显示该摘要。
- 复用 `asset-reference-summary.js` 的 `assetLabel()` 和 `assetTypeLabel()`，
  删除 `node-generation-guards.js` 内部重复的 `assetTypeLabel()`。
- 新增小型 static regression，避免继续增大已有 oversized Studio static test。

## 非目标和边界

- 不新增 Runtime route。
- 不新增 request 字段。
- 不扩展 OpenAPI path。
- 不新增 fetch 或 Runtime client 调用。
- 不打开 provider gate。
- 不调用 live provider。
- 不写入生成媒体或私有媒体字节。
- 不写入 provider raw response、signed URL、本地绝对路径、token 或 secret。
- 不做 deploy、server sync 或 Runtime health check。
- 不声明 human creative acceptance 或 business validation。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_preflight_source_evidence_static.py -q
# 1 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_preflight_source_evidence_static.py tests\test_web_studio_assets_generation_static.py::test_loop003_qal003_001_fixed_asset_submit_interlock_has_regression_markers tests\test_web_studio_assets_generation_static.py::test_asset_card_generation_uses_optional_fixed_asset_carry_policy -q
# 3 passed
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
# yaml_ok=True; current_task_id=AFS-T27

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增重复 sanitizer。
- 没有新增一次性工具。
- 新 helper 是纯展示 helper，不做网络调用、不写状态。
- `node-generation-guards.js` 从 322 行降到 320 行，仍是既有 oversized
  warning，但本轮没有扩大该债务。
- 新测试文件 22 行，避免增大已有大型 static test。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

下一切片应继续把 fixed asset reuse evidence 连接到可操作闭环，例如在 Studio
的 production graph / storyboard inspection surface 中展示 fixed asset reuse
关系，或补一条从 storyboard candidate 到 human gate 到 promotion 的更直接入口。
分支达到 20 commits、80 changed files 或 5000 insertions 任一阈值时，必须
停止新增功能并进入 merge review gate。
