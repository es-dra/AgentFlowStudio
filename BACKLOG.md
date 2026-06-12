# Backlog

| # | 待办项 | 来源 | 优先级 | 建议时机 | 记录时间 | 说明 |
|---|---|---|---|---|---|---|
| 1 | 拆分 oversized Runtime/Studio 文件 | `tools/maintenance_audit.py` oversized warning | P1 | 下一轮维护清理 | 2026-06-12 by Codex | 当前 warning 覆盖 `runtime_context_resolver.py`、`runtime_director_compiler.py`、`runtime_keyframes.py`、`runtime_service.py`、`director-shell.js` 和两个大测试文件；本轮不扩大 scope 强拆。 |
| 2 | 实现 Kling video adapter v0.2 | Provider Adapter v0.1 非目标 | P1 | keyframe controllability 证据稳定后 | 2026-06-12 by Codex | v0.1 已能表达 async 生命周期，但只标准化 MiniMax image；Kling submit/poll 收编应单独做。 |
