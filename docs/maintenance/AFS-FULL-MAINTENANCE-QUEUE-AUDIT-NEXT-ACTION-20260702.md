# AFS Full Maintenance Queue Audit And Next Action - 2026-07-02

## C1 Execution Update - 2026-07-02

本文件的原始判断停在“先建立历史摘要，再决定归档/删除”。后续 C1 已完成第一步并执行第一批可恢复归档：

- `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 已存在，并继续作为历史文档摘要入口。
- `docs/maintenance/AFS-DOCS-CURRENTNESS-CLEANUP-LEDGER-20260702.zh-CN.md` 是本轮实际 currentness / cleanup ledger。
- 11 个无当前索引入口、无外部引用的 handoff 已移动到 `docs/archive/handoff/`。
- 9 个无当前索引入口、无外部引用的 maintenance 账本已移动到 `docs/archive/maintenance/`。
- 本轮没有物理删除 tracked docs，未触碰 `docs/demo-docs-20260629/`、provider、server、runtime evidence、local config、secret、generated/private media 或 CompanyOS active rule。

后续接手时，应从上述 ledger 继续处理剩余“被 `TASK_TRACKER.md`、`DEVLOG.md` 或维护账本引用”的旧文件，而不是重复本文件的 summary-only 预备动作。

中文摘要：本文件是 T51-T54 与 R3 之后的维护队列复核，不是分支卫生重复报告。R3 已经处理旧 redundancy branch / worktree residue；本轮把剩余维护债按审计 warning、超大模块、松散/待办文档、过期 handoff、server-sync 残留、本地保护路径重新归类，并给出下一条可执行清理建议。本文不执行 provider、server sync、deploy、删除、reset、clean、外部下载、客户/成本/私有素材处理或 CompanyOS active-rule 晋升。

## 中文执行说明

本轮维护判断的重点是把“还剩什么债”与“现在能做什么”分开。分支卫生在 R3 已经收口，旧的冗余维护分支、重建工作树和远端残留都不再是当前问题；继续围绕旧分支重复审计只会消耗调度注意力。真正留下来的维护队列主要是文档、历史证据、超大测试、遗留分发链、旧 Production Memory 表面、低置信度 secret-like 告警、以及本地缓存权限问题。这些问题不会阻塞当前产品切片，但如果不登记，会在下一次集成、部署或新人接手时重新变成噪声。

本文件采用的处理原则是：能证明已经收口的事项标记为已解决；能在当前波次低风险推进的事项只推荐形成后续清理 lane；涉及 provider、server、视频、旧运行时、权限缓存、历史证据删除或私有本地材料的事项全部延后并要求复核。这样做的目的不是保守，而是避免把文档治理、代码拆分、服务器同步和产品实现混成一个不可验证的大动作。后续如果 CEO 或 Owner 要执行清理，应该从本文的推荐 lane 启动，先重新跑审计，再按写入范围逐项推进。

当前最值得推进的低风险事项不是删除文件，而是建立中文历史摘要与当前性索引，让维护审计能够区分“有摘要的历史证据”和“真的需要人工阅读的当前文档”。在这个索引存在之前，大量旧 handoff 看起来都像活跃债务；索引完成后，才能决定哪些文件继续保留、哪些只保留摘要、哪些可以在明确授权下归档或删除。另一个小型候选是 CLI 中的 no-op support registry 包装器，但它触碰命令入口，必须等测试证明没有用户可见变化后再执行。

本轮没有读取或写入本地 provider secret，没有触碰演示文档目录，没有处理服务器，也没有把任何运行时证据、生成媒体或公司私有知识写入仓库。所有结论只代表维护队列状态，不代表产品完成、部署完成、商业验证完成或人工验收完成。

## Contract

| Field | Value |
|---|---|
| artifact_class | `afs_full_maintenance_queue_audit_next_action` |
| workspace_root | `D:\Projects\AgentFlowStudio` |
| source_ceo_thread | `019f1e02-a8b2-7c93-a931-bfd1cc2c254a` |
| work mode | Deep maintenance audit, non-destructive |
| write_scope | this maintenance artifact plus handoff index entry |
| provider gates | closed for LLM, ASR, image, video, external download, and high-cost actions |
| server authority | no server sync, restart, deploy, SSH repair, or runtime-health execution |
| cleanup authority | inventory and follow-up recommendation only; no delete/archive/reset/clean |
| protected state | `docs/demo-docs-20260629/`, secrets, provider raw responses, signed URLs, generated/private media, local config |

## Startup Snapshot

| Item | Current observation |
|---|---|
| primary checkout | `master` at `5ddbd39966f31bd5298375d3721f469c08ae404f`, aligned with `origin/master` |
| remote heads | only `refs/heads/master` at `5ddbd39966f31bd5298375d3721f469c08ae404f` |
| primary dirty state | only protected untracked `docs/demo-docs-20260629/` files |
| worktrees | primary checkout plus active T54 worktree `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-t54-spec2-branch-workflow-package-20260702` |
| T54 worktree state | branch `codex/afs-t54-spec2-branch-workflow-package-20260702`, dirty product-lane files under `agentflow/algorithms/branch_workflow_package`, fixture, and test |
| redundancy residue | R3 closeout records no remaining local redundancy branches, no redundancy branch config, and no remote redundancy heads |
| indexed docs check | indexed Markdown targets exist on disk, but 20 handoff files and 24 maintenance files are currently unindexed |

## Maintenance Audit Warning Groups

Fresh `tools/maintenance_audit.py` result:

| Check | Count | State | Queue classification |
|---|---:|---|---|
| `legacy_frozen_surface` | 10 | warning only | `backlog_defer_with_recheck` |
| `human_doc_chinese_coverage` | 34 tracked docs | warning only | `current_wave_cleanup_candidate` for summary/index work; broad localization deferred |
| `secret_like_fragments` | 9, `high_confidence_count=0` | warning only | `backlog_defer_with_recheck`; read-only security/provider classification first |
| `oversized_files` | 60 total: 58 tracked, 2 protected untracked demo docs | warning only | split by risk below |
| blocking failures | 0 | passed | `resolved` for blocker state only |

Legacy-frozen surface remains the same family: `agentflow/memory`, legacy SOP/distribution paths under `agentflow_studio/*_sop`, `agentflow_studio/production`, `agentflow_studio/workflow_engine`, and `apps/cli/production_memory_`. These are not current MVP entry points, but they are still import/test-sensitive enough to require a dedicated legacy quarantine lane.

Secret-like findings are low-confidence or fixture/code-surface hits only in this run. No high-confidence secret was reported by the audit. They stay deferred to a read-only provider/security lane because the paths include provider adapters, auth code, video dispatch, tests, and frontend mention suggestions.

## Oversized / Module Queue

| Area | Evidence | Category | Next action |
|---|---|---|---|
| `DEVLOG.md`, `TASK_TRACKER.md` | 8611 and 2207 lines | `current_wave_cleanup_candidate` | create compact current-state index before pruning; do not rewrite in a product lane |
| active Runtime/API modules | examples include `runtime_keyframes.py` 911, `runtime_video_dispatch.py` 689, `runtime_keyframe_routes.py` 515 | `backlog_defer_with_recheck` | split only in focused Runtime maintenance lanes with focused pytest plus full suite gate |
| active Studio modules/styles | examples include `runtime-client.js`, `asset-card-drafts.js`, `modals.css`, `studio-project-controller.js` | `backlog_defer_with_recheck` | split only after current product worktree closes or with disjoint UI scope |
| provider/model gateway files | examples include `volc_seedance_video.py`, `provider_api_relay.py`, `codex_image_worker.py` | `backlog_defer_with_recheck` | provider-sensitive; classify before edit and keep provider gates closed |
| large tests | multiple Runtime/Studio/provider tests exceed threshold | `safe_low_risk_cleanup_authorized_after_checks` for planning, not mass rewrite | first lane should add a test-split plan and extract only one low-risk helper if touched |
| `apps/cli/support_command_registry.py` | retention review marks one `hidden_provider_and_legacy_cli` transition surface; file is currently a no-op wrapper | `safe_low_risk_cleanup_authorized_after_checks` | tiny cleanup candidate after CLI registry tests and `--help`/`version`; do not mix with T54 |
| protected demo docs | 2 untracked demo files exceed line threshold | `do_not_touch` | keep local-only unless Owner explicitly changes scope |

## Loose / Backlog Docs

| Item | Evidence | Category | Next action |
|---|---|---|---|
| `BACKLOG.md` | exists, but current T51-T54/R3 queue is not reflected as a fresh table item | `current_wave_cleanup_candidate` | update or supersede with this artifact's queue in a docs-only lane |
| `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` | maintenance audit names it as `historical_summary_path`, but it does not exist | `safe_low_risk_cleanup_authorized_after_checks` | create a concise archive/currentness summary before any handoff/doc pruning |
| retention review | `delete_candidate_count=0`, `manual_review_required_count=0`, `archive_or_delete_when_indexed=127 files + docs/handoff dir`, `review_for_currentness=34 files + docs/ dirs` | `current_wave_cleanup_candidate` | docs/index lane should summarize first, then propose archive/delete candidates |
| unindexed handoff/maintenance docs | 20 handoff files and 24 maintenance files exist on disk but are not listed in `docs/handoff/INDEX.md` | `current_wave_cleanup_candidate` | docs/index lane should classify as current, archive-summary-only, or delete-after-owner-approval; no bulk index/delete here |
| indexed Markdown targets | all indexed Markdown targets checked in this lane exist on disk | `resolved` for broken-reference risk | keep future index edits verified |

## Obsolete Handoff Queue

No handoff file is proven obsolete enough for deletion in this lane. The queue is:

| Handoff group | Category | Reason |
|---|---|---|
| current release gates T51-T53 and T46-T50 | `backlog_defer_with_recheck` | still carry current evidence and non-claim boundaries |
| unindexed handoffs such as CompanyOS feedback candidates, D1 project-book packet, Director Stage, human-acceptance runbooks, older frontend/TuanTuan/Studio files | `current_wave_cleanup_candidate` | they are real loose docs; summarize/index/archive decision is needed before any deletion |
| many `*-TASKRUN-20260630.md` handoffs | `current_wave_cleanup_candidate` | likely summarizable after a Chinese archive summary exists |
| older Browser QA, MVP, provider-flow, and Studio v0.x handoffs | `backlog_defer_with_recheck` | need reference scan and summary before archive/delete |
| old Workbench/static web handoffs already removed | `resolved` | `docs/handoff/INDEX.md` says retired Workbench/static memory-workbench/old LibTV paths were deleted instead of archived |

## Branch / Worktree Residue

This is a current-state note, not a branch-hygiene lane.

| Subject | Category | Next action |
|---|---|---|
| R3 redundancy cleanup | `resolved` | no redundancy branches/config/worktree or remote heads remain per R3 and current branch scan |
| remote branch surface | `resolved` | `git ls-remote --heads origin` returns only `master` |
| active T54 branch/worktree | `do_not_touch` | product lane is dirty and outside this maintenance audit write scope |
| primary checkout protected untracked demo docs | `do_not_touch` | keep visible; do not stage, edit, delete, clean, or use as cleanup input |

## Server-Sync Residue

No server command was run in this lane. Current repository state has commits after the last durable server/runtime-health sync evidence:

| Evidence | Category | Next action |
|---|---|---|
| T46 recorded local/origin/server `/home`/server `/opt` sync at `72c698ac` and runtime `status=ready` | `resolved` only for T46 date/state | do not reuse as current server state |
| current local/origin head is `5ddbd399` after T51-T54/R3 docs/code work | `backlog_defer_with_recheck` | next release/deploy lane must recheck server `/home`, `/opt`, service CWD, and `/health` before claiming alignment |
| this lane has no deploy/runtime authority | `owner_decision` | Owner/CEO decides whether current `master` needs server sync now or waits for T54 integration |

## Protected Local-Only Paths

| Path | Category | Notes |
|---|---|---|
| `docs/demo-docs-20260629/` | `do_not_touch` | five untracked demo docs; not tracked and not cleanup input |
| `configs/models.yaml` | `do_not_touch` | ignored local config |
| `configs/providers.local.json` | `do_not_touch` | ignored local provider config; do not read/copy secrets from local configs |
| `.venv/`, `.pytest_cache/`, `.tmp/`, `runs/`, `data/processed/*` | `do_not_touch` by default | ignored runtime/test evidence; admin cleanup only under separate local-cache lane |
| ACL-denied pytest basetemp directories | `backlog_defer_with_recheck` | current scan still produced permission warnings under `.venv` and `data/processed/pytest-basetemp`; this is an admin-shell cleanup item, not repo code work |

## Execution Map

| Category | Items |
|---|---|
| `resolved` | R3 old redundancy branch/worktree cleanup; remote only `master`; indexed Markdown targets are not broken; retention review has zero immediate delete candidates and zero manual-review-required unknowns |
| `current_wave_cleanup_candidate` | docs/currentness and archive summary; 20 unindexed handoff files; 24 unindexed maintenance files; `BACKLOG.md` refresh/supersession; summarizing dense T51-T53/T46-T50 handoff evidence; `DEVLOG.md` and `TASK_TRACKER.md` current-state index before future pruning |
| `safe_low_risk_cleanup_authorized_after_checks` | create `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`; add a docs queue entry; optionally remove the no-op `apps/cli/support_command_registry.py` wrapper after CLI boundary tests prove no user-visible change |
| `backlog_defer_with_recheck` | legacy frozen surfaces; broad oversized Runtime/Studio/provider/test splits; secret-like warning classification; server sync recheck; ACL-denied local caches; provider/video legacy routes |
| `owner_decision` | whether to run a server sync/deploy check before or after T54; whether protected demo docs remain local-only; whether broad legacy quarantine is worth a dedicated lane now |
| `do_not_touch` | T54 dirty worktree, `docs/demo-docs-20260629/`, local configs, secrets/provider raw/private assets, generated media bytes, ignored runtime evidence |

## Recommended Follow-Up Cleanup Lane

This is the recoverable low-risk current-wave recommendation. It is inside AFS and excludes provider/server/secret/customer/local-private state.

```text
You are the AFS Maintenance Queue C1 Docs/CLI Micro-Cleanup Worker.

Workspace root: D:\Projects\AgentFlowStudio
Start from latest master after checking whether T54 is still active. Use project-development-workflow first and run startup scan.

Scope:
- Do not touch docs/demo-docs-20260629/, local configs, provider raw responses, generated media, secrets, server, deploy, Runtime health, or active T54 files.
- Write scope is limited to docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md, BACKLOG.md or a small docs/maintenance queue update, docs/handoff/INDEX.md, and optionally apps/cli/support_command_registry.py plus apps/cli/command_registry.py/tests if the no-op wrapper removal is chosen.

Plan:
1. Re-run tools/repository_retention_review.py --summary-only and tools/maintenance_audit.py.
2. Create a Chinese archive/currentness summary that maps docs/handoff archive candidates and docs currentness-review groups without deleting files.
3. Refresh the maintenance backlog entry to point to this queue and the archive summary.
4. Optional tiny code cleanup only if still low-risk: remove the no-op support_command_registry wrapper and its import, update CLI boundary tests, then verify no hidden provider/support command surface returns.

Verification:
- .\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
- .\.venv\Scripts\python.exe tools\maintenance_audit.py
- .\.venv\Scripts\python.exe -m apps.cli.main --help
- .\.venv\Scripts\python.exe -m apps.cli.main version
- .\.venv\Scripts\python.exe -m pytest tests\test_cli_command_registry_boundaries.py tests\test_architecture_audit_gates.py -q if CLI wrapper is touched
- git diff --check

Closeout:
- Report changed files, warning count movement, non-claims, and whether CLI cleanup was skipped or completed.
- Do not claim provider smoke, server alignment, runtime health, generated-media quality, human acceptance, business validation, legal/public release, durable-memory promotion, or COS active-rule promotion.
```

## Verification Evidence

Commands run in this audit lane:

```text
Get-Content C:\Users\chenzy\.codex\skills\project-development-workflow\SKILL.md
Get-Content AGENTS.md docs\company_operating_model.md TASK_TRACKER.md DEVLOG.md docs\handoff\INDEX.md
Get-ChildItem docs\maintenance
git status --short --branch --untracked-files=all
git worktree list --porcelain
git branch --all --verbose --no-abbrev
git ls-remote --heads origin
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
handoff/maintenance index cross-check scripts
git check-ignore -v configs\models.yaml configs\providers.local.json data\processed\pytest-basetemp .pytest_cache
```

Observed verification results:

```text
maintenance_audit: status=warning; failed=0; warning=4
repository_retention_review --summary-only: delete_candidate_count=0; manual_review_required_count=0
handoff/maintenance index cross-check: indexed Markdown targets exist; 20 handoff files and 24 maintenance files are currently unindexed and should be handled by the docs/index follow-up lane
primary checkout before this artifact: master aligned with origin/master; only protected untracked docs/demo-docs-20260629/
remote heads: only origin/master
```

## Non-Claims

This artifact does not claim product readiness, provider smoke, live provider calls, generated-media quality, human creative acceptance, business validation, server/runtime health, deploy alignment, public/legal/patent approval, durable-memory promotion, or CompanyOS/COS active-rule promotion.
