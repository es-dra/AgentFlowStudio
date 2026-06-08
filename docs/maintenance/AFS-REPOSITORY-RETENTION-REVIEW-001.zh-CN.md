---
doc_type: repository_retention_review
status: active
last_updated: 2026-06-08
owner_role: Maintainability Steward
branch: codex/afs-maintenance-localization-cleanup-001
confidentiality: internal
---

# AFS 仓库逐目录逐文件保留性审查 001

## 审查目标

本记录用于回答一个具体问题：当前项目里的目录和文件是否仍有保留理由，是否存在可以立即删除的冗余项。

审查范围是 Git 可见的 tracked / untracked 非忽略文件，以及这些文件派生出的目录。不审查 `.git`、`.venv`、缓存目录、被 `.gitignore` 明确排除的 runtime 素材和生成媒体。

## 审查命令

```powershell
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root .
```

第二条命令会输出每一个目录和文件的状态、保留理由、退休条件和非声明边界。

## 本轮结论

当前审查结论：

- `delete_candidate_count = 0`
- `manual_review_required_count = 0`
- `directory_count = 82`
- `file_count = 997`
- `README.zh-CN.md` 已作为冗余中文入口提交删除。
- 历史英文文档已由 `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 提供中文摘要索引，当前不再作为“可立即删除”候选。
- 完整 per-file / per-directory 输出已重新生成到本地临时文件：
  `C:\Users\chenzy\AppData\Local\Temp\afs_repository_retention_review_current.json`

这表示：本轮没有发现仍待处理的“可立即删除冗余文件”。但这不表示仓库已经没有维护债务。

## 目录层分类

| 分类 | 处理 |
|---|---|
| `agentflow/` | 保留。平台 contract、harness、memory、router、skills 核心。 |
| `agentflow_studio/` | 保留。内容生产与分发 pipeline 仍被 CLI 和测试覆盖。 |
| `apps/api/` | 保留。Runtime Service 是后续前端唯一对接面。 |
| `apps/cli/` | 保留。本地 deterministic harness 和运维入口。 |
| `apps/web/` | 过渡保留。只作为 read-only Web 工作台，等外部前端接管后再退休。 |
| `apps/web_bridge/` | 过渡保留。Runtime Service v0.2 后复审。 |
| `configs/` | 保留。只提交 example/config contract，不提交本地 secret。 |
| `data/` | 保留占位。只允许 `.gitkeep` 入库，runtime 输出继续 ignored。 |
| `docs/` | 保留但继续瘦身。当前承载 contract、runbook、handoff、维护账本和历史证据。 |
| `examples/` | 保留。contract fixture、CLI 输入和前端 request fixture。 |
| `tests/` | 保留。当前重构和前端对接的主要安全网。 |
| `tools/` | 保留。维护审计、staging preflight、retention review。 |
| `workflows/` / `prompts/` / `skills/` | 保留。Agent 执行投影和本地 workflow 输入。 |

## 已处理冗余

| 路径 | 处理 | 理由 |
|---|---|---|
| `README.zh-CN.md` | 删除，已提交 | `README.md` 已是中文主入口，继续保留两个中文 README 会造成入口漂移。 |

## 仍然存在的维护债务

| 债务 | 当前处理 | 下一步条件 |
|---|---|---|
| 历史英文文档较多 | 已新增中文摘要索引，不逐字翻译、不直接删除 | 若要删除原文，先证明没有测试、contract 或 handoff 引用。 |
| 部分文件超过 300 行 | 保留为 warning | Runtime Service v0.2 前后按模块边界拆分高收益文件。 |
| `configs/tool_catalog.yaml` 很长且含 secret 字段名 | 保留为配置契约，但继续标记 warning | 拆成 provider/tool 小文件，并把字段名风险降级为 schema field。 |
| `apps/web/` 文件多 | 过渡保留 | 外部画布工作台接管后，按测试迁移结果删除旧 Web 面。 |
| 大量 handoff 文档 | 保留为历史证据，已由中文摘要索引提供入口 | 外部引用清零后再逐批移入 archive 或删除。 |
| `data/processed/pytest-basetemp/` 权限残留 | ignored runtime，本轮不纳入 Git 审查 | 多个历史目录返回 Access denied；需要单独用本机权限处理，不影响 tracked/untracked retention review。 |

## 非声明边界

本审查只声明 repository retention review：

- 不是 human acceptance。
- 不是 business validation。
- 不是 durable memory。
- 没有调用 provider。
- 没有写入 secret、signed URL、本地私有素材或生成媒体。
- 没有把 COS candidate 规则晋升为 active。

## 下次复查标准

每次维护 PR 合并前至少运行：

```powershell
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
.\.venv\Scripts\python.exe tools\maintenance_audit.py --root .
git diff --check
```

若 `manual_review_required_count > 0`，必须先补分类或处理对应路径，不能直接声明项目已清理。
