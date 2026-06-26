# AFS 内测账号与邀请码管理员方案 - 2026-06-26

本文是当前内测邀请的管理员操作手册。目标是让维护者可以低成本分发账号入口，
同时不把邀请码、session token、provider secret 或用户数据写进 Git。

## 当前账号能力

Runtime 已具备：

- `AFS_AUTH_ENABLED=true` 后启用账号门禁。
- `/auth/register` 使用一次性邀请码注册。
- `/auth/login` 返回 session token。
- `/auth/status` 公开返回 auth 状态和是否允许 invite registration。
- 项目按 `project_owner` 隔离，用户只能看到自己的项目。
- session 有 TTL，默认 168 小时，可由 `AFS_AUTH_SESSION_TTL_HOURS` 调整。
- 登录和注册失败有最小限流，默认同一来源和同一账号标识 5 次失败后锁 15 分钟。
- 登录、注册、邀请码环境变量跳过、限流事件会写入 systemd journal 审计日志。

这仍是内测账号系统，不是 SaaS 级组织、角色、计费或团队权限系统。

## 管理原则

- 邀请码明文只给管理员和被邀请者。
- Runtime auth store 只保存邀请码 hash。
- 不使用短码、`123456`、`password`、`admin`、`test` 等固定弱邀请码；Runtime 会跳过这些环境变量邀请码。
- 不在 GitHub issue、PR、日志、handoff、DEVLOG 或 TASK_TRACKER 写邀请码明文。
- 每一批邀请码要有 `batch_id`，方便后续盘点和撤销。
- 被邀请者遇到问题时，收集账号邮箱、项目 id、浏览器现象和时间，不收集密码或
  session token。

## 管理命令

命令组：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main auth-invites --help
```

生成一批邀请码：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main auth-invites issue `
  --runtime-root data/processed/runs/runtime_service `
  --count 20 `
  --batch internal-beta-wave1-20260626 `
  --note "第一批内测用户" `
  --output data/outputs/internal_beta_invites/internal-beta-wave1-20260626.csv
```

指定 `--output` 时，命令行只显示 `invite_id` 和状态；邀请码明文只写入 CSV，便于管理员单独分发。

服务器上使用真实 Runtime root：

```bash
cd /opt/afs/AgentFlowStudio
.venv/bin/python -m apps.cli.main auth-invites issue \
  --runtime-root /var/lib/afs-runtime \
  --count 20 \
  --batch internal-beta-wave1-20260626 \
  --note "第一批内测用户" \
  --output /home/afs-ops/afs-admin/invites/internal-beta-wave1-20260626.csv
chmod 600 /home/afs-ops/afs-admin/invites/internal-beta-wave1-20260626.csv
```

查看状态，不显示明文邀请码：

```bash
cd /opt/afs/AgentFlowStudio
.venv/bin/python -m apps.cli.main auth-invites list --runtime-root /var/lib/afs-runtime
```

撤销未使用的邀请码：

```bash
cd /opt/afs/AgentFlowStudio
.venv/bin/python -m apps.cli.main auth-invites revoke inv_xxxxxxxxxxxx \
  --runtime-root /var/lib/afs-runtime
```

## 分发建议

给每个内测用户单独发送：

```text
入口：https://afstudio.art/studio/
注册邮箱：请使用你常用的接收反馈邮箱
邀请码：<单独发送一个 code>
反馈方式：把问题截图、项目 id、发生时间、期望结果发回，不要发送密码或 token。
```

不要群发同一个邀请码；当前邀请码是一人一次。

## 备份命令

生成 Runtime 数据备份：

```bash
cd /opt/afs/AgentFlowStudio
mkdir -p /home/afs-ops/afs-admin/backups
chmod 700 /home/afs-ops/afs-admin /home/afs-ops/afs-admin/backups
.venv/bin/python -m apps.cli.main runtime-backup create \
  --runtime-root /var/lib/afs-runtime \
  --output-dir /home/afs-ops/afs-admin/backups \
  --label manual-before-beta \
  --retention-days 14
```

默认会排除 `codex-home` 和 `.lock` / `.tmp` 文件，避免把本地工具认证材料打进备份。
备份文件权限会收紧为 `600`。该备份仍包含用户邮箱、session hash、项目和生成证据，
只能放在管理员目录，不要上传 Git。

建议内测期至少每日备份一次。可以用 `crontab -e` 添加：

```cron
15 3 * * * cd /opt/afs/AgentFlowStudio && .venv/bin/python -m apps.cli.main runtime-backup create --runtime-root /var/lib/afs-runtime --output-dir /home/afs-ops/afs-admin/backups --label nightly --retention-days 14 >/home/afs-ops/afs-admin/backups/runtime-backup.log 2>&1
```

## 审计与限流

查看 Runtime 审计日志：

```bash
journalctl -u afs-runtime --since "1 hour ago" --no-pager | grep 'runtime_audit'
```

查看慢请求或 5xx：

```bash
journalctl -u afs-runtime --since "1 hour ago" --no-pager | grep 'runtime_request_slow_or_error'
```

默认限流环境变量：

```text
AFS_AUTH_RATE_LIMIT_MAX_FAILURES=5
AFS_AUTH_RATE_LIMIT_WINDOW_SECONDS=900
AFS_AUTH_RATE_LIMIT_LOCK_SECONDS=900
```

限流状态存储在 `/var/lib/afs-runtime/auth/rate_limits.json`。不要手工编辑，除非明确要解除误锁。
如果确实要解除，先停止 Runtime 或确认无人注册登录，再删除对应 bucket。

## 接手反馈处理

当用户反馈问题时，先分类：

| 类型 | 处理方式 |
|---|---|
| 登录/注册失败 | 检查邀请码是否 consumed/revoked/expired，检查邮箱是否已注册。 |
| 登录被锁定 | 查看 `rate_limits.json` 或 journal 审计日志；默认 15 分钟自动解除。 |
| 项目看不到 | 检查 `project_owners.json` 和用户邮箱对应的 `user_id`。 |
| 生成失败 | 看对应节点的 job id、safe manifest、provider gate，不要要求用户提供 token。 |
| 体验问题 | 记录截图、步骤、期望结果，进入 `TASK_TRACKER.md` 或 GitHub issue。 |
| 创意质量问题 | 作为 human feedback，不等同于 Runtime bug。 |

## 边界

- 管理 CLI 是本地/SSH 管理工具，不是公开 HTTP 管理后台。
- 不提供密码重置、邮箱验证、组织管理或角色系统。
- 当前存储仍是 Runtime JSON 文件，不是数据库；内测期依赖文件锁、原子写和备份降低风险。
- 不自动把内测反馈写入长期 Company OS memory。
- 如需更正式的管理员 UI，应在下一阶段从当前 CLI 能力之上做，而不是绕过
  Runtime auth store。
