# AFS + COS 接手交接 - 2026-06-26

本文是 AgentFlow Studio 与 Company OS 上下文的当前接手入口。它是仓库内
执行投影，不是私有 Company OS 源头知识库。

## 当前状态

- 本地仓库：`D:\Projects\AgentFlowStudio`
- 默认分支：`master`
- 当前代码事实来源：`master` 的当前 HEAD
- 最近功能基线：`e3d8092 feat(studio): expose keyframe asset constraints`
- GitHub 基线：`origin/master`
- 服务器 `/home`：`/home/afs-ops/AgentFlowStudio`
- 服务器 `/opt`：`/opt/afs/AgentFlowStudio`
- Runtime：`http://127.0.0.1:8790/health` 返回 `status=ready`
- 最近一次 provider gate：LLM true、image true、video true、vision true、
  ASR false、external download false
- 当前产品入口：`/studio/`

## 接手阅读顺序

开始改代码前按下面顺序阅读：

1. `AGENTS.md`
2. `docs/company_operating_model.md`
3. `docs/GFR_EXECUTION_PROJECTION.md`
4. `docs/handoff/INDEX.md`
5. `TASK_TRACKER.md`
6. `DEVLOG.md`
7. 本文件

如果需要 COS 源头上下文，只使用 `AGENTS.md` 和
`docs/company_operating_model.md` 中列出的源头控制文件。不要把私有 Company
OS 源头材料复制到本仓库。

## 当前产品链路

当前 MVP 主链路是：

```text
/studio/ canvas
  -> Runtime Service
  -> prompt / script optimization
  -> storyboard nodes
  -> editable asset cards
  -> keyframe generation
  -> keyframe-to-video node
  -> provider-gated Seedance image-to-video
```

已部署的近期修复：

- 文本想法扩写现在先生成正式短视频剧本正文，再拆分分镜，不再输出占位
  `分镜 01/02/03/04` 模板。
- 关键帧生成会携带连接的候选资产卡签名、特征摘要、参考图数量和负向约束。
- 关键帧图片节点右键已有 `编辑关键帧资产约束`，可在重新生成前手动修订
  资产/提示词约束。
- 视频节点 `识别视频资产卡` 已修复点击路径，并会显示未生成视频、识别中、
  成功或失败反馈。
- Runtime video job 已写入安全耗时字段：`provider_phase`、`elapsed_sec`、
  `queued_sec`、`running_sec`。

## 验证证据

最近本地验证：

```powershell
.\.venv\Scripts\python.exe -m pytest
# 631 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 121 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

git diff --check
# passed
```

最近服务器验证：

```text
local master == origin/master == /home == /opt
Runtime /health status=ready
Studio static modules returned HTTP 200
```

## 分支和 Worktree 基线

清理后的目标状态是：

- 本地分支：只保留 `master`
- GitHub 分支：只保留 `master`
- 服务器 `/home` 分支：只保留 `master`
- 服务器 `/opt` 分支：只保留 `master`
- AFS worktree：只保留主工作树 `D:\Projects\AgentFlowStudio`

后续任务如果需要新分支，使用 `codex/<task-slug>`。涉及 Runtime、Studio、
provider、schema、contract、清理或发布的任务，优先使用隔离 worktree。

## 服务器注意事项

GitHub `master` 是代码基线。服务器是 runtime state，不是代码事实来源。

声明部署对齐前，分别检查：

```bash
cd /home/afs-ops/AgentFlowStudio && git status -sb && git rev-parse --short HEAD
cd /opt/afs/AgentFlowStudio && git status -sb && git rev-parse --short HEAD
curl -fsS http://127.0.0.1:8790/health
```

`/home` checkout 当前有未跟踪 `ops/` 目录。它被视为 ops-local artifact，不属于
本次仓库分支清理范围；不要在没有单独 ops review 的情况下删除。

如果需要重启 Runtime 且没有 passwordless sudo，先确认进程命令，只终止
`runtime-service` 用户进程，让 systemd 接管重启。不要误杀图片 worker 或其他
无关进程。

## Provider Gate

Provider gate 是按能力授权的。视频任务必须显式授权 video；image 授权不代表
video、ASR、LLM 或 external download 也被授权。

禁止提交：

- provider secret 或本地 provider config
- signed URL
- provider 原始响应
- 生成媒体字节
- 本地私有媒体路径
- 客户材料或私有 Company OS 源头材料
- 内部失败复盘原文

## 下一位接手者的第一步

推荐先做这些低风险检查：

1. 打开 `/studio/`，做一次不调用 provider 的画布浏览器 smoke。
2. 跑一条 deterministic 的文本 -> 剧本 -> 分镜 -> 资产卡 -> 关键帧提示词构造
   链路，不触发真实 provider。
3. 只有在明确授权后，使用中性、非 IP 的内容跑一次视频 provider smoke，确认
   `queued_sec/running_sec` 在真实视频任务中写入。
4. 如果需要公开或外部 GitHub 治理，请从当前 `master` 新建分支重做；不要恢复
   旧的 `codex/open-source-handoff-governance` 分支。

## 声明边界

- 自动化测试只代表 structure verification。
- Runtime health 只代表 runtime verification。
- Provider smoke 只代表 provider-path verification。
- 上述任何一项都不等于 human creative acceptance、business validation 或
  durable Company OS memory promotion。
