# NarratoCut

[English README](README.md)

NarratoCut 是一个面向短视频生产流程的 Python MVP 项目，用来探索从文本分析、脚本生成、切片计划到真实视频切片与质量审查的自动化工作流。

当前版本支持文本到 hooks 分析、mock 脚本生成、ClipPlan 生成、mock slicing、本地 workflow 编排、轻量 Model Gateway、FFmpeg/FFprobe 可用性检测，以及基于本地视频、ROI settings 和已提供 `ClipPlan` 的真实视频切片 workflow。

这是一个 clean-room 项目。之前的 AVP 工作区只作为参考材料，不作为代码迁移来源。

## 当前状态

NarratoCut 目前是 CLI-first、schema-first、workflow-first 的原型项目。默认流程是本地 mock pipeline：

```text
text -> hooks -> scripts -> clip_plans -> mock clips
```

已实现能力：

- ROI / hook analysis，本地 mock provider 默认可用
- mock short-video script generation
- 确定性的 ClipPlan generation
- mock slicing 输出：`slice_manifest.json` 和 `.txt` 占位 clips
- 顺序 YAML workflow 执行
- Model Gateway Lite，默认 mock，可选 OpenAI-compatible provider 代码路径
- FFmpeg availability probe
- real slicing command contract
- standalone `ncut slice-real` PoC
- ROI-aware real video slicing workflow：
  `本地视频 + ROI settings + ClipPlan -> 元数据读取 -> 计划校验 -> FFmpeg clips -> inspect/review`

当前真实视频能力是“手工提供 ClipPlan 后的可信执行层”。系统可以校验并执行一个已有切片计划，生成真实 `.mp4` clips 和可审查 artifacts，但当前还不是自动爆点识别、自动剪辑或自动成片工具。

尚未实现：

- 自动高光 / 爆点识别
- ASR 或带时间戳 transcript 生成
- 剧本 / transcript 自动生成可执行 ClipPlan
- clips 拼接为 final video
- 字幕烧录
- 竖屏裁剪或画幅适配
- BGM、封面生成、多轨 timeline
- Web UI、API server、数据库、队列或 SaaS runtime

## 项目结构

```text
apps/                 CLI、API 和未来 Web 入口
narratocut/           核心 Python package
workflows/            YAML workflow 定义
prompts/              可审计 prompt 模板
configs/              示例配置文件
examples/             面向用户的 demo 输入
data/                 本地运行数据；生成产物默认被 git 忽略
docs/                 架构和设计说明
tests/                自动化测试和 fixtures
```

## 环境要求

- 推荐 Python 3.12。
- 项目声明支持 `>=3.11,<3.13`。
- 暂不建议使用 Python 3.13，因为 ASR、视频处理和模型相关依赖通常会滞后于最新 runtime。
- 默认 mock pipeline 不强制安装 FFmpeg；`slice-real` 和 `workflows/real_video_roi_to_clips.yaml` 需要本机可用的 FFmpeg / FFprobe。

## 快速开始

PowerShell：

```powershell
cd D:\Projects\NarratoCut
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m pytest
.venv\Scripts\ncut version
```

运行完整 mock workflow：

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
```

预期生成文件：

```text
data/processed/runs/demo_full_mock/
+-- manifest.json
+-- hooks.json
+-- scripts.json
+-- clip_plans.json
+-- slice_manifest.json
+-- clips/
    +-- clip_plan_script_mock_001.txt
    +-- clip_plan_script_mock_002.txt
    +-- clip_plan_script_mock_003.txt
```

`data/processed/` 下的运行产物会被 git 忽略。

## Model Gateway 边界

默认 provider 是 `mock`，所以标准 CLI 和 workflow 命令不需要 API key，也不会访问网络。

远程 LLM 调用默认关闭。只有在明确需要真实 provider 调用时，才设置：

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_LLM="true"
```

本地模型配置应写入 `configs/models.yaml`，该文件被 git 忽略。仓库中只提交 `configs/models.example.yaml`。

## FFmpeg 边界

检查本机 FFmpeg / FFprobe 可用性：

```powershell
.venv\Scripts\ncut ffmpeg-check --json
```

如果本机没有安装 FFmpeg 或 FFmpeg 不在 `PATH` 中，该命令会输出 unavailable 状态。这对默认 mock pipeline 是可接受的，但真实视频切片 workflow 需要 FFmpeg 和 FFprobe。

运行 Phase 9 真实视频切片 workflow：

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/real_video_roi_to_clips.yaml --input examples/demo_real_video/input.example.json --output data/processed/runs/demo_real_video
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_real_video
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_real_video
```

该 workflow 需要 input bundle 中声明的本地视频文件。真实媒体文件和运行产物默认被 git 忽略。

## 开发检查

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m compileall -q apps narratocut tests
.venv\Scripts\ncut --help
.venv\Scripts\ncut version
```

## License

MIT License。详见 [LICENSE](LICENSE)。
