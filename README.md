# AgentFlow Studio

AgentFlow Studio 是一个本地优先的 Agent 工程工作台，用于验证 `Harness-first Agentic Delivery System`：把提示词、上下文、工具、规则、执行轨迹、质量报告和反馈信号组织成可重复、可审计、可维护的项目交付闭环。

当前内容生产与分发链路是第一条真实验证线，不是项目的全部定义。当前阶段目标仍然是“本地内测可用”：测试人员能跑任务、看 artifact、记录反馈、复用上下文，并清楚地区分结构验证、运行验证、人工验收和商业结论。

术语分工：

```text
AI-Native Company OS                 总系统
Harness-first Agentic Delivery System 当前主打项目交付主题
Evidence-backed Context Runtime       上下文运行层
Governed Memory / Memory OS           记忆和知识晋升子系统 / 长期愿景
AgentFlow Studio                      第一条本地验证项目线
```

## 当前状态

AFS 已具备以下基础：

- deterministic Production Memory asset loop。
- 本地 read-only Web Memory Workbench。
- Asset Profile Review Screen。
- Real Asset Test Run Harness。
- Two-Round Context Runtime Validation。
- Project Manifest v0.1。
- Provider Validation Gate。
- FastAPI Runtime Service v0.1，供外部前端工作台对接。
- 本地轻量 AgentOps contract：run trace、quality report、guardrail result、handoff record、maintenance audit report。

这些通过项只代表 structure/runtime verification，不代表 human acceptance、business validation 或 durable memory。

## 仓库分层

```text
apps/                  CLI、Runtime Service、过渡 Web 工作台
agentflow/             平台 contract、harness、router、memory、skills
examples/agentflow_production/  内容生产侧结构化 handoff 示例输入
agentflow_studio/      短视频分发侧包装、审查、报告
workflows/             YAML workflow definitions
prompts/               可审计 prompt templates
configs/               示例配置和工具目录
examples/              可提交的最小示例输入
data/                  本地 runtime data；生成内容默认 ignore
docs/                  架构、contract、runbook、handoff、维护账本
tests/                 自动化测试和 fixture
```

## 后端对接面

前端团队只需要对接 Runtime Service：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

启动后：

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
```

前端应使用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest

前端不应读取：

- provider secret
- 本地素材绝对路径
- signed URL
- 生成媒体字节
- CLI 内部实现

前端对接材料见：

```text
docs/frontend_integration/
examples/frontend_runtime_service/
```

## 本地开发

PowerShell：

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

维护审计：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

## Provider 边界

默认不调用远程 provider。

能力 gate：

```powershell
$env:AFS_ALLOW_REMOTE_LLM="true"
$env:AFS_ALLOW_REMOTE_ASR="true"
$env:AFS_ALLOW_REMOTE_IMAGE="true"
```

Video provider 仍需要任务级显式授权或后续独立 gate。一个能力的授权不代表另一个能力也被授权。

本地 provider config、secret、真实素材、生成媒体都不能提交。

## 当前产品路径

内容分发侧基础链路：

```text
video / transcript / clip_plan
  -> highlight_plan
  -> clip_plan.json
  -> real clips
  -> final_video.mp4
  -> subtitles.srt
  -> final_video_with_subtitles.mp4
  -> cover.jpg
  -> final_video_with_bgm.mp4
  -> finished_package_manifest.json
  -> inspect/review
```

Production Memory asset loop：

```text
Round 1 package
  -> tester feedback
  -> update candidate
  -> promotion decision / profile version
  -> context projection
  -> Round 2 package
  -> consistency review
  -> before/after report
```

## 关键文档

- `AGENTS.md`：本仓库 Agent 工作规则。
- `TASK_TRACKER.md`：当前任务账本。
- `DEVLOG.md`：短开发日志。
- `docs/company_operating_model.md`：公司规则在本项目的执行投影。
- `docs/local_internal_test_runbook.md`：本地内测 runbook。
- `docs/project_manifest_contract.md`：Project Manifest v0.1。
- `docs/frontend_integration/`：前端对接包。
- `docs/maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`：维护性重置账本。

## License

MIT License. See `LICENSE`.
