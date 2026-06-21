# AFS 分支合并与支线清理账本

日期：2026-06-22
状态：已完成
范围：`codex/studio-prompt-script-image-diagnostics` 合入 `master`、三端同步、支线清理。

## 背景

当前服务器 `/home/afs-ops/AgentFlowStudio` 与 `/opt/afs/AgentFlowStudio` 已运行
`codex/studio-prompt-script-image-diagnostics` 的 `765ed79`，但 `master` 仍停在
`b1c0031`。本地工作树另有分镜资产卡与关键帧层改动，已完成本地验证但尚未提交。

本次目标是恢复 GitHub `master`、本地、服务器 `/home`、服务器 `/opt` 四处代码状态一致，
并清理已经吸收或已摘取价值的旧支线。

## 写入范围

- 提交当前分镜资产卡与关键帧层改动。
- 摘取旧内测验收支线中仍有价值的操作索引文档。
- 将当前功能分支合入 `master` 并推送。
- 同步服务器 `/home` 与 `/opt` 到 `master`。
- 删除已吸收或已摘取的旧分支。

## 非目标

- 不打开新的 provider gate。
- 不触发 video provider。
- 不提交 secret、provider 配置、本地素材、raw provider response、signed URL 或媒体字节。
- 不把工程验证声明为 human acceptance、provider smoke、business validation 或 durable memory。

## 分支决策

| 分支 | 决策 | 理由 |
|---|---|---|
| `codex/studio-prompt-script-image-diagnostics` | 合入 `master` 后删除 | 服务器实际运行该分支，且其中提示词、worker、文本节点和资产链路改动属于当前 MVP 主线。 |
| `codex/studio-edge-disconnect-20260619` | 删除 | 核心 edge disconnect 文件已经在当前主线存在，内容等价吸收。 |
| `codex/internal-beta-acceptance-runbook-20260619` | 摘取文档后删除 | 旧分支基线过旧，不能直接合并；其中内测验收操作索引仍有复用价值。 |

## 验证路线

合并前：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run check:studio-js
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
git diff --check
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

合并后：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run check:studio-js
.\.venv\Scripts\python.exe tools\afs_three_end_status.py --server afs-bwg-ops
```

服务器同步后：

```powershell
.\.venv\Scripts\python.exe tools\afs_three_end_status.py --server afs-bwg-ops
```

## 当前风险

- `DEVLOG.md` 与 `TASK_TRACKER.md` 已经超大，仍作为短期记录入口；后续需要归档拆分。
- 历史 handoff/maintenance 文档仍有 MiniMax 旧记录，运行时不有害，但容易误导后续线程。
- 服务器曾经在功能分支运行，合并后必须确认服务工作目录和 branch 都回到 `master`。

## 最终结果

- `master` 已合入并推送到 `origin/master`，最终提交为 `5b9d88a`。
- 本地、GitHub、服务器 `/home/afs-ops/AgentFlowStudio`、服务器 `/opt/afs/AgentFlowStudio`
  均回到 `master`，并对齐到 `5b9d88a`。
- 服务器 `afs-runtime` 与 `afs-codex-image-worker` 已重启；Runtime health 返回 `ready`。
- `codex/studio-prompt-script-image-diagnostics` 已本地和远端删除。
- `codex/internal-beta-acceptance-runbook-20260619` 的操作索引文档与测试已摘取到主线，旧分支已删除。
- `codex/studio-edge-disconnect-20260619` 的边缘断连能力已由主线现有文件和测试覆盖，旧本地分支已删除。

## 最终验证

```powershell
npm run check:studio-js
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
git diff --check
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\studio_full_coverage_browser_qa.py --timeout-ms 30000
.\.venv\Scripts\python.exe tools\afs_three_end_status.py --server afs-bwg-ops --report runs\afs_three_end_status_final_20260622.json
```

结果摘要：

- `pytest`: `588 passed, 520 deselected, 2 warnings`。
- Studio JS syntax check: `107 files` passed。
- CLI help/version passed，版本 `0.1.0`。
- `git diff --check` passed。
- Maintenance audit failed=0，仍有历史文档中文覆盖、secret-like placeholder、oversized files 等既有 warning。
- Browser full coverage QA passed。
- Three-end status `aligned`，三端 dirty count 为 0，Runtime status `ready`。

本次验证没有声明 human acceptance、business validation、provider smoke 或 durable memory promotion。
