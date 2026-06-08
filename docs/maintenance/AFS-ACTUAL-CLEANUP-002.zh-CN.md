# AFS 实际清理 002

状态：进行中，第一块 provider smoke 拆分已验证。

日期：2026-06-08

## 目标

本切片开始执行前序深度瘦身审查中已经确认的结构债，不再停留在规划。

本轮第一目标是降低 Kling provider smoke 的单文件职责混杂，保持现有 provider gate、safe manifest、task recovery 和测试行为不变。

## Dirty Ownership Ledger

| 类别 | 处理 |
|---|---|
| `DEVLOG.md`、`docs/company_operating_model.md` 的外部项目思想投影 | 保留为本切片前已存在的 COS 执行投影，并继续作为当前分支 dirty 内容 |
| Runtime Service v0.2 | 已在 `origin/master`，本切片从 `origin/master` 新开 `codex/afs-actual-cleanup-002` |
| provider live call | 未调用，仍由 `AFS_ALLOW_REMOTE_VIDEO` gate 控制 |
| runtime media / provider response | 未写入仓库 |

## 已执行清理

### 1. 拆分 Kling video smoke

原文件：

```text
agentflow_studio/model_gateway/kling_video_smoke.py
```

问题：

- 同时承担 smoke 入口、request plan、task resume 校验、poll/download 完成逻辑、fallback、video 文件写入和 safe manifest 写入。
- 被 `maintenance_audit` 归类为超 300 行 warning。

处理：

- 新增 `agentflow_studio/model_gateway/kling_video_completion.py`。
- `kling_video_smoke.py` 继续保留公开入口：
  - `run_kling_i2v_smoke`
  - `run_kling_t2v_smoke`
  - `resume_kling_video_task`
- completion 模块接管：
  - poll task。
  - httpx 到 curl fallback。
  - download video。
  - 写 safe task state。
  - 写 safe smoke manifest。

行数变化：

```text
kling_video_smoke.py: 327 -> 201
kling_video_completion.py: 116
```

`kling_video_smoke.py` 已退出超 300 行维护审计 warning。

### 2. 收口 Kling task state JSON helper

将：

```text
agentflow_studio/model_gateway/kling_video_task_state.py
```

中的 `write_json` 从旧 `agentflow_studio.utils` 切换到：

```text
agentflow.harness.json_io
```

这让 Kling video provider state/manifest 路径继续靠近平台 harness helper，而不是依赖旧 Studio utils。

### 3. 拆分 Kling video 测试边界

原文件：

```text
tests/test_kling_video_task_recovery.py
```

问题：

- 同时测试 poll failure safe state、resume、completion fallback、runtime poll retry。
- 被 `maintenance_audit` 归类为超 300 行 warning。

处理：

- `tests/test_kling_video_task_recovery.py` 只保留 task recovery / resume 行为。
- 新增 `tests/test_kling_video_completion.py` 覆盖 httpx 到 curl fallback。
- 新增 `tests/test_kling_video_runtime_polling.py` 覆盖 transient poll retry。

行数变化：

```text
test_kling_video_task_recovery.py: 317 -> 172
test_kling_video_completion.py: 86
test_kling_video_runtime_polling.py: 31
```

`test_kling_video_task_recovery.py` 已退出超 300 行维护审计 warning。

### 4. 拆分 MiniMax image smoke CLI 测试边界

原文件：

```text
tests/test_minimax_image_smoke.py
```

问题：

- 同时测试 smoke runtime、request plan、I2I subject reference、seed、CLI help 和 CLI gate failure。
- 被 `maintenance_audit` 归类为超 300 行 warning。

处理：

- `tests/test_minimax_image_smoke.py` 保留 runtime smoke / request plan 行为。
- 新增 `tests/test_minimax_image_smoke_cli.py` 覆盖 CLI help 和 CLI gate failure。

行数变化：

```text
test_minimax_image_smoke.py: 329 -> 232
test_minimax_image_smoke_cli.py: 60
```

`test_minimax_image_smoke.py` 已退出超 300 行维护审计 warning。

### 5. 拆分 PosterFlow provider 测试边界

原文件：

```text
tests/test_posterflow_provider.py
```

问题：

- 同时测试 OpenAI-compatible image provider、MiniMax image provider、provider factory 和共享测试 fixture。
- 被 `maintenance_audit` 归类为超 300 行 warning。

处理：

- 新增 `tests/posterflow_provider_helpers.py`，集中放测试图像 fixture、fake response 和 prompt pack。
- 新增 `tests/test_posterflow_openai_provider.py`，覆盖 OpenAI-compatible provider gate、配置、request error 和 secret redaction。
- `tests/test_posterflow_provider.py` 保留 MiniMax provider 和 provider factory。

行数变化：

```text
test_posterflow_provider.py: 342 -> 188
test_posterflow_openai_provider.py: 125
posterflow_provider_helpers.py: 46
```

`test_posterflow_provider.py` 已退出超 300 行维护审计 warning。

## 验证

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py -q
```

结果：

```text
16 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_architecture_audit_gates.py -q
```

结果：

```text
22 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_kling_video_completion.py tests/test_kling_video_runtime_polling.py tests/test_architecture_audit_gates.py -q
```

结果：

```text
22 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_minimax_image_smoke.py tests/test_minimax_image_smoke_cli.py tests/test_cli_command_registry_boundaries.py -q
```

结果：

```text
16 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_posterflow_provider.py tests/test_posterflow_openai_provider.py -q
```

结果：

```text
13 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_kling_video_completion.py tests/test_kling_video_runtime_polling.py tests/test_minimax_image_smoke.py tests/test_minimax_image_smoke_cli.py tests/test_posterflow_provider.py tests/test_posterflow_openai_provider.py tests/test_cli_command_registry_boundaries.py tests/test_architecture_audit_gates.py tests/test_maintenance_audit.py -q
```

结果：

```text
63 passed
```

已运行：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

结果：

```text
failed=0
passed=4
warning=2
oversized_files: 33 -> 29
secret_like_fragments high_confidence_count=0
```

已运行：

```powershell
git diff --check
```

结果：退出码 0；仅有 Windows 工作区 LF/CRLF 提示。

已运行：

```powershell
rg -n "[ \t]+$" agentflow_studio\model_gateway\kling_video_completion.py docs\maintenance\AFS-ACTUAL-CLEANUP-002.zh-CN.md tests\test_kling_video_completion.py tests\test_kling_video_runtime_polling.py tests\test_minimax_image_smoke_cli.py tests\posterflow_provider_helpers.py tests\test_posterflow_openai_provider.py
```

结果：退出码 1；无匹配，即新增文件没有尾随空白。

## 剩余风险

- `agentflow_studio.model_gateway` 与 `agentflow_studio.production` 的包级循环依赖仍是已知债务，本轮只拆 smoke completion，不改变 provider interface。
- `configs/tool_catalog.yaml` 仍为最大 oversized 文件，后续需要单独做配置分片或生成策略。
- 旧 Web / web_bridge / hidden CLI 本轮未删除。

## 非声明边界

- 本轮是结构清理和 runtime smoke 回归，不是 live provider validation。
- 未调用 Kling、OpenAI、MiniMax 或其他远程 provider。
- 未声明 human acceptance、business validation 或 durable memory。
- 未把 COS candidate rule 晋升为 active。
