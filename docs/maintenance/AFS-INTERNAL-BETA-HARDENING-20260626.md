# AFS 内测可用性与安全硬化 - 2026-06-26

## 范围

本轮处理的是扩大内测前的最低运行风险，不是完整 SaaS 化改造。目标是让
`/studio/` 可以继续对内测用户开放，同时把最容易造成事故的问题先压住。

已覆盖：

- 环境变量中的弱邀请码兜底过滤。
- 登录和注册失败限流。
- 登录、注册、限流、弱邀请码跳过的安全审计日志。
- 请求 `X-Request-ID`、慢请求和 5xx 日志。
- JSON 写入改为同目录临时文件、`fsync`、原子替换和文件锁。
- auth 读改写流程增加 `auth.lock`，降低并发注册、登录、session 更新时的丢写风险。
- 新增 `runtime-backup create` 管理员备份命令。

## 非目标

- 不做公开管理员 UI。
- 不做 OAuth、邮箱验证、密码重置、组织、角色、计费系统。
- 不在本轮迁移 SQLite 或 Postgres。
- 不把 provider 原始响应、token、session token、邀请码明文、媒体字节或公司源头知识库内容写入 Git。

## 管理员入口

账号、邀请码、分发、备份、审计命令统一看：

```text
docs/handoff/AFS-INTERNAL-BETA-ADMIN-20260626.md
```

## 验证命令

```text
pytest tests/test_api_runtime_auth.py tests/test_api_runtime_auth_modules.py tests/test_cli_command_registry_boundaries.py tests/test_json_io_atomic.py -q
pytest
python -m apps.cli.main auth-invites --help
python -m apps.cli.main runtime-backup --help
git diff --check
python tools/maintenance_audit.py
```

## 剩余风险

- 当前 Runtime 存储仍是 JSON 文件，不适合大规模多用户并发。
- 备份文件仍包含用户邮箱、session hash、项目数据和生成证据，必须保存在管理员目录，不得提交 Git。
- root-owned systemd drop-in 中的历史弱邀请码配置需要有 sudo 权限的人清理；代码层已经跳过弱环境邀请码，避免 runtime root 重建后再次种入。
