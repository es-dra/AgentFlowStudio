# AFS runs/ 证据保留规则

中文摘要：本规则只定义 `runs/` 与 evidence 目录的保留策略；本切片不执行批量删除。

## 保留规则

- canonical 报告目录永久保留，除非后续 handoff 明确声明被新报告取代。
- `runs/` 下非 canonical evidence 目录满 30 天后可进入清理候选。
- exact duplicate media 只有在 sha、manifest、场景归属都明确时才允许删除。
- provider raw response、本地私有素材、本地 provider config、模型权重不得移动进 tracked 文件。
- 大批 live smoke 或 A/B/C 前，先确认本规则仍适用，避免 evidence 目录无边界增长。

## 日常测试命令

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not slow"
```

合并或发布前仍需跑全量 pytest、Studio JS `node --check`、`tools/maintenance_audit.py` 和 `git diff --check`。

## 非声明边界

本规则只是维护策略，不代表 provider smoke、人工验收或业务验证。删除 evidence 前必须能从 handoff 或 manifest 证明该证据不是唯一可复核材料。
