# Workflow 目录

本目录保存 AgentFlow Studio 的 YAML workflow definitions。

## 使用原则

Agent 和前端原型不要扫描全部 workflow 后自行猜测。优先使用下面的产品入口；组件级 workflow 只作为 building block、测试 fixture 或历史回归资产。

## 当前推荐产品 Workflow

| Workflow | 类型 | 适用场景 | 主要输出 |
|---|---|---|---|
| `video_to_finished_package_local_asr.yaml` | product / recommended | 只有源视频，使用本地 ASR。 | `boundary_signal_manifest.json`、`candidate_windows.json`、`highlight_score_report.json`、`selection_diagnostics.json`、`finished_package_manifest.json`、`package_report.md` |
| `video_script_to_finished_package_local_asr.yaml` | product / recommended | 源视频 + 脚本，使用本地 ASR。 | `script_highlight_alignment.json`、`boundary_signal_manifest.json`、`candidate_windows.json`、`highlight_score_report.json`、`selection_diagnostics.json`、`finished_package_manifest.json`、`package_report.md` |
| `video_to_finished_package_real_asr.yaml` | product / optional | 明确允许远程 ASR。 | 同上，但 ASR 是 opt-in。 |
| `video_script_to_finished_package_real_asr.yaml` | product / optional | 视频 + 脚本，并明确允许远程 ASR。 | 同上，外加脚本对齐。 |
| `agentflow_production_brief_to_production_handoff.yaml` | production / recommended | 需要本地优先的结构化 production handoff。 | `production_handoff.json`、`production_report.md`、`memory_candidates.json`、`cost_quality_trace.json` |
| `posterflow_memory_demo.yaml` | demo / optional remote image | 需要显式远程图片 opt-in 的视觉记忆 demo。 | `poster_candidates_manifest.json`、`poster_preview.html`、`poster_memory_candidates.json`、`next_round_prompt.json`、`poster_round_comparison.json` |

## 常用命令

正式运行后，使用下面命令检查 run：

```powershell
.venv\Scripts\afs inspect-run --run-dir <run_dir>
.venv\Scripts\afs review-run --run-dir <run_dir>
.venv\Scripts\afs package-report --run-dir <run_dir>
```

多 run 交付检查：

```powershell
.venv\Scripts\afs delivery-readiness `
  --run-dir <video_only_run_dir> `
  --run-dir <video_script_run_dir> `
  --output <delivery_report_dir>
```

这些命令只读取已有 artifact 或刷新报告，不代表人工验收或商业验证。

## Production Handoff 示例

```powershell
.venv\Scripts\afs run-workflow --workflow workflows/agentflow_production_handoff.yaml --input examples/agentflow_production/creative_brief.example.json --output data/processed/runs/demo_agentflow_production_handoff
.venv\Scripts\afs inspect-run --run-dir data/processed/runs/demo_agentflow_production_handoff
.venv\Scripts\afs review-run --run-dir data/processed/runs/demo_agentflow_production_handoff
```

该 workflow 是 local-first structured production handoff generator。它不调用 remote LLM，不创建媒体资产，不发布内容，不写 long-term memory，也不提供 Web UI。

## PosterFlow 示例

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
$env:AFS_IMAGE_BASE_URL="https://your-openai-compatible-host/v1"
$env:AFS_IMAGE_API_KEY="<local-secret>"
$env:AFS_IMAGE_MODEL="<image-model>"
.venv\Scripts\afs run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/run_001
```

`AFS_IMAGE_API_KEY` 只能在本地环境中设置，不能进入 Git。

## 组件 Workflow

常见组件：

- `transcript_to_candidate_windows.yaml`
- `clip_plan_to_real_clips.yaml`
- `clips_to_final_video.yaml`
- `final_video_package.yaml`
- `mock_text_to_slices.yaml`
- `video_to_real_clips.yaml`

组件 workflow 可以用于测试、调试和回归，但不是默认产品入口。

## 边界

- workflow 输出默认写入 `data/processed/` 或 `data/reports/`，这些目录被 Git ignore。
- 真实媒体不提交。
- provider 调用必须有显式 capability gate。
- workflow 通过不等于 human acceptance。
- provider smoke 不等于 business validation。
- memory candidate 不等于 durable memory。
