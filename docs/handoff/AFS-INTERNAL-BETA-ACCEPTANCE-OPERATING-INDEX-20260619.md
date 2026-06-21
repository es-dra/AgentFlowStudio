# AFS 内测验收操作索引

日期：2026-06-19
状态：当前内测 readiness 与 acceptance 的操作入口

## 用途

本文用于把 AFS 从“工程验证通过”推进到“受控内测验收”。它不替代既有工具，也不替代旧人工验收手册；它只回答三个问题：

- 什么时候跑哪个命令；
- 每条命令最多能证明什么；
- 哪些结论仍然不能声明。

当前索引只写 repo 执行投影，不写入 secret、provider 配置、本地素材、真实邀请码或 COS 私密判断。

## 路线 1：三端 readiness

每次 GitHub、本地或服务器有变化后，先跑三端状态：

```powershell
.\.venv\Scripts\python.exe tools\afs_three_end_status.py `
  --repo-root . `
  --server afs-bwg-ops `
  --report runs\internal_beta\three-end-YYYYMMDD.json
```

这条路线证明：

- 本地、GitHub `origin/master`、服务器 `/home`、服务器 `/opt` 是否对齐；
- 是否存在 dirty state；
- Runtime `/health` 的安全字段是否 ready；
- `video=false` 是否仍按当前边界关闭。

这条路线不证明 human acceptance、provider smoke、business validation 或 durable memory。

## 路线 2：线上 Runtime preflight

服务器已运行时，先用 preflight 判断是否具备邀请码验收条件：

```powershell
.\.venv\Scripts\python.exe tools\afs_internal_beta_acceptance.py `
  --base-url https://YOUR_RUNTIME_OR_SITE_ORIGIN `
  --preflight-only `
  --three-end-status `
  --three-end-server afs-bwg-ops `
  --report runs\internal_beta\preflight-YYYYMMDD.json
```

成功状态应为：`ready_for_http_acceptance`。

这条路线证明：

- `/health`、`/auth/status`、Studio 静态资源、provider gate 投影和可选三端状态可安全读取；
- 本轮是 no provider call；
- auth 开启时，完整 HTTP 验收必须使用一次性邀请码。

## 路线 3：本地 deterministic contract

没有服务器或没有一次性邀请码时，用本地 deterministic 合约做快速回归：

```powershell
.\.venv\Scripts\python.exe tools\afs_internal_beta_acceptance.py `
  --report runs\internal_beta\inprocess-YYYYMMDD.json `
  --human-review-md runs\internal_beta\human-review-YYYYMMDD.md
```

成功状态应为：`contract_verified_pending_human_acceptance`。

这条路线验证 auth、项目隔离、Studio state 隔离、image asset 隔离、vision draft gate、fixed asset 防污染、feedback raw evidence、artifact scope 和 video gate closed 等 deterministic 合约。

## 路线 4：线上 HTTP acceptance

只有在有一次性邀请码时才运行。邀请码只放本地环境变量，不提交：

```powershell
$env:AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE = "<disposable-alpha-code>"
$env:AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA = "<disposable-beta-code>"

.\.venv\Scripts\python.exe tools\afs_internal_beta_acceptance.py `
  --base-url https://YOUR_RUNTIME_OR_SITE_ORIGIN `
  --report runs\internal_beta\http-acceptance-YYYYMMDD.json `
  --human-review-md runs\internal_beta\human-review-YYYYMMDD.md
```

成功状态应为：`contract_verified_pending_human_acceptance`。

生成的 Markdown review packet 仍是 `pending_human_review`，必须由人工完成评分和决策后，才能把对应 run 说成 human acceptance。

## 结论分级

| 证据 | 允许声明 | 仍不能声明 |
|---|---|---|
| 三端报告 `aligned` | 部署代码状态已对齐 | human acceptance、provider smoke、business validation |
| Preflight `ready_for_http_acceptance` | 服务器具备邀请码验收前置条件 | 完整验收完成或媒体质量合格 |
| Acceptance `contract_verified_pending_human_acceptance` | deterministic 内测合约通过 | 人工验收，直到 review packet 完成 |
| 人工决策 `accepted_for_next_beta_round` | 本次 run 的 human acceptance 通过 | business validation 或 durable memory promotion |

## 人工 review packet

`--human-review-md` 会生成人工验收 Markdown。操作者至少完成这些区块：

- 账号与项目隔离；
- 资产确认与上下文连续性；
- 生成媒体质量；
- 反馈与修订链路；
- 隐私与 provider 边界。

低于通过阈值的区块必须进入 `needs_fix_before_next_beta_round` 或 `blocked_by_provider_or_configuration`，不能把工程绿灯包装成人工验收。

## 安全边界

报告和人工记录禁止出现：

- secret、token、cookie、账号密码、真实邀请码；
- provider raw response；
- signed URL；
- local absolute path；
- 私有素材字节、生成 media bytes；
- provider key 或本地配置文件内容。

报告默认放在 ignored 的 `runs\internal_beta\...` 下。只有经过脱敏的摘要，才可以进入 `docs\handoff`。

## 当前服务器基线必须重查

当前内测预期形态是：

- Runtime health `status=ready`；
- `auth_required=true`；
- provider gates: `llm=true`, `image=true`, `vision=true`, `video=false`；
- Studio static readiness `status=ready`；
- GitHub `master`、服务器 `/home`、服务器 `/opt` 在声明部署状态前必须对齐。

这些值可能漂移。任何“当前状态”声明前，都要重新跑路线 1 或路线 2。
