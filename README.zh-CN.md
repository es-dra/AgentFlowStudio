# AgentFlow Studio

[English README](README.md)

AgentFlow Studio 是面向 Agent 的内容生产与分发工作流平台。当前仓库容器
已经改名为 `AgentFlowStudio`；本阶段刻意不改 Python 包名、CLI 命令、
workflow 文件或 artifact 契约。

当前顶层模块：

- `agentflow/`：平台合同、harness、router、memory、skills 的逐步迁移层。
- `narratostudio/`：制作侧结构化内容 handoff MVP。
- `narratocut/`：分发侧短视频高光切片、包装、报告和复核 MVP。

NarratoCut 仍然是 Python 实现的 local-first CLI/Agent MVP：每个关键步骤
都会写出可读的 JSON 或媒体 artifact，并且可以通过 inspect/review 做质量
检查。

这是一个 clean-room 项目。之前的 AVP 工作区只作为参考材料，不作为代码迁移
来源。

## 当前状态

AgentFlow Studio 当前是本地优先的平台仓库，包含已经工作的 MVP 模块、
AgentFlow 合同层 helper，以及确定性的 Production Memory Architecture
切片。近期产品定位是“记忆驱动的 AI 内容生产工作台”，`Memory OS` 保留为
长期愿景。

仓库已经包含一个本地只读 Web Memory Workbench，用于选择本地 artifact 文件
并检查 JSON/Markdown 结构，也可以渲染 Production Memory asset loop。它不会
扫描目录、持久化浏览器状态、执行 workflow、调用 provider，也不是 hosted Web
产品。

NarratoStudio 当前制作侧 workflow 是：

```text
creative_brief
  -> story_bible
  -> episode_outline
  -> scene_plan
  -> shot_plan
  -> prompt_pack
  -> production_handoff
  -> production_report
```

NarratoCut 当前分发侧主链路是：

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

已经支持：

- deterministic script/transcript highlight workflows
- OCR-subtitle timeline from frame-level OCR results
- explainable candidate-window scoring to selected highlights
- mock and explicit opt-in OpenAI-compatible ASR paths
- local faster-whisper ASR path for offline product smokes
- ClipPlan validation against probed video metadata
- real FFmpeg slicing from existing ClipPlans
- simple final-video assembly from real clips
- final video quality hardening with FFmpeg warning classification
- subtitle export to SRT
- subtitle burn-in for existing videos and SRT files
- cover image export from an existing final video
- local BGM mixing with bounded volume settings
- finished package manifest indexing
- PosterFlow Memory Demo with explicit remote-image opt-in and local preview
- `inspect-run` and `review-run` reports for generated run artifacts
- `package_report.md` and delivery-readiness reports for handoff
- `draft-plan` for static workflow plans
- Production Memory asset loop artifacts and local read-only Web inspection

尚未包含：

- hosted Web UI、桌面 UI、SaaS runtime 或 workflow execution UI
- 自动选曲或版权管理
- 转场模板或多轨时间线编辑
- 基于视频画面的自动高光识别
- 真实 OCR frame extraction/provider integration
- 发布平台上传
- 物理 package 目录或 zip 导出
- hosted API、数据库、队列或 SaaS runtime

## 项目结构

```text
apps/                 CLI、API 和本地 Web 入口
agentflow/            平台合同和 harness 迁移层
narratostudio/        制作侧结构化 handoff 模块
narratocut/           分发侧媒体 workflow 模块
workflows/            YAML workflow 定义
prompts/              可审计 prompt 模板
configs/              示例配置和 tool catalog
examples/             面向用户的 demo 输入
data/                 本地运行数据；生成产物默认被 git 忽略
docs/                 架构、契约、路线图和 smoke 文档
tests/                自动化测试和 fixtures
```

## 环境要求

- 推荐 Python 3.12。
- 项目声明支持 `>=3.11,<3.13`。
- 暂不建议使用 Python 3.13，因为媒体、ASR 和模型相关依赖可能滞后。
- 真实视频切片、final video assembly、字幕烧录、封面导出、BGM 混音需要
  FFmpeg 和 FFprobe。
- 远程 LLM / ASR 默认关闭。

## 快速开始

PowerShell：

```powershell
cd D:\Projects\AgentFlowStudio
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m pytest
.venv\Scripts\ncut version
```

运行默认 mock workflow：

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```

预期产物包括：

```text
manifest.json
run_manifest.json
trace.json
quality_report.json
review_report.json
hooks.json
scripts.json
clip_plans.json
slice_manifest.json
clips/
```

`data/processed/`、`data/reports/` 和 `data/raw/` 下的本地媒体/运行产物
默认被 git 忽略。

## 产品级 Golden Path

Phase 13 之后，推荐用 Golden Path 做本地产品 smoke：

```text
source video + clip_plan
  -> real clips
  -> final_video.mp4
  -> subtitles.srt
  -> final_video_with_subtitles.mp4
  -> cover.jpg
  -> final_video_with_bgm.mp4
  -> finished_package_manifest.json
  -> inspect/review
```

所需本地文件、命令、预期产物和验收标准见
[`docs/golden_path.md`](docs/golden_path.md)。v0.1.0 的最小验收路径见
[`docs/golden_sample_v0_1_0.md`](docs/golden_sample_v0_1_0.md)。

## 主要 Workflow

规划和转写类 workflow：

- `workflows/script_to_highlight_plan.yaml`
- `workflows/transcript_to_highlight_clip_plan.yaml`
- `workflows/video_to_transcript.yaml`
- `workflows/video_to_transcript_real_asr.yaml`
- `workflows/video_to_highlight_clip_plan.yaml`
- `workflows/video_to_highlight_clip_plan_real_asr.yaml`

执行和成品产物类 workflow：

- `workflows/clip_plan_to_real_clips.yaml`
- `workflows/video_to_real_clips.yaml`
- `workflows/clips_to_final_video.yaml`
- `workflows/transcript_to_subtitles.yaml`
- `workflows/final_video_with_subtitles.yaml`
- `workflows/final_video_to_cover.yaml`
- `workflows/final_video_with_bgm.yaml`
- `workflows/final_video_package.yaml`

详细说明见 [`workflows/README.md`](workflows/README.md)。

## Artifact / Review 模型

NarratoCut 把生成产物当作一等契约。关键 artifact 包括：

```text
run_manifest.json
trace.json
quality_report.json
review_report.json
real_slice_manifest.json
final_video_manifest.json
subtitle_manifest.json
subtitle_burn_manifest.json
cover_manifest.json
audio_mix_manifest.json
finished_package_manifest.json
```

`inspect-run` 写出 `quality_report.json`。
`review-run` 读取 run artifacts 并写出 `review_report.json`。

相关契约：

- [`docs/run_contract.md`](docs/run_contract.md)
- [`docs/workflow_plan_contract.md`](docs/workflow_plan_contract.md)
- [`docs/agent_reviewer_contract.md`](docs/agent_reviewer_contract.md)
- [`docs/tool_contracts.md`](docs/tool_contracts.md)
- [`docs/agent_usage_guide.md`](docs/agent_usage_guide.md)
- [`docs/narratocut_delivery_checklist.md`](docs/narratocut_delivery_checklist.md)
- [`docs/current_architecture.md`](docs/current_architecture.md)

## 远程 Provider 边界

默认模型和 ASR 路径都是本地/mock。标准 CLI 和 workflow 不需要 API key，
也不会访问网络。

远程 LLM 需要显式开启：

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_LLM="true"
```

远程 ASR 需要显式开启：

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_ASR="true"
```

本地模型配置应写入被 git 忽略的 `configs/models.yaml`。仓库只提交
`configs/models.example.yaml` 等示例配置。

## FFmpeg 边界

检查本机 FFmpeg / FFprobe：

```powershell
.venv\Scripts\ncut ffmpeg-check --json
```

如果没有 FFmpeg，mock workflows 仍可运行。真实媒体 workflow 需要
FFmpeg/FFprobe。

## 开发检查

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m compileall apps agentflow narratocut narratostudio tests
git diff --check
.venv\Scripts\python -m apps.cli.main --help
.venv\Scripts\python -m apps.cli.main version
```

## License

MIT License。详见 [LICENSE](LICENSE)。
