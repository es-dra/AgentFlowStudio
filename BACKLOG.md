# Backlog

中文摘要：本文件只保留当前仍能推动 Studio MVP、真实 provider 接入或维护降本的
后续事项。历史想法、旧 Web/Workbench 任务、无测试支撑的概念记录不再进入
backlog；如果某项任务已经不能服务当前主线，应直接删除，而不是长期挂起。

| # | 事项 | 来源 | 优先级 | 建议时机 | 记录时间 | 说明 |
|---|---|---|---|---|---|---|
| 1 | 拆分 oversized Runtime/Studio 文件 | `tools/maintenance_audit.py` oversized warning | P1 | 下一轮维护切片 | 2026-06-12 by Codex | 当前 warning 覆盖 `runtime_context_resolver.py`、`runtime_director_compiler.py`、`runtime_keyframes.py`、`runtime_service.py`、`director-shell.js` 和两个大型测试文件。不要在 provider 接入切片里顺手强拆，避免扩大风险。 |
| 2 | 实现 Kling video adapter v0.2 | Provider Gateway v0.1 非目标 | P1 | keyframe 可控性证据稳定后 | 2026-06-12 by Codex | v0.1 已用 fake video 表达 async 生命周期，但 Kling 的 submit/poll/normalize、任务状态恢复和 video gate 需要独立切片。 |
| 3 | 清理 ACL 阻塞的 pytest basetemp 缓存 | AFS-PROJECT-INVENTORY-001 cleanup manifest | P1 | 下一次管理员 shell 或所有权修复窗口 | 2026-06-12 by Codex | `data/processed/pytest-basetemp` 是 ignored 测试缓存，但当前用户无法完全删除历史 ACL-denied 目录。这不是 repo 代码问题，需要目录所有者或管理员 shell 清理。 |
| 4 | 制定媒体/evidence 保留规则 | AFS-PROJECT-INVENTORY-001 inventory report | P1 | provider gateway v0.2 或大批 live smoke 前 | 2026-06-12 by Codex | 深度本地盘点发现 80 组 exact duplicate media/evidence，理论可回收约 827MB。只有在 canonical run/manifest 保留规则确定后才能删除。 |
| 5 | 退役 Production Memory legacy core/tests | AFS-PROJECT-INVENTORY-001 direct cleanup | P1 | fixed visual_asset / resolver MVP 验收后 | 2026-06-12 by Codex | 旧 asset handoff 和短 CLI alias 已删除，但 `agentflow/memory` 与 `tests/test_production_memory_*` 仍有真实 contract 覆盖。后续应作为单独迁移，不作为 incidental cleanup。 |
| 6 | 退役 legacy `ModelGateway` LLM config 路径 | AFS-PROVIDER-GATEWAY-V0-1 | P1 | registry-backed live LLM smoke 通过后 | 2026-06-12 by Codex | Runtime prompt enhancement 已改走 `ProviderRegistry.dispatch(...)`，但 `configs/models.example.yaml`、`configs/models.yaml` 和 `tests/test_model_gateway.py` 仍保留旧 OpenAI-compatible gateway contract。真实 registry LLM smoke 验证后再决定保留 shim 还是删除旧配置路径。 |
| 7 | Generate and adopt lock file | AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613 | P1 | Next dependency-maintenance slice | 2026-06-13 by Codex | Core dependency upper bounds were added in `pyproject.toml`; lock generation is intentionally deferred to avoid mixing resolver churn into the Runtime route-removal diff. |
| 8 | Add `.gitattributes` and run CRLF renormalization | AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613 | P1 | Standalone repository hygiene slice | 2026-06-13 by Codex | `git diff --check` can report Windows CRLF notices in existing files. Normalize line endings separately so behavior diffs stay reviewable. |
| 9 | Add provider gate isolation tests | `AGENTS.md` provider-gate contract | P1 | Before the next provider-gated vertical expands | 2026-06-13 by Codex | Assert that enabling image provider access does not implicitly enable video, LLM, ASR, external download, or unrelated provider surfaces. |
| 10 | Harden or retire legacy v02 error projection | AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613 residual risk | P1 | Legacy v02 retirement/hardening slice | 2026-06-13 by Codex | Current default Runtime routes use safe error details; `runtime_v02.py` still has `detail=str(exc)` and remains legacy-only behind `AFS_ENABLE_LEGACY_RUNTIME_V02=true`. |
