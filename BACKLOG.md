# Backlog

| # | 待办项 | 来源 | 优先级 | 建议时机 | 记录时间 | 说明 |
|---|---|---|---|---|---|---|
| 1 | 拆分 oversized Runtime/Studio 文件 | `tools/maintenance_audit.py` oversized warning | P1 | 下一轮维护清理 | 2026-06-12 by Codex | 当前 warning 覆盖 `runtime_context_resolver.py`、`runtime_director_compiler.py`、`runtime_keyframes.py`、`runtime_service.py`、`director-shell.js` 和两个大测试文件；本轮不扩大 scope 强拆。 |
| 2 | 实现 Kling video adapter v0.2 | Provider Adapter v0.1 非目标 | P1 | keyframe controllability 证据稳定后 | 2026-06-12 by Codex | v0.1 已能表达 async 生命周期，但只标准化 MiniMax image；Kling submit/poll 收编应单独做。 |
| 3 | 清理权限异常的 pytest basetemp 缓存目录 | AFS-PROJECT-INVENTORY-001 cleanup manifest | P1 | 下次管理员 shell / 所有权修复窗口 | 2026-06-12 by Codex | `data/processed/pytest-basetemp` 是 ignored 测试缓存；Python、PowerShell、`icacls` 在当前用户下均被部分历史目录拒绝访问。需要拥有该目录所有权的 Windows 用户或管理员 shell 清理，不影响 tracked 代码。 |
| 4 | 制定大型 ignored media/evidence 归档策略 | AFS-PROJECT-INVENTORY-001 inventory report | P1 | provider gateway v0.2 前 | 2026-06-12 by Codex | 本地深度核对发现 80 组 exact duplicate，若每组只保留 1 份 canonical copy，理论可回收约 827MB；其中大量是 acceptance/provider/media evidence，不能在没有 canonical run 规则时随手删。后续应按 run manifest 保留策略决定冷存储、保留最新 N 个 run 或只保留 manifest。 |
| 5 | 退役 Production Memory legacy core/tests | AFS-PROJECT-INVENTORY-001 direct cleanup | P1 | fixed visual_asset / resolver MVP 验收后 | 2026-06-12 by Codex | 本轮已删除旧 asset handoff 并把 production-memory CLI 短别名移出默认产品面；`agentflow/memory` 和 `tests/test_production_memory_*` 仍有大量 contract/test 引用，不能作为零引用死代码直接删。下一刀应以“保留 examples contract 或删除整条 legacy core”为单独迁移，避免继续隐藏在主线。 |
