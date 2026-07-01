# AFS 测试维护审计账本 - 2026-06-29

## 范围

本轮只处理测试维护和维护审计可解释性，不新增产品功能，不触发 live
provider，不改 Runtime provider gate。

写入范围：

- `tools/maintenance_audit.py`
- `tools/maintenance_audit_secret_scan.py`
- `tests/test_maintenance_audit.py`
- 本维护账本
- `DEVLOG.md`

保护范围：

- 主工作树未跟踪 `docs/demo-docs-20260629/` 不纳入本轮提交。
- 服务器 `/home/afs-ops/AgentFlowStudio` 的未跟踪 demo/ops-local 文件不删除。
- 服务器 `/opt/afs/AgentFlowStudio` 是 Runtime 当前运行目录，部署前只做 fast-forward 同步。
- 不读取、输出或提交 provider secret、token、signed URL、raw provider response、生成媒体字节或邀请码明文。

## 初始状态

- 本地 `master` 与 `origin/master` 对齐在 `9125e0b5c1dfa87c766f7224ccf42b0b09dbe3da`。
- 当前实现分支：`codex/test-maintenance-audit-20260629`。
- 实现 worktree：
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\test-maintenance-audit-20260629`。
- 主工作树有未跟踪 `docs/demo-docs-20260629/`，本轮不触碰。

## 远端支线检查

`origin/zhaowei` 相对 `origin/master` 有 11 个未合并提交，主题包括 script
expansion、optimizer pollution guard、asset-card image handoff、image relay
和 Crazyrouter artifact host。

隔离 worktree 内 `git merge --no-commit --no-ff origin/zhaowei` 试合并结果：

- 产生 9 个核心文件冲突，包括 Runtime keyframe、LLM enhancement、prompt memory
  和 Studio script breakdown。
- 三点 diff 涉及 35 个文件、约 2000 行新增。
- 当前主线已经有 image relay、Crazyrouter `.myqcloud.com` artifact host、
  `AFS_CODEX_HOME` worker runtime home、script expansion 和 optimizer 污染防护的
  等价或更新实现记录。

结论：不整包合并 `origin/zhaowei`。本轮完成后若验证主线稳定，应清理该远端
冗余分支，避免再次成为三端同步噪声。

## Warning 分类原则

维护审计 warning 不直接等价于代码债务。本轮把 warning 拆成：

- `tracked`：进入 Git 事实的活跃维护债。
- `untracked`：当前工作区或服务器本地临时材料，先做 ownership 记录，不直接提交或删除。
- `ignored`：运行证据、runtime data、生成输出；仍可参与 secret scan，但不应污染 oversized/chinese 活跃维护指标。
- `legacy_frozen`：已冻结 legacy surface，保留边界记录，不在本轮拆分。
- `secret_like`：优先区分 high-confidence 与字段名/fixture/检测逻辑误报。

## 验证计划

- `.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_audit.py -q`
- `.\.venv\Scripts\python.exe tools\maintenance_audit.py`
- `npm.cmd run check:studio-js`
- `.\.venv\Scripts\python.exe -m apps.cli.main --help`
- `.\.venv\Scripts\python.exe -m apps.cli.main version`
- `git diff --check`

如提交推送，再分别核验本地、GitHub、服务器 `/home`、服务器 `/opt` 和
Runtime `/health`。

## 实施结果

- `agentflow_maintenance_audit_report` 现在输出 `workspace_files`，统计
  tracked、untracked、ignored、unknown text files。
- `legacy_company_path`、`human_doc_chinese_coverage`、`secret_like_fragments`
  和 `oversized_files` 的 file-level finding 现在带 `git_state`。
- `oversized_files` 和 `human_doc_chinese_coverage` 排除 ignored 文件，避免
  `runs/`、runtime evidence、生成报告把活跃维护债务放大。
- `secret_like_fragments` 继续扫描 ignored 文件，避免因为排除运行目录而漏掉
  secret-like 片段。
- Git 状态探测拆到 `tools/maintenance_audit_git.py`，主审计入口保持 299 行，
  没有新增 oversized 工具文件。

## 当前审计口径

本轮隔离 worktree 的实际审计结果：

- `failed=0`
- `legacy_frozen_surface=10`
- `human_doc_chinese_coverage=22`，`source_summary.tracked=22`
- `secret_like_fragments=9`，`high_confidence_count=0`
- `oversized_files=57`，`source_summary.tracked=57`
- `workspace_files.tracked_text_files=1105`
- `workspace_files.untracked_text_files=2`，均为本轮新增文件，提交后应归零
- `workspace_files.ignored_text_files=0`，隔离 worktree 没有 ignored runtime evidence

这说明本轮没有清零维护债，而是把活跃 tracked 债与本地/运行证据噪声分开。

## 已运行验证

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_maintenance_audit.py -q
# 11 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0, warnings only

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

`git diff --check` 和三端同步核验将在提交前后分别执行。
