# AgentFlow Studio

AgentFlow Studio 是一个本地优先、provider-gated 的内容生产工作台。当前用户侧 Web 是 **AFS Studio**：一个面向提示词记忆闭环的无限画布创作图谱。

当前产品不是复制某个外部工具，而是基于 AFS 自己的生产流程组织界面：

```text
创作意图
  -> 剧本 / 分镜
  -> 人物与场景参考
  -> 导演台调度
  -> 关键帧与视频片段提示词
  -> 本地预览或显式授权后的 provider 任务
```

第一阶段 MVP 聚焦“提示词记忆闭环”：用户在画布节点里输入提示词，点击“优化”，系统根据专业规则、项目上下文、人物/场景摘要和低权重用户偏好生成影视结构化提示词。隐藏记忆、trace、provider 状态和内部 gate 不出现在普通用户界面。

## 当前前端

启动 Runtime Service：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

打开：

```text
http://127.0.0.1:8790/studio/
```

`/studio/` 是当前唯一用户侧前端入口。旧 Workbench 和 static memory-workbench 已退出当前产品路径。

## 仓库结构

```text
apps/api/              FastAPI Runtime Service 和安全前端 API 边界
apps/cli/              本地 CLI、deterministic harness 和 smoke 入口
apps/studio/           当前 AFS Studio 画布前端
agentflow/             平台 contract、memory loop、harness、router、skills
agentflow_studio/      内容生产、分发、workflow、provider adapter
configs/               示例配置和 tool catalog contract
examples/              可提交 contract fixture 和最小示例
docs/                  架构、runbook、handoff、维护账本
tests/                 自动化验证
data/                  ignored runtime data；只提交 .gitkeep
```

## API 边界

前端只对接 Runtime Service，不读取 CLI 内部实现。

前端可以使用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest
- OpenAPI request / response 结构

前端不能暴露：

- provider secret
- 本地素材绝对路径
- signed URL
- provider 原始响应
- 私有媒体字节
- 生成媒体字节

## 本地开发

```powershell
cd D:\Projects\AgentFlowStudio
python -m venv .venv
.\.venv\Scripts\pip.exe install -e .[dev]
.\.venv\Scripts\python.exe -m apps.cli.main version
```

基础验证：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

维护清理追加：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

远程 provider 默认关闭，必须按能力显式授权。浏览器 QA、deterministic tests、provider smoke、human acceptance、business validation 和 durable-memory 结论必须分开。
